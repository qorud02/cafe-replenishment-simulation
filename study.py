"""Reproducible shared-ingredient inventory experiment. Python 3.12+ / NumPy.

An independent daily-cohort simulator. No fnb-procure source is imported.
The exact static whole-pack rule in fnb-procure is a related implementation,
not a source of simulated observations or an expiry-aware policy.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import itertools
import json
import platform
import time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'protocol.json').read_text(encoding='utf-8'))
assert P['lead_time_days'] == P['review_interval_days'] == 1, 'This model implements daily review and one-day delivery.'
assert P['disposal_fee'] == 0, 'No disposal fee is implemented.'
assert all(float(x).is_integer() and x > 0 for x in P['recipe_units']), 'Recipes must use positive whole quantity units.'
UNIT_LITERS = P['quantity_unit_ml'] / 1000
MEANS = np.array(P['menu_mean_counts'], dtype=float)
RECIPE = np.array(P['recipe_units'], dtype=float)
WEEK = np.array(P['weekday_multipliers'], dtype=float)


def forecasts(days: int, cv: float):
    multiplier = WEEK[np.arange(days) % 7]
    mean = multiplier * (MEANS @ RECIPE)
    variance = multiplier * (MEANS @ (RECIPE ** 2)) + cv ** 2 * mean ** 2
    return mean, variance


def make_demand(replications: int, days: int, cv: float, seed: int):
    """Gamma-Poisson common daily factor, independent across days/replications."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, round(cv * 1000)]))
    factor = (np.ones((replications, days)) if cv == 0 else
              rng.gamma(1 / cv ** 2, cv ** 2, size=(replications, days)))
    rates = factor[:, :, None] * WEEK[np.arange(days) % 7][None, :, None] * MEANS
    counts = rng.poisson(rates)
    return (counts @ RECIPE.astype(np.int64)).astype(np.int64)


def consume(stock: np.ndarray, demand: np.ndarray):
    """Mutates cohorts (soonest expiry first); returns served volume."""
    remaining = np.array(demand, dtype=float, copy=True)
    for age in range(stock.shape[-1]):
        used = np.minimum(stock[..., age], remaining)
        stock[..., age] -= used
        remaining -= used
    return np.asarray(demand) - remaining


def forecast_expiry(stock: np.ndarray, means: np.ndarray):
    """Expected-mean depletion heuristic over the two-day protection period.

    This is expiry under deterministic mean demands, not E[waste] under the
    stochastic demand distribution. Only currently available cohorts enter.
    """
    trial = stock.copy()
    waste = np.zeros(stock.shape[:-1])
    for mean in means:
        consume(trial, np.full(stock.shape[:-1], mean))
        waste += trial[..., 0]
        trial[..., :-1] = trial[..., 1:]
        trial[..., -1] = 0
    return waste


def simulate(demand: np.ndarray, *, pack: int, life: int, cv: float,
             penalty_ratio: float, z_values, expiry_adjusted=False,
             burn_in=None, check=True):
    """Simulate z settings in parallel on identical demand paths.

    Returned arrays have dimensions [independent replication, z setting].
    Costs are daily rates after burn-in. Lead time is exactly one day.
    """
    burn_in = P['burn_in_days'] if burn_in is None else burn_in
    n, days = demand.shape
    z = np.asarray(z_values, dtype=float)
    stock = np.zeros((n, len(z), life))
    pipeline = np.zeros((n, len(z)))
    mean, variance = forecasts(days + 1, cv)
    totals = {k: np.zeros((n, len(z))) for k in
              ('purchased', 'served', 'unmet', 'expired', 'inventory', 'orders', 'demand')}
    for day in range(days):
        stock[..., -1] += pipeline
        before = stock.sum(axis=-1)
        protection_mean = mean[day:day+2].sum()
        protection_sd = np.sqrt(variance[day:day+2].sum())
        target = np.maximum(0, protection_mean + z * protection_sd)
        correction = forecast_expiry(stock, mean[day:day+2]) if expiry_adjusted else 0
        order = pack * np.ceil(np.maximum(0, target[None, :] - before + correction) / pack)
        requested = np.broadcast_to(demand[:, day, None], before.shape)
        served = consume(stock, requested)
        expired = stock[..., 0].copy()
        stock[..., :-1] = stock[..., 1:]
        stock[..., -1] = 0
        closing = stock.sum(axis=-1)
        if check:
            if not np.allclose(before, served + expired + closing, atol=1e-9, rtol=0):
                raise AssertionError('Daily ingredient conservation failed')
            if np.any(stock < 0) or np.any(order % pack != 0):
                raise AssertionError('Negative stock or nonintegral pack order')
        pipeline = order
        if day >= burn_in:
            daily = {'purchased': order, 'served': served, 'unmet': requested - served,
                     'expired': expired, 'inventory': closing, 'orders': order > 0,
                     'demand': requested}
            for key, value in daily.items():
                totals[key] += value
    measured = days - burn_in
    cost = (totals['purchased'] * P['purchase_cost_krw_per_unit'] +
            totals['unmet'] * P['purchase_cost_krw_per_unit'] * penalty_ratio +
            totals['inventory'] * P['holding_cost_krw_per_unit_day']) / measured
    output = {k + '_per_day': v / measured for k, v in totals.items()}
    output.update(cost_per_day=cost,
                  fill_rate=np.divide(totals['served'], totals['demand'],
                                      out=np.ones_like(cost), where=totals['demand'] != 0),
                  final_inventory=stock.sum(axis=-1), final_pipeline=pipeline)
    return output


def ci(values):
    from scipy.stats import t
    a = np.asarray(values, dtype=float)
    se = a.std(ddof=1) / np.sqrt(len(a))
    margin = t.ppf(0.975, len(a)-1) * se
    return float(a.mean()), float(a.mean()-margin), float(a.mean()+margin), float(se)


def write_csv(file: Path, rows):
    with file.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(sensitivity=False):
    start = time.perf_counter()
    out = HERE / ('sensitivity' if sensitivity else 'results')
    out.mkdir(exist_ok=True)
    if sensitivity:
        packs, lives, cvs = [20, 120], [2, 5], [0.7]
        burn, duration, train_seed, test_seed = 180, 1095, 2026101103, 2026101104
    else:
        packs, lives, cvs = P['pack_units'], P['shelf_life_days'], P['common_factor_cv']
        burn, duration = P['burn_in_days'], P['measurement_days']
        train_seed, test_seed = P['validation_seed'], P['evaluation_seed']
    days = burn + duration
    z_grid = P['z_grid']
    train = {cv: make_demand(P['validation_replications'], days, cv, train_seed) for cv in cvs}
    test = {cv: make_demand(P['evaluation_replications'], days, cv, test_seed) for cv in cvs}
    rows, paired, replicate_rows, calibration_rows = [], [], [], []
    for pack, life, cv, penalty in itertools.product(packs, lives, cvs, P['shortage_penalty_purchase_cost_ratio']):
        sid = f'Q{pack}_M{life}_CV{cv}_P{penalty}'
        params = dict(pack=pack, life=life, cv=cv, penalty_ratio=penalty, burn_in=burn)
        outcomes = {}
        for policy, adjusted in [('mean_base_stock', False), ('calibrated_base_stock', False),
                                 ('expiry_adjusted_base_stock', True)]:
            if policy == 'mean_base_stock':
                best_z = 0.0
            else:
                validation = simulate(train[cv], z_values=z_grid, expiry_adjusted=adjusted, **params)
                costs = validation['cost_per_day'].mean(axis=0)
                best_idx = int(costs.argmin())
                best_z = z_grid[best_idx]
                for z, value in zip(z_grid, costs):
                    calibration_rows.append(dict(scenario=sid, policy=policy, z=z,
                                                 validation_daily_cost_krw=float(value), selected=z == best_z))
            result = simulate(test[cv], z_values=[best_z], expiry_adjusted=adjusted, **params)
            outcomes[policy] = {k: v[:, 0] for k, v in result.items()}
            cost, lo, hi, se = ci(outcomes[policy]['cost_per_day'])
            row = dict(scenario=sid, pack_liters=pack*UNIT_LITERS, shelf_life_days=life, factor_cv=cv,
                       penalty_ratio=penalty, policy=policy, selected_z=best_z,
                       daily_cost_krw=cost, cost_ci_low=lo, cost_ci_high=hi, cost_mc_se=se)
            for metric in ('fill_rate', 'purchased_per_day', 'expired_per_day', 'unmet_per_day',
                           'inventory_per_day', 'orders_per_day'):
                value = outcomes[policy][metric].mean()
                key = metric if metric in ('fill_rate','orders_per_day') else metric.replace('_per_day', '_liters_per_day')
                row[key] = float(value if metric in ('fill_rate','orders_per_day') else value*UNIT_LITERS)
            rows.append(row)
            for i in range(P['evaluation_replications']):
                replicate_rows.append(dict(scenario=sid, policy=policy, replication=i,
                                           **{k: float(v[i]) for k, v in outcomes[policy].items()}))
        baseline = outcomes['calibrated_base_stock']
        adjusted = outcomes['expiry_adjusted_base_stock']
        diff, lo, hi, se = ci(adjusted['cost_per_day'] - baseline['cost_per_day'])
        fill_diff, fill_lo, fill_hi, _ = ci(adjusted['fill_rate'] - baseline['fill_rate'])
        waste_diff, waste_lo, waste_hi, _ = ci((adjusted['expired_per_day'] - baseline['expired_per_day'])*UNIT_LITERS)
        paired.append(dict(scenario=sid, pack_liters=pack*UNIT_LITERS, shelf_life_days=life,
                           factor_cv=cv, penalty_ratio=penalty,
                           cost_difference_krw=diff, ci_low=lo, ci_high=hi, mc_se=se,
                           percent_difference=100*diff/baseline['cost_per_day'].mean(),
                           fill_rate_difference=fill_diff, fill_ci_low=fill_lo, fill_ci_high=fill_hi,
                           expired_liters_difference=waste_diff, expired_ci_low=waste_lo, expired_ci_high=waste_hi))
        print(f'{sid}: expiry minus calibrated {diff:+.2f} KRW/day [{lo:+.2f}, {hi:+.2f}]', flush=True)
    write_csv(out/'scenario_results.csv', rows)
    write_csv(out/'paired_comparisons.csv', paired)
    write_csv(out/'replication_results.csv', replicate_rows)
    write_csv(out/'calibration.csv', calibration_rows)
    metadata = dict(protocol_sha256=hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
                    python=platform.python_version(), numpy=np.__version__,
                    elapsed_seconds=time.perf_counter()-start, scenarios=len(paired),
                    validation_replications=P['validation_replications'],
                    evaluation_replications=P['evaluation_replications'],
                    measured_days=duration, burn_in_days=burn,
                    validation_seed=train_seed, evaluation_seed=test_seed,
                    improved_point_estimates=sum(r['cost_difference_krw']<0 for r in paired),
                    lower_pointwise_ci=sum(r['ci_high']<0 for r in paired),
                    higher_pointwise_ci=sum(r['ci_low']>0 for r in paired))
    (out/'run_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sensitivity', action='store_true')
    args = parser.parse_args()
    run(args.sensitivity)

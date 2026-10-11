"""Post hoc expanded-grid check for primary upper-boundary tuning selections.

The primary results and protocol are never modified. Settings are selected only
from primary validation-calibration rows, not from primary evaluation outcomes.
Both calibrated rules get the same expanded grid and original validation paths.
A fresh evaluation seed is used. Run after installing requirements.txt.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

def read_csv(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dependency-dir', type=Path, default=None,
                        help='Optional installed-package directory for this interpreter')
    args = parser.parse_args()
    if args.dependency_dir is not None:
        if not args.dependency_dir.is_dir():
            raise SystemExit('Dependency directory does not exist')
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    import numpy as np
    import scipy
    from study import P, simulate, make_demand, ci, write_csv
    start = time.perf_counter()
    out = HERE/'boundary-sensitivity'
    out.mkdir(exist_ok=True)
    protected = [HERE/'protocol.json', HERE/'study.py'] + list((HERE/'results').glob('*.csv')) + [HERE/'results/run_metadata.json'] + list((HERE/'sensitivity').glob('*.csv')) + [HERE/'sensitivity/run_metadata.json']
    before = {str(p.relative_to(HERE)):sha(p) for p in protected}
    primary_cal = read_csv(HERE/'results/calibration.csv')
    original = [float(z) for z in P['z_grid']]
    upper = max(original)
    selected = sorted({r['scenario'] for r in primary_cal if r['selected']=='True' and float(r['z'])==upper})
    if not selected:
        raise SystemExit('No primary upper-boundary scenario found')
    primary_summaries = read_csv(HERE/'results/scenario_results.csv')
    source = {r['scenario']:r for r in primary_summaries}
    grid = sorted(set(original+[3.5,4.0,4.5,5.0]))
    assert original==[-1.,-.5,0.,.5,1.,1.5,2.,2.5,3.]
    assert P['quantity_unit_ml']==50 and P['lead_time_days']==1
    assert P['validation_replications']==30 and P['evaluation_replications']==200
    burn, duration = 90,365
    days = burn+duration
    eval_seed = 2026101105
    cvs = sorted({float(source[s]['factor_cv']) for s in selected})
    validation = {cv:make_demand(30,days,cv,P['validation_seed']) for cv in cvs}
    evaluation = {cv:make_demand(200,days,cv,eval_seed) for cv in cvs}
    old_lookup = {(r['scenario'],r['policy'],float(r['z'])):float(r['validation_daily_cost_krw']) for r in primary_cal}
    summary_rows=[];paired_rows=[];replication_rows=[];calibration_rows=[]
    max_old_validation_difference=0.
    for sid in selected:
        source_row=source[sid]
        pack=int(round(float(source_row['pack_liters'])*20))
        life=int(source_row['shelf_life_days'])
        cv=float(source_row['factor_cv'])
        penalty=float(source_row['penalty_ratio'])
        params=dict(pack=pack,life=life,cv=cv,penalty_ratio=penalty,burn_in=burn)
        outcomes={};chosen={}
        for policy,adjusted in [('calibrated_base_stock',False),('expiry_adjusted_base_stock',True)]:
            val=simulate(validation[cv],z_values=grid,expiry_adjusted=adjusted,**params)
            costs=val['cost_per_day'].mean(axis=0)
            idx=int(costs.argmin());z=grid[idx];chosen[policy]=z
            for candidate,value in zip(grid,costs):
                if candidate in original:
                    difference=abs(float(value)-old_lookup[(sid,policy,candidate)])
                    max_old_validation_difference=max(max_old_validation_difference,difference)
                    if difference>1e-7:
                        raise AssertionError(('Original validation rerun mismatch',sid,policy,candidate,difference))
                calibration_rows.append(dict(scenario=sid,policy=policy,z=candidate,
                    validation_daily_cost_krw=float(value),selected=candidate==z))
            ev=simulate(evaluation[cv],z_values=[z],expiry_adjusted=adjusted,**params)
            outcomes[policy]={k:v[:,0] for k,v in ev.items()}
            mean,lo,hi,se=ci(outcomes[policy]['cost_per_day'])
            row=dict(scenario=sid,pack_liters=pack*.05,shelf_life_days=life,
                factor_cv=cv,penalty_ratio=penalty,policy=policy,selected_z=z,
                selected_at_upper_boundary=z==max(grid),daily_cost_krw=mean,
                cost_ci_low=lo,cost_ci_high=hi,cost_mc_se=se)
            for metric in ('fill_rate','purchased_per_day','expired_per_day','unmet_per_day','inventory_per_day','orders_per_day'):
                value=float(outcomes[policy][metric].mean())
                field=metric if metric in ('fill_rate','orders_per_day') else metric.replace('_per_day','_liters_per_day')
                row[field]=value if metric in ('fill_rate','orders_per_day') else value*.05
            summary_rows.append(row)
            for i in range(200):
                replication_rows.append(dict(scenario=sid,policy=policy,replication=i,
                    **{k:float(v[i]) for k,v in outcomes[policy].items()}))
        baseline=outcomes['calibrated_base_stock'];adjusted=outcomes['expiry_adjusted_base_stock']
        assert np.array_equal(baseline['demand_per_day'],adjusted['demand_per_day'])
        diff,lo,hi,se=ci(adjusted['cost_per_day']-baseline['cost_per_day'])
        f,fl,fh,_=ci(adjusted['fill_rate']-baseline['fill_rate'])
        w,wl,wh,_=ci((adjusted['expired_per_day']-baseline['expired_per_day'])*.05)
        paired_rows.append(dict(scenario=sid,pack_liters=pack*.05,shelf_life_days=life,
            factor_cv=cv,penalty_ratio=penalty,
            baseline_z=chosen['calibrated_base_stock'],expiry_adjusted_z=chosen['expiry_adjusted_base_stock'],
            cost_difference_krw=diff,ci_low=lo,ci_high=hi,mc_se=se,
            percent_difference=100*diff/float(baseline['cost_per_day'].mean()),
            fill_rate_difference=f,fill_ci_low=fl,fill_ci_high=fh,
            expired_liters_difference=w,expired_ci_low=wl,expired_ci_high=wh))
        print(f'{sid}: z={chosen}; delta {diff:+.6f} [{lo:+.6f}, {hi:+.6f}] KRW/day',flush=True)
    write_csv(out/'scenario_results.csv',summary_rows)
    write_csv(out/'paired_comparisons.csv',paired_rows)
    write_csv(out/'replication_results.csv',replication_rows)
    write_csv(out/'calibration.csv',calibration_rows)
    after={str(p.relative_to(HERE)):sha(p) for p in protected}
    assert before==after,'Primary files changed during sensitivity; investigate before interpreting'
    remaining=[dict(scenario=r['scenario'],policy=r['policy'],z=r['selected_z']) for r in summary_rows if r['selected_at_upper_boundary']]
    metadata=dict(analysis_type='post hoc validation-boundary sensitivity',
        reason='At least one calibrated policy selected z=3 on primary validation paths',
        selection_uses_primary_evaluation_outcomes=False,
        scenario_selection=selected,scenarios=len(selected),original_z_grid=original,expanded_z_grid=grid,
        validation_replications=30,evaluation_replications=200,burn_in_days=burn,measured_days=duration,
        validation_seed=P['validation_seed'],evaluation_seed=eval_seed,
        validation_reproduction_max_absolute_difference=max_old_validation_difference,
        remaining_upper_boundary_fits=remaining,remaining_upper_boundary_count=len(remaining),
        negative_point_estimates=sum(r['cost_difference_krw']<0 for r in paired_rows),
        positive_point_estimates=sum(r['cost_difference_krw']>0 for r in paired_rows),
        zero_point_estimates=sum(r['cost_difference_krw']==0 for r in paired_rows),
        lower_pointwise_ci=sum(r['ci_high']<0 for r in paired_rows),
        higher_pointwise_ci=sum(r['ci_low']>0 for r in paired_rows),
        python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        elapsed_seconds=time.perf_counter()-start,
        protected_primary_file_hashes=before,primary_files_unchanged=before==after)
    (out/'run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    readme="""# Expanded safety-grid sensitivity

This analysis was added after primary validation selected the original upper
endpoint z=3 for at least one of the two calibrated policies. It was not part of
the original factorial protocol. The primary experiment is preserved unchanged.

Selected settings are identified exclusively from validation calibration flags.
Both calibrated policies are retuned on the identical original 30 validation
paths with the original nine z values plus3.5,4,4.5,5. Primary evaluation outcomes
are not used for tuning or setting selection. Evaluation uses fresh seed
2026101105, 200 independent paths,90 burn-in and365 measured days.

Negative paired cost differences favor expiry adjustment. Confidence intervals
are pointwise Monte Carlo intervals conditional on the selected tuning values.
If z=5 remains selected, that residual boundary is reported without further
automatic expansion. This sensitivity checks dependence on the tuning-grid cap;
it does not establish an unrestricted optimal policy.

scenario_results.csv contains liters/day for physical flow rates. Raw
replication_results.csv retains the50ml base unit. Purchase rates refer to order
commitments. The main run protocol, source and primary CSV hashes are recorded
in run_metadata.json and checked unchanged at completion.
"""
    (out/'README.md').write_text(readme,encoding='utf-8')
    print(json.dumps(metadata,indent=2),flush=True)

if __name__=='__main__':
    main()

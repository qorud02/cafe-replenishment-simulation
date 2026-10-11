# Independent model review

Reviewed 2026-10-11 KST. Source files were not edited. Scope: event timing, age cohorts, order commitments, demand moments, common random numbers, calibration/evaluation separation and numerical implementation. This review does not establish empirical validity for a particular cafe or a literature novelty claim.

## Verdict

No discrepancy was found between the implemented simulator and an independently written scalar cohort reference. Event timing, one-day delivery lag, shelf-life expiry, ingredient conservation and the stated order-commitment cost objective are internally consistent for the frozen scenario values. The remaining issues are limits of interpretation and configuration, listed below.

## Executed checks

1. The existing test_study.py suite passed: 8 tests, 7.160 seconds, Python 3.12, NumPy installed.
2. An independently written scalar reference used ordinary Python lists and explicit per-cohort loops, independent mean/variance formulas and math.ceil. It did not call study.consume, study.forecast_expiry, study.forecasts or study.make_demand. Only study.simulate was used as the system under comparison.
3. The reference compared 192 settings: life in {1,2,3,5}, pack in {1,20,60,120}, common-factor CV in {0,.35,.7}, penalty in {3,10}, expiry adjustment on/off. Each setting used 3 demand paths, 17 days, 3 burn-in days and z in {-.5,0,1,2.5}.
4. All 2,304 scalar trajectories and 25,344 returned metric comparisons matched exactly. Maximum absolute difference: 0.0. Including life=1 checked the event implementation beyond the planned life grid, without claiming that the policy is optimal for life=1.
5. The standalone checking script is verify_reference.py. Its stdout results are summarized here; the experimental engine and protocol were unchanged by the reviewer.

### Hand-worked event fixture

Demand is zero for 3 days; pack=20 units; life=2; CV=0; z=0; burn-in=0. Conditional daily means are 144,162,171,180 units.

| Day | Arrival | Opening stock | Protection mean | Order | Expiry | Closing stock |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 306 | 320 | 0 | 0 |
| 1 | 320 | 320 | 333 | 20 | 0 | 320 |
| 2 | 20 | 340 | 351 | 20 | 320 | 20 |

Total order commitments are 360 units, total expiry is 320 units, final stock is 20 and final pipeline is 20. Thus 360=320+20+20. Holding quantity summed over the window is 340 unit-days. Reported daily cost is (360×100+340×.25)/3=12,028.333333333334 KRW. The simulator matched every quantity.

This fixture also shows why the purchased field means orders committed rather than deliveries received during the window. Day-2's last order is costed and remains outstanding. The revised protocol objective correctly says order commitments and explicitly reports end-of-horizon orders.

## Event order and policy interpretation

- Receipt before ordering, order before current-day demand, FIFO consumption, expiration at the end of the day and cohort aging give a delivery lag of exactly one day.
- A lot received with life L remains usable on its arrival day and the next L−1 days. There is no off-by-one shelf-life error in the inspected loop.
- Because review occurs before today's demand and an order arrives tomorrow, the t and t+1 protection mean/variance is appropriate for the chosen order-up-to heuristic.
- Current pipeline is fully received before the order decision; with this fixed one-day lead time there is no other outstanding order to include in the position at that instant.
- forecast_expiry projects only existing cohorts. Later incoming lots are younger, so FIFO means they do not change whether currently held older stock survives those same deterministic demand draws.
- The expiry correction remains a heuristic. It does not solve the stochastic dynamic program and should not be described as expected stochastic waste.

A simple distinction between deterministic-mean expiry and expected waste is worth preserving in the exposition. Ten units expire after today's demand. Demand is 0 or12 with equal probability, giving mean6. Deterministic mean depletion predicts waste4, while expected waste is (10+0)/2=5. Current forecast_expiry docstring already distinguishes the two.

## Demand distribution

For weekday multiplier w, conditional menu counts satisfy N_j|F~Poisson(F w mu_j), independently given common factor F, with E[F]=1 and Var(F)=CV². Therefore aggregate ingredient mean is wΣ(mu_j r_j), and variance is wΣ(mu_j r_j²)+CV²[wΣ(mu_j r_j)]². The code matches this law.

At w=1, aggregate mean is 180 units:

| Common-factor CV | Aggregate SD | Correlation between menus 0 and1 |
|---|---:|---:|
| 0 | 29.59729717 | 0 |
| .35 | 69.60603422 | .63988285 |
| .7 | 129.42951750 | .87613896 |

Increasing CV changes both marginal demand variance and cross-menu dependence. The original question's wording about correlation alone was too strong. The inspected revised protocol now correctly asks about shared daily demand-factor variability. Do not infer a pure causal or isolated correlation effect from these cells.

## Calibration and inference

Separate validation/evaluation SeedSequences prevent realized evaluation demand entering calibration. Within a scenario all policies receive identical demand paths. Separate z calibration for both calibrated and expiry-adjusted policies gives the baseline the same tuning privilege; the mean policy is a secondary untuned benchmark.

The selected policy's paired cost difference is computed across 200 independent replication paths. Pointwise Student-t intervals are reasonable Monte Carlo intervals for the simulation means, conditional on the validation-selected tuning values. They do not include variation caused by choosing a different validation sample. No claim about a population of real cafes follows.

The protocol correctly avoids a simultaneous54-cell claim. Counts of intervals lying above/below zero are descriptive; they are not a multiplicity-controlled discovery count. If the manuscript singles out cells after viewing results, label the selection exploratory.

The 9-point revised z grid is still a restricted tuning family. Report selected z and how often a grid boundary wins. Boundary selection would justify a predeclared sensitivity extension rather than a claim that the compared rules were globally optimized.

Long-horizon sensitivity with new seeds is appropriate to inspect endpoint effects. Even though order commitments are a valid cost objective, finite-window opening/closing inventory and pipeline can affect small differences. Report terminal quantities and compare direction and magnitude in the planned1,095-day evaluation.

## Remaining configuration issues

These do not change the inspected frozen runs but should be prevented from silently changing later:

1. study.py uses .05 directly for liters rather than quantity_unit_ml/1000.
2. lead_time_days and review_interval_days are protocol metadata; simulate implements1 day directly.
3. disposal_fee is fixed at0 and not used in cost. A future nonzero protocol value would silently fail to change the objective.
4. recipe conversion casts RECIPE to int64. Current recipe units are integers, but fractional future values would truncate.
5. The variance and common-factor generator assume days are independent; autocorrelated shocks require a different protection-period variance.
6. The system Python312 used for independent checks has NumPy but no SciPy. ci requires SciPy. requirements.txt pins NumPy/SciPy/Matplotlib; install them in the actual run environment and record that interpreter.

Recommended small correction: assert the currently supported configuration values, or use the protocol fields in computation. At minimum make the supported domain explicit in the README and record the protocol hash before each run.

## Scientific limits to retain

The setup has one shared ingredient, additive ingredient-volume demand, no substitution or customer allocation, known weekday mean/variance, fixed recipe and shelf life, no supplier uncertainty and hypothetical costs. Fill rate means ingredient-volume service. This experiment cannot establish actual menu stockout counts, customer behavior, cafe profit gains or a new optimal policy.

For a research manuscript the strongest report is a reproducible comparative result, including small effects and adverse cases. Shared ingredient pooling and expiry-aware replenishment already have substantial literature; simulator correctness alone does not establish novelty.

## Reviewed file hashes

- study.py: 05a86dca5148646913e38b7ef6387ffe34848ae7883acfab585d60e000ba812e
- protocol.json: 709181d362704a9a12a2127fc2e18806ec6c8b1f3db028b7279d7b02eb796c0c
- test_study.py: 7a06439607c2ac54c60987bcedc7913441e3fee794f7ac84d7fa026bf4d0ddbe

Protocol wording and z-grid were revised by the main agent during the review; the hashes above identify the final inspected files. If code or scientific assumptions change, affected checks should be rerun.

## Main-agent corrections after review

The engine now derives liters from quantity_unit_ml and asserts one-day lead/review, zero disposal fee and positive whole recipe units. These checks preserve the reviewed model for the frozen protocol. Both recorded runs use NumPy2.3.5 and Python3.12.9. Final file hashes are in the package manifest.

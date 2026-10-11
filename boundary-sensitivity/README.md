# Expanded safety-grid sensitivity

This analysis was added after primary validation selected the original upper
endpoint z=3 for at least one of the two calibrated policies. It was not part of
the original factorial protocol. The primary experiment is preserved unchanged.

Selected settings are identified exclusively from validation calibration flags.
Both calibrated policies are retuned on the identical original 30 validation
paths with the original nine z values plus 3.5,4,4.5,5. Primary evaluation outcomes
are not used for tuning or setting selection. Evaluation uses fresh seed
2026101105, 200 independent paths, 90 burn-in and 365 measured days.

Negative paired cost differences favor expiry adjustment. Confidence intervals
are pointwise Monte Carlo intervals conditional on the selected tuning values.
If z=5 remains selected, that residual boundary is reported without further
automatic expansion. This sensitivity checks dependence on the tuning-grid cap;
it does not establish an unrestricted optimal policy.

scenario_results.csv contains liters/day for physical flow rates. Raw
replication_results.csv retains the 50 ml base unit. Purchase rates refer to order
commitments. The main run protocol, source and primary CSV hashes are recorded
in run_metadata.json and checked unchanged at completion.

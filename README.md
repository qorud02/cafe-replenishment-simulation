# Shared ingredient cafe replenishment

[한국어로 읽는 연구 결과](PLAIN_LANGUAGE_KO.md)

A controlled simulation comparing pooled mean base stock, calibrated base stock and a deterministic mean-depletion expiry correction. Generated demand is used throughout.

## Reproduce

Python 3.12.9 was used for the recorded runs. Create a local virtual environment, install requirements.txt, then run:

```text
python -m unittest test_study -v
python study.py
python study.py --sensitivity
python boundary_sensitivity.py
python make_report.py
```

The main experiment has 54 settings, 30 validation replications and 200 independent evaluation replications per setting. The sensitivity experiment has eight preselected settings, with 1,095 measured days instead of 365. Common demand paths make within-setting cost comparisons paired. Calibration and evaluation random streams are separate.

## Files

- protocol.json — scenario grid, events, costs and seeds recorded before the main run.
- study.py — independent cohort simulator and policy calibration.
- test_study.py — targeted executable scientific checks.
- results/ — full main-experiment CSVs and metadata.
- sensitivity/ — long-horizon CSVs and metadata.
- make_report.py — regenerates figures, summary and manuscript from saved results.
- manuscript.md — English research article.
- Cafe_replenishment_simulation.pdf / .docx — reading and editable document copies.
- RESULTS_REVIEW.md — independent CSV and uncertainty checks.
- figures/ — newly generated PNG and SVG charts.
- boundary-sensitivity/ — supplemental expanded-grid results for 11 validation-boundary settings.
- verify_reference.py — portable independent scalar checker.
- MODEL_REVIEW.md — independent scalar comparison and model review.

## Data dictionary

scenario_results.csv reports costs in KRW per measured day, volume columns ending in _liters_per_day in liters per day, ingredient fill_rate as a fraction, and orders_per_day as a frequency. purchased_liters_per_day means purchase commitments at the time of ordering. replication_results.csv keeps quantities in base units of 50 ml; final_inventory and final_pipeline are end-of-run quantities, not expired waste. paired_comparisons.csv is expiry-adjusted minus calibrated base stock; negative cost differences favor expiry adjustment. Its 95% intervals describe Monte Carlo uncertainty conditional on validation-selected parameters. They are pointwise intervals.

Demand parameters are known to all policies. The factor CV changes both marginal variance and cross-menu dependence. Only a one-day lead time and daily review are implemented. There is no supplier uncertainty, customer-choice model or field sales data. The expiry projection depletes current cohorts using forecast means; it is not a stochastic expected-waste calculation.

## Related software

fnb-margin-kit v0.6.0 provides the earlier static procurement calculation: https://github.com/qorud02/fnb-margin-kit/releases/tag/v0.6.0 . This simulation does not import its source, and independently implements age cohorts and repeated decisions.

## Licenses

New source code: MIT (LICENSE). New manuscript, figures and generated results: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Third-party source articles are linked and are not bundled.

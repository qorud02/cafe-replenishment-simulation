# Boundary sensitivity verification and interpretation

Completed 2026-10-11 KST. The primary experiment was preserved.

Eleven settings were selected only because at least one policy selected the original validation upper endpoint z=3. Both policies were retuned on the same original 30 validation paths over the original nine points plus 3.5,4,4.5,5. Evaluation used new seed2026101105 with200 independent replications,90 burn-in days and365 measured days.

Original nine-point validation costs reproduced the primary calibration exactly: maximum absolute difference0.0 KRW/day. Protected protocol, source, main CSVs/metadata and long-horizon CSVs/metadata remained unchanged.

## Verification

Independent standard-library CSV regrouping checked22 summary rows,4,400 replication rows,11 paired rows and286 calibration rows. Every selected coefficient matched the expanded-grid validation minimum and lower-z tie rule. Costs, liter conversions, paired differences, Student-t intervals and shared demands matched the raw replication records. Maximum CI discrepancy was below6.6e-11 KRW. See verification.json and verify_outputs.py.

## Findings

- None of22 policy fits selected the new upper endpoint z=5.
- Six fits, covering three settings, changed from z=3 to3.5: CV0, shelf-life5, shortage penalty10, packs1/3/6L. Both policies changed identically. Their paired evaluation cost differences were exactly zero.
- The remaining16 fits retained z=3.
- Across11 settings, six cost differences were negative, five exactly zero and none positive. One pointwise95% interval was entirely negative; ten included zero.
- The largest relative difference was only−0.021230%, corresponding to−3.874589 KRW/day for Q20_M5_CV0.35_P10.
- The two primary extremely small positive Q20_M3_CV0 cells changed sign on new evaluation paths and their intervals included zero. Their coefficients remained z=3, so this change cannot be attributed to grid expansion.
- The other two primary extremely small positive cells, Q60_M3_CV0_P3 and Q60_M3_CV0_P10, were not boundary-selected and were not included in this sensitivity.

The expanded grid resolves the observed tuning-cap concern for these selected settings within the tested range. It does not establish a global optimum. New evaluation paths and sometimes new selected coefficients both distinguish this analysis from the primary run; do not attribute all numerical changes to grid expansion.

This analysis was added after observing validation boundary selections. Keep it labeled as a post hoc sensitivity, separate from the frozen54-cell primary experiment. Its narrow selected conditions do not replace the primary factorial findings or the preselected eight-cell long-horizon check.

# Independent results review

Reviewed 2026-10-11 KST. Experimental source, protocol and primary result files were not edited.

## Numerical audit: pass

A standard-library CSV auditor independently regrouped all replication records, recomputed costs, service fractions, liter conversions, paired differences, standard errors, confidence limits and validation-grid choices. It did not call study.ci or reuse SciPy for the confidence calculation. The Student-t critical value was solved from the incomplete beta function: t(199, .975)=1.9719565442517357.

| Check | Main | Long horizon |
|---|---:|---:|
| Scenario summary rows | 162 | 24 |
| Replication rows | 32,400 | 4,800 |
| Paired comparison rows | 54 | 8 |
| Calibration rows | 972 | 144 |
| Negative point estimates | 44 | 8 |
| Positive point estimates | 4 | 0 |
| Exactly zero estimates | 6 | 0 |
| Pointwise CI below zero | 40 | 8 |
| Pointwise CI above zero | 4 | 0 |

All expected scenario/policy/replication identities were unique, and every group contained replication IDs0–199. All paired methods had identical demand totals at each replication. Every validation selected flag and selected_z matched the minimum validation cost and lower-z tie rule.

Maximum numerical discrepancy was below7.3e-10 KRW for summary cost confidence limits and2.5e-10 KRW for paired cost limits. Cost means, standard errors, fill-rate intervals and expiry intervals likewise matched within ordinary floating-point summation differences. No numerical reporting error was found.

Independent checking script: verify_results.py. It checks the output metrics through per-row and regrouped comparisons without importing the experimental code.

## Monetary and physical units

Primary scenario results use liters per day for named volume columns; replication results retain50ml units. Cost is KRW per measured day. The purchased field records commitments when ordering. Fill-rate differences are fractions, so multiply by100 for percentage points. Relative cost changes divide by calibrated baseline mean cost.

The largest relative reduction is Q20_M2_CV0.7_P10:−7.540173%, or−2,594.768634 KRW/day, with paired95% interval[−2,801.238853,−2,388.298415]. Ingredient fill rises0.02755333, i.e.2.755333 percentage points, while expired milk rises0.909643L/day. A headline saying that the largest cost improvement reduced waste would be false.

Four positive estimates are only+0.00513699 to+0.00986301 KRW/day, or+0.00002847% to+0.00005469%. Their confidence intervals exclude zero because Monte Carlo precision is very high. Their economic magnitude is negligible under the assumed prices; statistically above zero does not make these important policy failures. Thirteen of54 settings have absolute estimated cost differences belowKRW1/day.

The median relative difference is−0.41085084%. The equal-weight shelf-life summaries are:

| Shelf life | Mean relative difference | CIs below/above/include zero |
|---|---:|---|
| 2days |−2.88792025% |18/0/0 |
| 3days |−1.29380332% |12/4/2 |
| 5days |−0.33197913% |10/0/8 |

These are descriptions of the fixed factorial grid, not estimates over a population of cafes.

## Long-horizon check

All eight preselected CV0.70 long-horizon comparisons have negative estimates and intervals below zero. All eight signs agree with their corresponding primary settings. Relative reductions range from0.326061% to7.598336%. This supports direction stability in those selected extreme settings, not robustness of all54 primary cells. Validation is repeated on longer independent paths; differences in chosen coefficients can contribute to changes.

## Calibration boundary concern

Twenty-two of108 tuned policy-setting fits select the upper grid endpoint z=3, covering11 distinct settings. None of the16 tuned long-horizon fits selects an endpoint. Primary results are correct for the restricted grid, but an unrestricted policy optimum is not established. A validation-only expanded-grid sensitivity was requested after observing boundary selections. Its outputs must remain separate from the frozen primary experiment, with the selection rule and new evaluation seed disclosed.

## Manuscript check

The generated manuscript.md was inspected after it appeared, and the derived table values,40/4/10 interval counts,−0.41% median,8/8 long sign agreement,22 boundary fits and13 sub-KRW1 cells agree with the CSVs.

Two presentation corrections were sent to the main agent:

- The positive extreme's two-decimal display produces [+0.01,+0.01] for a nondegenerate interval. Use additional decimals or explicitly belowKRW0.01/day.
- Quantify the+2.76 percentage-point service and+0.91L/day expiry tradeoff at the maximum cost-reduction cell. The generic waste tradeoff figure alone leaves an important finding implicit.

requirements.txt was revised to NumPy2.3.5, matching run metadata. The inspected requirements also specify SciPy1.15.3 and Matplotlib3.10.8.

## Two result-grounded public sentences

1. 가상의 카페54개 조건을 비교한 시뮬레이션에서, 남은 보존기간을 발주에 반영한 규칙은44개 조건에서 평균 평가비용이 낮았고 가장 큰 차이는7.54%였습니다.
2. 가장 큰 비용 차이를 보인 조건에서는 우유 충족률이2.76%p 높아지는 동시에 폐기량도 하루0.91L 늘어, 비용과 폐기를 함께 살펴볼 필요가 있었습니다.

The44-cell statement concerns point estimates;40 cells have pointwise intervals below zero. Neither sentence describes field outcomes.

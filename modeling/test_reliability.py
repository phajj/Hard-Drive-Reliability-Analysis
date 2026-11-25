"""Check the math in reliability.py on fake drives with known answers.

    python modeling/test_reliability.py

Fake drives follow a Weibull with known k and lam. Like the real data, they enter
the study already running (left truncation) and most are still alive at the end
(right censoring). The checks:
  1. The Weibull fit recovers k and lam inside its 95% CI.
  2. Ignoring the entry age gives a wrong answer (shows why delayed entry matters).
  3. The AFR CI covers the true rate about 95% of the time.
  4. The conditional failure formula (M5) matches the simulation (M6).
  5. Piecewise-constant rates: recovers known rates per age interval; one interval gives plain F/E;
     the curve over time ends at the observed total and its range covers ~95%.
  6. A power-on-hours counter that rolled over at 65,536 gets fixed, and one that didn't is left alone.
"""
import numpy as np
import pandas as pd

from reliability import (afr_ci, interval_of, cond_fail_prob, fit_weibull, km, piecewise_curve,
                         piecewise_rates, simulate_failure_ages, unwrap_poh)

TRUE_K, TRUE_LAM = 1.8, 8.0
rng = np.random.default_rng(42)


def fake_drives(n=20000):
    life = TRUE_LAM * rng.weibull(TRUE_K, size=n * 3)
    entry = rng.uniform(0, 4, size=life.size)
    alive = life > entry                      # drives that died before entering are never seen
    life, entry = life[alive][:n], entry[alive][:n]
    end = entry + rng.uniform(0.5, 6, size=n)  # end of the study for each drive
    return pd.DataFrame({"a": entry, "t": np.minimum(life, end), "d": (life <= end).astype(int)})


PW_EDGES = [0, 1, 3, 5, np.inf]
PW_RATES = np.array([0.04, 0.015, 0.025, 0.06])  # a bathtub: high, low, rising, high


def piecewise_drives(n=40000):
    """Drives whose failure rate is PW_RATES[j] in age interval j. Each enters at age a and is
    followed up to 6 years. Failure age by inverse transform on the cumulative hazard."""
    a = rng.uniform(0, 4, size=n)
    end = a + rng.uniform(0.5, 6, size=n)
    lo, hi = np.array(PW_EDGES[:-1]), np.array(PW_EDGES[1:])
    cum = np.concatenate([[0], np.cumsum(PW_RATES[:-1] * (hi[:-1] - lo[:-1]))])  # H at each interval start
    interval = np.searchsorted(lo, a, "right") - 1
    H_a = cum[interval] + PW_RATES[interval] * (a - lo[interval])  # cumulative hazard at entry age a
    target = H_a + rng.exponential(size=n)            # alive at a, so add Exp(1) hazard
    j = np.searchsorted(cum, target, "right") - 1
    life = lo[j] + (target - cum[j]) / PW_RATES[j]
    return pd.DataFrame({"a": a, "t": np.minimum(life, end), "d": (life <= end).astype(int)})


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    return ok


def main():
    iv = fake_drives()
    results = []

    w = fit_weibull(iv)
    results.append(check("Weibull k", w["k_low"] <= TRUE_K <= w["k_high"],
                         f"true {TRUE_K}, fit {w['k']:.3f} [{w['k_low']:.3f}, {w['k_high']:.3f}]"))
    results.append(check("Weibull lam", w["lam_low"] <= TRUE_LAM <= w["lam_high"],
                         f"true {TRUE_LAM}, fit {w['lam']:.3f} [{w['lam_low']:.3f}, {w['lam_high']:.3f}]"))

    naive = fit_weibull(iv.assign(a=0.0))
    results.append(check("ignoring entry age is biased", not (naive["k_low"] <= TRUE_K <= naive["k_high"]),
                         f"naive k {naive['k']:.3f}, naive lam {naive['lam']:.3f}"))

    curve = km(iv)
    s5 = curve.loc[curve.age_years <= 5, "S"].iloc[-1]
    true_s5 = np.exp(-(5 / TRUE_LAM) ** TRUE_K)
    results.append(check("Kaplan-Meier S(5)", abs(s5 - true_s5) < 0.02, f"true {true_s5:.3f}, KM {s5:.3f}"))

    rate, exposure, trials = 0.015, 3000.0, 2000
    counts = rng.poisson(rate * exposure, size=trials)
    covered = np.mean([lo <= rate <= hi for _, lo, hi in (afr_ci(c, exposure) for c in counts)])
    results.append(check("AFR CI coverage", 0.93 <= covered <= 0.97, f"{covered:.1%} of {trials} (target 95%)"))

    a, h = np.array([1.0, 4.0, 7.0]), 2.0
    formula = cond_fail_prob(a, h, TRUE_K, TRUE_LAM)
    ages = simulate_failure_ages(a, np.full(200000, TRUE_K), np.full(200000, TRUE_LAM), rng)
    simulated = (ages <= a + h).mean(axis=0)
    results.append(check("M5 formula vs M6 simulation", np.allclose(formula, simulated, atol=0.005),
                         f"formula {np.round(formula, 4)}, simulated {np.round(simulated, 4)}"))

    results.append(check("age interval edges", list(interval_of([0.0, 0.5, 1.0, 1.01, 9.0])) == [-1, 0, 0, 1, 8],
                         "age exactly 1.0 counts in interval 0-1"))

    p = piecewise_drives()
    one = piecewise_rates(p.a, p.t, p.d, edges=[0, np.inf])
    results.append(check("one interval = plain F/E", np.isclose(one.rate[0], p.d.sum() / (p.t - p.a).sum()),
                         f"{one.rate[0]:.4f}"))
    est = piecewise_rates(p.a, p.t, p.d, edges=PW_EDGES)
    hit = ((est.rate_low <= PW_RATES) & (PW_RATES <= est.rate_high)).sum()
    results.append(check("piecewise rates recovered", hit >= len(PW_RATES) - 1,
                         f"{hit}/{len(PW_RATES)} true rates inside CI; est {np.round(est.rate.to_numpy(), 3)}"))

    first_day = rng.integers(0, 2000, size=len(p))
    end_day = first_day + (p.t - p.a).to_numpy() * 365.25
    q_start = np.arange(0, 2000 + 6 * 366, 91.0)
    curve = piecewise_curve(p.a, first_day, end_day, p.d, q_start, q_start + 91, edges=PW_EDGES)
    results.append(check("curve ends at total", np.isclose(curve["expected"][-1], p.d.sum()),
                         f"last expected {curve['expected'][-1]:.1f}, failures {p.d.sum()}"))
    per_q = np.diff(curve["expected"], prepend=0)
    sims = rng.poisson(per_q, size=(2000, per_q.size)).cumsum(axis=1)
    inside = ((sims >= curve["low"]) & (sims <= curve["high"]))[:, per_q.cumsum() > 5].mean()
    results.append(check("curve range coverage", 0.93 <= inside <= 0.99, f"{inside:.1%} of points inside (target ~95%)"))

    first = pd.Series(["2016-01-01"] * 2)
    last = pd.Series(pd.to_datetime("2016-01-01") + pd.to_timedelta([3000, 3000], unit="D"))
    fixed = unwrap_poh(pd.Series([300.0, 300.0]), pd.Series([72300.0 - 65536, 72300.0]), first, last)
    results.append(check("POH rollover fix", list(fixed) == [72300.0, 72300.0], f"{list(fixed)}"))

    print(f"\n{sum(results)}/{len(results)} passed")
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

"""Check the math in reliability.py on fake drives with known answers.

    python modeling/test_reliability.py

Fake drives follow a Weibull with known k and lam. Like the real data, they enter
the study already running (left truncation) and most are still alive at the end
(right censoring). The checks:
  1. The Weibull fit recovers k and lam inside its 95% CI.
  2. Ignoring the entry age gives a wrong answer (shows why delayed entry matters).
  3. The AFR CI covers the true rate about 95% of the time.
  4. The conditional failure formula (M5) matches the simulation (M6).
"""
import numpy as np
import pandas as pd

from reliability import afr_ci, cond_fail_prob, fit_weibull, km, simulate_failure_ages

TRUE_K, TRUE_LAM = 1.8, 8.0
rng = np.random.default_rng(42)


def fake_drives(n=20000):
    life = TRUE_LAM * rng.weibull(TRUE_K, size=n * 3)
    entry = rng.uniform(0, 4, size=life.size)
    alive = life > entry                      # drives that died before entering are never seen
    life, entry = life[alive][:n], entry[alive][:n]
    end = entry + rng.uniform(0.5, 6, size=n)  # end of the study for each drive
    return pd.DataFrame({"a": entry, "t": np.minimum(life, end), "d": (life <= end).astype(int)})


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

    print(f"\n{sum(results)}/{len(results)} passed")
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

"""Shared reliability math. Each function is one formula in MODELS.md (M1-M6).

Ages are in years of power-on time (power-on hours / 8760).
Every drive is an interval: entry age a, exit age t, failed flag d (1 or 0).
Drives were usually already running when they first show up (a > 0), so every fit
uses a as a delayed entry (left truncation).
"""
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test
from scipy.optimize import minimize
from scipy.stats import chi2

HOURS_PER_YEAR = 8760


WRAP = 2 ** 16  # some Seagate models store power-on hours in 16 bits and roll over at 65,536


def unwrap_poh(first_poh, last_poh, first_date, last_date) -> pd.Series:
    """Fix a power-on-hours counter that rolled over. If adding 65,536 hours brings the
    last reading closer to first_poh + calendar hours, the counter wrapped, so add it."""
    cal_hours = (pd.to_datetime(last_date) - pd.to_datetime(first_date)).dt.days * 24
    expected = first_poh + cal_hours
    wrapped = (last_poh + WRAP - expected).abs() < (last_poh - expected).abs()
    return last_poh + WRAP * wrapped


def intervals(df: pd.DataFrame, entry="first_poh", exit="last_poh", event="failed",
              dates=("first_date", "last_date")) -> pd.DataFrame:
    """Turn power-on hours into (a, t, d) in years. Unwraps 16-bit rollover when the
    date columns are there. Drops drives with no time at risk (t <= a)."""
    last = df[exit]
    if dates and all(c in df for c in dates):
        last = unwrap_poh(df[entry], last, df[dates[0]], df[dates[1]])
    out = pd.DataFrame({
        "a": df[entry] / HOURS_PER_YEAR,
        "t": last / HOURS_PER_YEAR,
        "d": df[event].astype(int),
    }, index=df.index)
    return out[(out.t > out.a) & out.a.ge(0)]


# M1 --------------------------------------------------------------------------
def afr_ci(failures: float, drive_years: float, level=0.95) -> tuple[float, float, float]:
    """AFR = F / E with the exact Poisson (Garwood) confidence interval."""
    alpha = 1 - level
    f, e = float(failures), float(drive_years)
    low = chi2.ppf(alpha / 2, 2 * f) / (2 * e) if f > 0 else 0.0
    high = chi2.ppf(1 - alpha / 2, 2 * f + 2) / (2 * e)
    return f / e, low, high


# M2 --------------------------------------------------------------------------
def rate_ratio(f1, e1, f0, e0, level=0.95) -> tuple[float, float, float]:
    """Rate ratio (group 1 vs reference group 0) with a log-scale normal CI."""
    z = _z(level)
    rr = (f1 / e1) / (f0 / e0)
    se = np.sqrt(1 / f1 + 1 / f0)
    return rr, rr * np.exp(-z * se), rr * np.exp(z * se)


# M3 --------------------------------------------------------------------------
def km(iv: pd.DataFrame, label=None, min_at_risk=100) -> pd.DataFrame:
    """Kaplan-Meier curve with delayed entry and Greenwood CI.
    Cut where fewer than min_at_risk drives are at risk."""
    f = KaplanMeierFitter(label=label).fit(iv.t, iv.d, entry=iv.a)
    curve = pd.concat([f.survival_function_, f.confidence_interval_], axis=1)
    curve.columns = ["S", "S_low", "S_high"]
    at_risk = f.event_table["at_risk"].reindex(curve.index)
    curve["at_risk"] = at_risk.values
    return curve[curve.at_risk >= min_at_risk].rename_axis("age_years").reset_index()


def logrank(iv1: pd.DataFrame, iv0: pd.DataFrame) -> float:
    """Log-rank test p-value between two groups, with delayed entry."""
    return logrank_test(iv1.t, iv0.t, iv1.d, iv0.d, entry_A=iv1.a, entry_B=iv0.a).p_value


# M4 --------------------------------------------------------------------------
def weibull_loglik(theta, a, t, d) -> float:
    """l(k, lam) = sum[ d*ln h(t) - (t/lam)^k + (a/lam)^k ], with theta = (ln lam, ln k).
    ln h(t) = ln k - ln lam + (k-1) ln(t/lam)."""
    log_lam, log_k = theta
    lam, k = np.exp(log_lam), np.exp(log_k)
    log_h = log_k - log_lam + (k - 1) * (np.log(t) - log_lam)
    return np.sum(d * log_h - (t / lam) ** k + (a / lam) ** k)


def fit_weibull(iv: pd.DataFrame) -> dict:
    """Weibull MLE with censoring and left truncation. S(t) = exp(-(t/lam)^k).
    Fitted on the log scale (ln lam, ln k) so both stay positive; 95% CIs from the
    inverse of the observed Fisher information (numerical Hessian)."""
    a, t, d = (iv[c].to_numpy(float) for c in ("a", "t", "d"))
    nll = lambda th: -weibull_loglik(th, a, t, d)
    # Start from the exponential fit (k = 1): lam = exposure / failures.
    start = np.array([np.log((t - a).sum() / max(d.sum(), 1)), 0.0])
    res = minimize(nll, start, method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 5000})
    res = minimize(nll, res.x, method="BFGS")
    cov_log = np.linalg.inv(_hessian(nll, res.x))
    se = np.sqrt(np.diag(cov_log))
    lam, k = np.exp(res.x)
    z = _z(0.95)
    return {
        "k": k, "k_low": k * np.exp(-z * se[1]), "k_high": k * np.exp(z * se[1]),
        "lam": lam, "lam_low": lam * np.exp(-z * se[0]), "lam_high": lam * np.exp(z * se[0]),
        "median_life": weibull_quantile(0.5, k, lam),
        "b10_life": weibull_quantile(0.1, k, lam),
        "drives": len(iv), "failures": int(iv.d.sum()),
        "converged": bool(res.success),
        "cov_log": cov_log,  # covariance of (ln lam, ln k), used by the simulation
    }


def _hessian(f, x, eps=1e-4):
    """Central-difference Hessian of f at x."""
    n = len(x)
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            ei, ej = np.eye(n)[i] * eps, np.eye(n)[j] * eps
            H[i, j] = (f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej) + f(x - ei - ej)) / (4 * eps ** 2)
    return H


def weibull_S(t, k, lam):
    return np.exp(-(np.asarray(t) / lam) ** k)


def weibull_quantile(p, k, lam):
    """Age by which a fraction p have failed: lam * (-ln(1-p))^(1/k)."""
    return lam * (-np.log(1 - p)) ** (1 / k)


# M5 --------------------------------------------------------------------------
def cond_fail_prob(a, h, k, lam):
    """P(fail before a+h | alive at a) = 1 - S(a+h)/S(a)."""
    a = np.asarray(a, dtype=float)
    return 1 - np.exp(-((a + h) / lam) ** k + (a / lam) ** k)


# M6 --------------------------------------------------------------------------
def draw_params(fit: dict, runs: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Draw (k, lam) per run from a normal on the log scale, using the MLE covariance."""
    mean = np.log([fit["lam"], fit["k"]])
    draws = np.exp(rng.multivariate_normal(mean, fit["cov_log"], size=runs))
    return draws[:, 1], draws[:, 0]  # k, lam


def simulate_failure_ages(a, k, lam, rng: np.random.Generator) -> np.ndarray:
    """Inverse transform: T = lam * ((a/lam)^k - ln U)^(1/k).
    a: ages now (n drives). k, lam: one value per run (shape runs).
    Returns the failure ages, shape (runs, n)."""
    a = np.asarray(a, dtype=float)[None, :]
    k = np.asarray(k, dtype=float)[:, None]
    lam = np.asarray(lam, dtype=float)[:, None]
    u = rng.random((k.shape[0], a.shape[1]))
    return lam * ((a / lam) ** k - np.log(u)) ** (1 / k)


def _z(level):
    from scipy.stats import norm
    return norm.ppf(1 - (1 - level) / 2)

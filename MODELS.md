# Models

The math models we use. The code is in `modeling/reliability.py`.

- **Drive-year:** one drive running for one year.
- **Failure rate:** failures per drive-year, written as a percent (AFR, annualized failure rate).

## M1. Constant failure rate

Code: `afr_ci()`

### Idea
Every drive-year has the same small chance $r$ of a failure. It doesn't matter how old the drive is.

### Variables
- $n$ = number of drives
- $E$ = total drive-years for all $n$ drives
- $F$ = total failures
- $r$ = failure rate (failures per drive-year)

### Model
Failures are Poisson:

$\displaystyle F \sim \text{Poisson}(rE)$

### Estimate (maximum likelihood)

$\displaystyle \ell(r) = -rE + F \ln(rE)$

$\displaystyle \frac{d\ell}{dr} = -E + \frac{F}{r} = 0 \quad\Rightarrow\quad \hat r = \frac{F}{E}$

### 95% confidence interval

$\displaystyle \left[\frac{\chi^2_{0.025}(2F)}{2E},\ \frac{\chi^2_{0.975}(2F + 2)}{2E}\right]$

### Example (5900 RPM)
$F = 788$, $E \approx 29{,}300$ drive-years

$\displaystyle \hat r = \frac{788}{29{,}300} \approx 2.69\% \text{ per year}, \qquad \text{95\% CI } (2.50\%,\ 2.88\%)$

## Why we switched to M1b

M1 says the rate never changes with age. When we drew M1 on the failure charts, the real totals fell outside its 95% range in 18–20 of 54 quarters for every RPM class. Drives don't fail at one steady rate. They follow a "bathtub": more failures when new, fewer in the middle years, more again as they wear out.

M1b keeps M1's math but gives each age interval its own rate. This makes the model more precise without making it harder: each interval is just M1 on its own.

## M1b. Piecewise-constant failure rate (rate by drive age)

Code: `piecewise_rates()` and `piecewise_curve()`. This is the model on the site's charts.

### Variables
- $n$ = number of drives
- $a_i$ = age of drive $i$ when first seen (years)
- $t_i$ = age of drive $i$ when last seen (years)
- $\delta_i$ = 1 if drive $i$ failed, 0 if not
- $b_0, b_1, \dots, b_J$ = age interval edges $(0, 1, 2, \dots, 8, \infty)$
- $r_j$ = failure rate in age interval $j$ (failures per drive-year)
- $E_j$ = drive-years spent in interval $j$
- $F_j$ = failures in interval $j$

A drive's age is its power-on hours at the first report ÷ 8,760, plus the time since.

### Model
The failure rate is constant within each age interval:

$\displaystyle r(x) = r_j \quad \text{for } b_{j-1} < x \le b_j$

### Exposure in each interval

$\displaystyle E_j = \sum_{i=1}^{n} \max\big(0,\ \min(t_i, b_j) - \max(a_i, b_{j-1})\big)$

### Failures in each interval are Poisson

$\displaystyle F_j \sim \text{Poisson}(r_j E_j)$

### Estimate (maximum likelihood)

$\displaystyle \ell(r_j) = -r_j E_j + F_j \ln(r_j E_j)$

$\displaystyle \frac{d\ell}{dr_j} = -E_j + \frac{F_j}{r_j} = 0 \quad\Rightarrow\quad \hat r_j = \frac{F_j}{E_j}$

### 95% confidence interval

$\displaystyle \left[\frac{\chi^2_{0.025}(2F_j)}{2E_j},\ \frac{\chi^2_{0.975}(2F_j + 2)}{2E_j}\right]$

### Example (7200 RPM, age 2–3 years)
$F = 40$, $E = 4{,}580$ drive-years

$\displaystyle \hat r = \frac{40}{4{,}580} \approx 0.87\% \text{ per year}, \qquad \text{95\% CI } (0.62\%,\ 1.19\%)$

With one interval ($b_0 = 0$, $b_1 = \infty$), M1b is exactly M1.

### The chart line
The expected total failures by quarter $q$ add up each interval's rate × the drive-years spent in that interval so far ($E_{jp}$ = drive-years in interval $j$ during quarter $p$):

$\displaystyle \mu_q = \sum_{p=1}^{q} \sum_{j=1}^{J} \hat r_j \, E_{jp}$

The shaded range is the 95% range of $\text{Poisson}(\mu_q)$.

### Results (main sample)
Quarters where the real total falls outside the 95% range, out of 54:

| Class | M1 | M1b |
|---|---|---|
| 5700 RPM | 19 | 7 |
| 5900 RPM | 18 | 25 |
| 7200 RPM | 20 | 6 |

- **7200 RPM** is a bathtub: 1.54% in year 1, 0.87% at 2–3 years, 2.43% at 6–7 years.
- **5700 RPM** is low at every age (0.2%–0.6%).
- **5900 RPM** fits worse. Its failures piled up in 2015–2017 at every age, so the cause is tied to *when*, not *how old*. An age model can't capture that.

### Assumptions
- The rate depends only on age.
- Drives fail independently.
- Drives run 24/7, so age goes up one day per calendar day.

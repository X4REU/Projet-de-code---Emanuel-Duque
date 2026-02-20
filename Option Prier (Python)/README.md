# Pricing Options

Complete guide to the European and American option pricing project.

---

## Overview

```text
Step 1: main.py   -> retrieves market data, prices the option, computes Greeks
Step 2: main.py   -> generates charts (payoff + Greeks curves)
Step 3: report.py -> exports a professional PDF (except comparison mode)
```

The program is interactive (CLI): you enter the parameters, it performs all calculations and generates the report.

---

## Project Structure

| File | Role | Output |
|------|------|--------|
| `main.py` | Main pipeline: input, market data, pricing, Greeks, charts | Console output + in-memory images + export call |
| `report.py` | PDF layout (header/footer, KPIs, payoff, Greeks) | `report/{ticker}_{style}_{type}_{position}.pdf` |
| `report/` | Generated reports folder | Final PDFs |

---

## Installation

### Requirements

- Python 3.10+
- Internet connection (required for `yfinance`)

### Install dependencies

```bash
pip install numpy scipy matplotlib yfinance fpdf2 py_vollib
```

### Run the program

```bash
python main.py
```

---

## Detailed Execution Flow (`main.py`)

### 1) User Input Collection

The script prompts for:

1. `ticker` (e.g., `AAPL`)
2. `style` (`european`, `american`, `comparison`)
3. `K` (strike)
4. `T` (maturity in years)
5. `option_type` (`call` / `put`)
6. `position` (`long` / `short`)

Typing `stop` at any prompt cleanly exits the program.

---

### 2) Market Data (`get_market_data`)

**Sources:**
- `yfinance` for the underlying asset
- `^IRX` for the risk-free rate

**Computed variables:**

- `S`: latest close price of the ticker
- `sigma`: annualized volatility from log-returns (`std * sqrt(252)`)
- `r`: latest close of `^IRX`, converted into a rate
- `q`: `dividendYield` from `stock.info` (0 if unavailable)

---

### 3) Pricing

- **European option**: Black-Scholes-Merton (`price_eu_bs`)
- **American option**: Binomial tree (`price_am_binomial`, `N=200`)

Console output:

- `european` mode: EU price
- `american` mode: US price
- `comparison` mode: EU price + US price + spread `US - EU`

---

### 4) Greeks

- **European**: Analytical formulas via `py_vollib`  
  (`delta`, `gamma`, `vega`, `theta`, `rho`)

- **American**: Finite differences around the binomial price (`greeks_am_fd`)

Normalizations applied (US side):

```python
vega_am = vega_am * 0.01
rho_am = rho_am * 0.01
theta_am = theta_am / 365.0
```

---

### 5) Charts (`generate_charts`)

Generated in memory (PNG via `BytesIO`):

- Payoff
- Delta
- Gamma
- Vega
- Theta
- Rho

Notes:

- In `comparison` mode, EU and US curves are plotted together for each Greek.
- Chart images are passed directly to `report.py` (no intermediate files).

---

### 6) PDF Export (`export_pdf` in `report.py`)

Export enabled for:

- `european`
- `american`

No export in `comparison` mode (current behavior).

File naming convention:

```text
report/{TICKER}_{style}_{option_type}_{position}.pdf
```

Example:

```text
report/AAPL_european_call_long.pdf
```

---

## Key Functions

### `price_eu_bs(S, K, T, r, q, sigma, option_type)`

Black-Scholes-Merton formula:

```python
d1 = (ln(S/K) + (r - q + 0.5*sigma^2)*T) / (sigma*sqrt(T))
d2 = d1 - sigma*sqrt(T)
call = S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2)
put  = K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1)
```

---

### `price_am_binomial(..., N=200)`

Recombining binomial tree:

- Construct payoffs at maturity
- Backward induction
- Early exercise at each node:

```python
max(continuation, exercise)
```

---

### `greeks_am_fd(...)`

Numerical approximation of sensitivities:

- Delta / Gamma: perturbation on `S`
- Vega: perturbation on `sigma`
- Rho: perturbation on `r`
- Theta: perturbation on `T`

---

### `payoff_net(option_type, position, S_T, K, premium)`

Net payoff (used for payoff chart):

- long: gross payoff − premium
- short: −gross payoff + premium

---

## PDF Report (`report.py`)

The generated PDF is structured in two pages:

### Page 1 – Indicators

- KPI cards (`Spot`, `Strike`, `Maturity`, `Volatility`, `Premium`)
- Table of additional inputs

### Page 2 – Greeks

- Summary row (`Delta`, `Gamma`, `Vega`, `Theta`, `Rho`)
- Grid of Greeks charts

### Visual Elements

- Custom header and footer
- Generation date
- Report title and pagination

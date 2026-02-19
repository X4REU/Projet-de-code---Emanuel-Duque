import math
import sys
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
from scipy.stats import norm
from report import export_pdf

def lire_input(message):
    val = input(message).strip()
    if val.lower() == "stop":
        print("Arrêt du programme.")
        sys.exit()
    return val

def get_market_data(ticker, lookback="1y"):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=lookback)

    if hist.empty:
        raise ValueError("Pas de données pour ce ticker.")

    S = float(hist["Close"].iloc[-1])

    log_returns = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
    sigma = float(log_returns.std() * np.sqrt(252))

    irx = yf.Ticker("^IRX").history(period="5d")
    if irx.empty:
        raise ValueError("Pas de taux ^IRX.")
    r = float(irx["Close"].iloc[-1]) / 100.0

    info = stock.info
    q = float(info.get("dividendYield") or 0.0) / 100.0

    return S, r, sigma, q

def demander_choix(message, choix):
    choix = tuple(c.lower() for c in choix)
    while True:
        val = lire_input(message).lower()
        if val in choix:
            return val
        print(f"Choix invalide. Options: {', '.join(choix)}")

def demander_float(message, min_value=None):
    while True:
        txt = lire_input(message).replace(",", ".")
        try:
            x = float(txt)
            if min_value is not None and x < min_value:
                print(f"Valeur invalide: doit être >= {min_value}")
                continue
            return x
        except ValueError:
            print("Entrée invalide. Tapez un nombre.")

def payoff_net(option_type, position, S_T, K, premium):
    if option_type == "call":
        brut = max(S_T - K, 0.0)
    else:
        brut = max(K - S_T, 0.0)

    if position == "long":
        return brut - premium
    return -brut + premium

def price_eu_bs(S, K, T, r, q, sigma, option_type):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def greeks_eu_bs(S, K, T, r, q, sigma, option_type):
    try:
        from py_vollib.black_scholes_merton.greeks.analytical import (
            delta as bsm_delta,
            gamma as bsm_gamma,
            rho as bsm_rho,
            theta as bsm_theta,
            vega as bsm_vega,
        )
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "py_vollib n'est pas installe. Installez-le avec: pip install py_vollib"
        )

    flag = "c" if option_type == "call" else "p"
    delta = bsm_delta(flag, S, K, T, r, sigma, q)
    gamma = bsm_gamma(flag, S, K, T, r, sigma, q)
    vega = bsm_vega(flag, S, K, T, r, sigma, q)
    theta = bsm_theta(flag, S, K, T, r, sigma, q)
    rho = bsm_rho(flag, S, K, T, r, sigma, q)
    return delta, gamma, vega, theta, rho


def price_am_binomial(S, K, T, r, q, sigma, option_type, N=200):
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    if not (0 <= p <= 1):
        raise ValueError("Paramètres incohérents pour l'arbre binomial (p hors [0,1]).")

    values = []
    for j in range(N + 1):
        S_T = S * (u ** j) * (d ** (N - j))
        if option_type == "call":
            values.append(max(S_T - K, 0.0))
        else:
            values.append(max(K - S_T, 0.0))

    for i in range(N - 1, -1, -1):
        new_values = []
        for j in range(i + 1):
            continuation = disc * (p * values[j + 1] + (1 - p) * values[j])
            S_ij = S * (u ** j) * (d ** (i - j))
            if option_type == "call":
                exercise = max(S_ij - K, 0.0)
            else:
                exercise = max(K - S_ij, 0.0)
            new_values.append(max(continuation, exercise))
        values = new_values
    return values[0]


def greeks_am_fd(S, K, T, r, q, sigma, option_type, N=200):
    hS = max(0.01, 0.01 * S)
    hSigma = 0.01
    hR = 0.0001
    hT = min(1.0 / 365.0, T / 2.0)

    base = price_am_binomial(S, K, T, r, q, sigma, option_type, N)
    v_up_S = price_am_binomial(S + hS, K, T, r, q, sigma, option_type, N)
    v_dn_S = price_am_binomial(max(S - hS, 1e-12), K, T, r, q, sigma, option_type, N)
    delta = (v_up_S - v_dn_S) / (2 * hS)
    gamma = (v_up_S - 2 * base + v_dn_S) / (hS ** 2)

    v_up_sigma = price_am_binomial(S, K, T, r, q, sigma + hSigma, option_type, N)
    v_dn_sigma = price_am_binomial(S, K, T, r, q, max(sigma - hSigma, 1e-12), option_type, N)
    vega = (v_up_sigma - v_dn_sigma) / (2 * hSigma)

    v_up_r = price_am_binomial(S, K, T, r + hR, q, sigma, option_type, N)
    v_dn_r = price_am_binomial(S, K, T, r - hR, q, sigma, option_type, N)
    rho = (v_up_r - v_dn_r) / (2 * hR)

    v_up_T = price_am_binomial(S, K, T + hT, r, q, sigma, option_type, N)
    v_dn_T = price_am_binomial(S, K, max(T - hT, 1e-12), r, q, sigma, option_type, N)
    theta = (v_up_T - v_dn_T) / (2 * hT)
    return delta, gamma, vega, theta, rho


def generate_charts(style, option_type, position, premium, S, K, T, r, q, sigma):
    chart_images = []

    S_payoff = np.linspace(0.5 * K, 1.5 * K, 200)
    payoff_net_vals = np.array([payoff_net(option_type, position, s, K, premium) for s in S_payoff])
    plt.figure(figsize=(8, 4.5), facecolor="white")
    ax = plt.gca()
    ax.set_facecolor("white")
    ax.fill_between(S_payoff, payoff_net_vals, 0, where=payoff_net_vals >= 0, color="#6AAE7B", alpha=0.9)
    ax.fill_between(S_payoff, payoff_net_vals, 0, where=payoff_net_vals < 0, color="#C44E52", alpha=0.9)
    ax.plot(S_payoff, payoff_net_vals, color="#1B1F23", linewidth=2.2)
    ax.axhline(0, color="#1B1F23", linewidth=1.1, alpha=0.7)
    ax.set_title("Payoff")
    ax.grid(axis="y", color="#D0D7DE", alpha=0.6, linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#1B1F23")
    ax.spines["bottom"].set_color("#1B1F23")
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close()
    buf.seek(0)
    chart_images.append({"name": "Payoff", "data": buf.getvalue()})

    n_points = 18 if style in ("americaine", "comparaison") else 40
    S_grid = np.linspace(0.6 * S, 1.4 * S, n_points)
    eu_vals = {"Delta": [], "Gamma": [], "Vega": [], "Theta": [], "Rho": []}
    am_vals = {"Delta": [], "Gamma": [], "Vega": [], "Theta": [], "Rho": []}

    for s in S_grid:
        d_eu, g_eu, v_eu, t_eu, r_eu = greeks_eu_bs(s, K, T, r, q, sigma, option_type)
        eu_vals["Delta"].append(d_eu)
        eu_vals["Gamma"].append(g_eu)
        eu_vals["Vega"].append(v_eu)
        eu_vals["Theta"].append(t_eu)
        eu_vals["Rho"].append(r_eu)
        if style in ("americaine", "comparaison"):
            d_am, g_am, v_am, t_am, r_am = greeks_am_fd(s, K, T, r, q, sigma, option_type, N=120)
            v_am = v_am * 0.01
            r_am = r_am * 0.01
            t_am = t_am / 365.0
            am_vals["Delta"].append(d_am)
            am_vals["Gamma"].append(g_am)
            am_vals["Vega"].append(v_am)
            am_vals["Theta"].append(t_am)
            am_vals["Rho"].append(r_am)

    for greek in ["Delta", "Gamma", "Vega", "Theta", "Rho"]:
        plt.figure(figsize=(8, 4.5), facecolor="white")
        ax = plt.gca()
        ax.set_facecolor("white")
        if style == "americaine":
            ax.plot(S_grid, am_vals[greek], color="#1B1F23", linewidth=2)
        elif style == "comparaison":
            ax.plot(S_grid, eu_vals[greek], color="#1B1F23", linewidth=2)
            ax.plot(S_grid, am_vals[greek], color="#1B1F23", linewidth=2, linestyle="--")
        else:
            ax.plot(S_grid, eu_vals[greek], color="#1B1F23", linewidth=2)
        ax.set_title("")
        ax.grid(axis="y", color="#D0D7DE", alpha=0.6, linewidth=0.8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color("#1B1F23")
        ax.spines["bottom"].set_color("#1B1F23")
        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close()
        buf.seek(0)
        chart_images.append({"name": greek, "data": buf.getvalue()})

    return chart_images

while True:
    ticker = lire_input("Ticker (ex: AAPL): ").upper()
    try:
        S, r, sigma, q = get_market_data(ticker)
        print(f"S={S:.3f}, r={r:.4%}, sigma={sigma:.2%}, q={q:.2%}")
        break
    except Exception as e:
        print(f"Erreur données ticker: {e}")
        print("Réessayez avec un autre ticker (ou tapez stop).")

style = demander_choix("Style (europeenne/americaine/comparaison): ",("europeenne", "americaine", "comparaison"),)

K = demander_float("Strike: ", min_value=1e-12)
T = demander_float("Maturité: ", min_value=1e-12)
option_type = demander_choix("Call or Put (call/put): ", ("call", "put"))
position = demander_choix("Position (long/short): ", ("long", "short"))

print("\nParamètres saisis:")
print(
    f"style={style}, S={S:.4f}, K={K:.4f}, T={T:.4f}, "
    f"r={r:.2%}, q={q:.2%}, sigma={sigma:.2%}, "
    f"type={option_type}, position={position}"
)

try:
    price_eu = price_eu_bs(S, K, T, r, q, sigma, option_type)
    delta, gamma, vega, theta, rho = greeks_eu_bs(S, K, T, r, q, sigma, option_type)
except ModuleNotFoundError as e:
    print(str(e))
    sys.exit()

try:
    price_am = price_am_binomial(S, K, T, r, q, sigma, option_type, N=200)
    delta_am, gamma_am, vega_am, theta_am, rho_am = greeks_am_fd(
        S, K, T, r, q, sigma, option_type, N=200
    )
    vega_am = vega_am * 0.01
    rho_am = rho_am * 0.01
    theta_am = theta_am / 365.0
except ValueError as e:
    print(str(e))
    sys.exit()

if style == "americaine":
    premium = price_am
else:
    premium = price_eu

if style in ("europeenne", "comparaison"):
    print(f"Prix européenne ({option_type}) = {price_eu:.4f}")

if style in ("americaine", "comparaison"):
    print(f"Prix américain ({option_type}) = {price_am:.4f}")

if style == "comparaison":
    diff = price_am - price_eu
    print(f"Différence (US - EU) = {diff:.4f}")

if style in ("europeenne", "comparaison"):
    print("\nGreeks (européenne):")
    print(f"Delta = {delta:.3f}")
    print(f"Gamma = {gamma:.3f}")
    print(f"Vega  = {vega:.3f}")
    print(f"Theta = {theta:.3f}")
    print(f"Rho   = {rho:.3f}")

if style in ("americaine", "comparaison"):
    print("\nGreeks (américaine):")
    print(f"Delta = {delta_am:.3f}")
    print(f"Gamma = {gamma_am:.3f}")
    print(f"Vega  = {vega_am:.3f}")
    print(f"Theta = {theta_am:.3f}")
    print(f"Rho   = {rho_am:.3f}")

ticker_label = ticker

chart_images = generate_charts(style, option_type, position, premium, S, K, T, r, q, sigma)
if style != "comparaison":
    print(f"Graphiques generes: {', '.join(img['name'] for img in chart_images)}")

results = {
    "inputs": {
        "style": style,
        "option_type": option_type,
        "position": position,
        "premium": premium,
        "S": S,
        "K": K,
        "T": T,
        "r": r,
        "q": q,
        "sigma": sigma,
    },
    "outputs": {
        "delta_eu": delta,
        "gamma_eu": gamma,
        "vega_eu": vega,
        "theta_eu": theta,
        "rho_eu": rho,
        "delta_am": delta_am,
        "gamma_am": gamma_am,
        "vega_am": vega_am,
        "theta_am": theta_am,
        "rho_am": rho_am,
    },
}

reports_dir = Path("report")
reports_dir.mkdir(exist_ok=True)
report_name = f"{ticker_label}_{style}_{option_type}_{position}.pdf"
report_path = reports_dir / report_name
if style != "comparaison":
    export_pdf(results, str(report_path), chart_images=chart_images)
    print(f"PDF genere: {report_path}")

#export en PDF (améliorer le visuel)
#vérifier les calculs de Vega et Theta et Rho
#pas de PDF quand comparaison

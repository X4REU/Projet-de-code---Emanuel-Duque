# Pricing options

Guide complet du projet de pricing d'options (EU vs US), génération de graphiques et export PDF.

---

## Vue d'ensemble

```text
Étape 1: main.py   -> récupère les données marché, valorise l'option, calcule les Greeks
Étape 2: main.py   -> génère les graphiques (payoff + courbes de Greeks)
Étape 3: report.py -> exporte un PDF professionnel (sauf mode comparaison)
```

Le programme est interactif (CLI): vous entrez les paramètres, il calcule tout et génère le rapport.

---

## Arborescence

| Fichier | Rôle | Sortie |
|---|---|---|
| `main.py` | Pipeline principal: input, market data, pricing, Greeks, charts | Affichage console + images en mémoire + appel export |
| `report.py` | Mise en page PDF (header/footer, KPI, payoff, Greeks) | `report/{ticker}_{style}_{type}_{position}.pdf` |
| `report/` | Dossier des rapports générés | PDF finaux |

---

## Installation

Pré-requis:
- Python 3.10+
- Connexion internet (requise pour `yfinance`)

Installer les dépendances:

```bash
pip install numpy scipy matplotlib yfinance fpdf2 py_vollib
```

Lancer:

```bash
python main.py
```

---

## Flux d'exécution détaillé (`main.py`)

### 1) Collecte des inputs utilisateur

Le script demande:
1. `ticker` (ex: `AAPL`)
2. `style` (`europeenne`, `americaine`, `comparaison`)
3. `K` (strike)
4. `T` (maturité en années)
5. `option_type` (`call` / `put`)
6. `position` (`long` / `short`)

`stop` à n'importe quel prompt quitte proprement le programme.

### 2) Données marché (`get_market_data`)

Sources:
- `yfinance` pour le sous-jacent
- `^IRX` pour le taux sans risque

Calculs:
- `S`: dernier close du ticker
- `sigma`: volatilité annualisée à partir des log-returns (`std * sqrt(252)`)
- `r`: dernier close de `^IRX` converti en taux
- `q`: `dividendYield` de `stock.info` (0 si absent)

### 3) Pricing

- **Européenne**: Black-Scholes-Merton (`price_eu_bs`)
- **Américaine**: arbre binomial (`price_am_binomial`, `N=200`)

Sortie console:
- mode `europeenne`: prix EU
- mode `americaine`: prix US
- mode `comparaison`: prix EU + prix US + écart `US - EU`

### 4) Greeks

- **EU**: analytiques via `py_vollib` (`delta`, `gamma`, `vega`, `theta`, `rho`)
- **US**: différences finies autour du prix binomial (`greeks_am_fd`)

Normalisations appliquées côté US:
- `vega_am = vega_am * 0.01`
- `rho_am = rho_am * 0.01`
- `theta_am = theta_am / 365.0`

### 5) Graphiques (`generate_charts`)

Génère en mémoire (PNG via `BytesIO`):
- `Payoff`
- `Delta`
- `Gamma`
- `Vega`
- `Theta`
- `Rho`

Notes:
- en mode `comparaison`, les courbes EU et US sont tracées ensemble pour chaque Greek
- les chart images sont passées à `report.py` sans fichiers intermédiaires

### 6) Export PDF (`export_pdf` dans `report.py`)

Export activé pour:
- `europeenne`
- `americaine`

Pas d'export en mode `comparaison` (comportement actuel du code).

Nom de fichier:

```text
report/{TICKER}_{style}_{option_type}_{position}.pdf
```

Exemple:

```text
report/AAPL_europeenne_call_long.pdf
```

---

## Fonctions clés

### `price_eu_bs(S, K, T, r, q, sigma, option_type)`

Formule Black-Scholes-Merton:

```python
d1 = (ln(S/K) + (r - q + 0.5*sigma^2)*T) / (sigma*sqrt(T))
d2 = d1 - sigma*sqrt(T)
call = S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2)
put  = K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1)
```

### `price_am_binomial(..., N=200)`

Arbre binomial recombiné:
- construction des payoffs à maturité
- backward induction
- exercice anticipé à chaque noeud (`max(continuation, exercise)`)

### `greeks_am_fd(...)`

Approximation numérique des sensibilités:
- Delta/Gamma: perturbation sur `S`
- Vega: perturbation sur `sigma`
- Rho: perturbation sur `r`
- Theta: perturbation sur `T`

### `payoff_net(option_type, position, S_T, K, premium)`

Payoff net long/short (utilisé pour le graphe payoff):
- long: payoff brut - premium
- short: -payoff brut + premium

---

## Rapport PDF (`report.py`)

Le PDF est structuré en deux pages:
1. **Indicateurs**:
   - cartes KPI (`Spot`, `Strike`, `Maturite`, `Volatilité`, `Premium`)
   - tableau des autres inputs
2. **Greeks**:
   - ligne résumé (`Delta`, `Gamma`, `Vega`, `Theta`, `Rho`)
   - grille de graphiques des Greeks

Éléments visuels:
- Header/Footer personnalisés
- Date de génération
- Nom du rapport + pagination


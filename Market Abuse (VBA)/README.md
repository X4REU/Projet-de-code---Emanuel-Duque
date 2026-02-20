# Code Guide: Market Abuse

Complete guide to the VBA architecture (UserForms, loaders, analysis engine, and Word/PDF reporting).

---

## Pipeline Overview

```text
Step 0: UserLogin / UserRegister           -> User authentication
Step 1: dataGui + Loaders.bas              -> Import / refresh market data via Alpha Vantage
Step 2: managerGui + ClientManager.bas     -> Client creation + trade entry
Step 3: analyzerGui + AnalyzerAndTrackers  -> Behavioral analysis + scoring + data_output export
Step 4: analyzerGui + WordReporting.bas    -> Word + PDF reporting package generation
```

---

## Module Map

| File | Role | Main Outputs |
|------|------|-------------|
| `main.bas` | Entry points to open UserForms | opens `managerGui`, `dataGui`, `analyzerGui` |
| `Loaders.bas` | API import + refresh + API counter | `data/{TICKER}.xlsx`, `data/__{TICKER}.xlsx`, updates `HiddenSettings` |
| `ClientManager.bas` | Client identity + lookup/filter | writes clients to `Transactions!N:Q` |
| `Add Trade.bas` | Trade validation + transaction insertion | writes trades to `Transactions!B:L` |
| `AnalyzerAndTrackers.bas` | Indicators + scoring + dashboard writeback | updates `DashBoard`, exports `reporting/data_output/data_*.xlsx` |
| `WordReporting.bas` | Word template fill + PDF/doc export | `reporting_{ID}_doc_package/` + PDF |
| `Logs.bas` | Login, registration, user metadata | reads/writes `User` sheet |
| `Utils.bas` | Utility functions (paths) | `GetCurrentPath()` |
| `UserLogin.frm` / `UserRegister.frm` | Login/register GUI | active session stored in `DashBoard!T4:T7` |
| `dataGui.frm` | Data management GUI | triggers API import |
| `managerGui.frm` | Client/trade management GUI | triggers client/trade creation |
| `AnalyzerGui.frm` | Analysis/reporting GUI | triggers analysis and reporting export |

---

# Important Information

This section explains the purpose of the different folders included in the package.

## `data/` Folder

The `data` folder contains all market data files (“APIs”) imported using the **Data** button in the Excel file.

- Each imported ticker generates a main file: `data/{TICKER}.xlsx`
- During a refresh process, a temporary file may be used: `data/__{TICKER}.xlsx`

---

## `data/symbol_list_avapi/` Folder

This folder contains two files:

- `config.xlsx`: tracks the number of API calls performed, with a limit of **25 calls per day**
- `symbol_list.csv`: serves as the database listing all importable tickers (asset universe)

---

## `reporting/` Folder

Inside the `reporting` folder, you will find two subfolders:

- `reporting/data_output/`
- `reporting/reporting_1_doc_package/` *(example for ID = 1)*

These folders are directly linked to the functions triggered by the **Analyzer** button in the Excel file.

### `reporting/data_output/`

Contains the detailed datasets used to perform the client transaction analysis:

- structured exports `data_{id}_*.xlsx`
- intermediate datasets used for indicator computation and scoring

### `reporting/reporting_1_doc_package/`

Contains the ready-to-send reporting package:

- pre-filled suspicious transaction report form
- exported PDF and original Word document
- copies of the related `data_{id}_*.xlsx` files

> Note: The folder name varies depending on the analyzed ID: `reporting_{id}_doc_package/`.

---

# Admin Info

To access the file without creating a new user account, you can use the following credentials:

- **Email:** `admin`  
- **Password:** `admin`  
- **Workbook password:** `admin` *(required to display the ribbon)*

---

# Scenarios

This section outlines the main indicators implemented in the software.

Thresholds are configurable and can be adjusted by the user depending on the client classification:

- **Retail**
- **Institutional**
Les seuils sont **variables** et peuvent être fixés par l’utilisateur, en fonction de la catégorisation du client :

- **Retail**
- **Institutionnel**

## Scénarios d’Alerte – Clients Institutionnels et Clients Retail

### 1) Accumulation de volume → Détection de volumes anormalement élevés

- **Transactions journalières** dépassant un seuil prédéfini, exprimé en **% du volume quotidien marché**
- **Achats cumulés sur X jours** excédant un seuil défini, basé sur les volumes échangés sur la même période

**Implémentation côté code :**
- `DailyVolumeTracker` (journalier)
- `CumulatedVolumeTracker` (rolling / cumulé)

Seuils et fenêtres pilotés par `IndicatorsConfig`.

### 2) Plus-value importante → Détection de gains potentiellement suspects

- Transaction générant une **performance journalière** supérieure à la **volatilité observée** sur les **X jours suivants**, ajustée selon la nature de l’opération (**achat** ou **vente**)

**Implémentation côté code :**
- `ProfitTracker` (calcul rendement client vs rendement/volatilité asset, rolling window + alert)

---

# Script 1 : `Loaders.bas` (Données Marché)

## Rôle principal

`ImportOrRefreshAPIData(symbole)` gère le cycle de vie complet d’un ticker :

- premier import si le fichier n’existe pas
- import temporaire pour refresh si fichier existant
- fusion des nouvelles lignes uniquement
- déduplication + tri
- sauvegarde de la dernière date importée dans `HiddenSettings`

## Fonctions clés

### `APILoader(symbole, temp)`

- construit l’URL `TIME_SERIES_DAILY` (format CSV)
- appelle l’API via `MSXML2.XMLHTTP`
- écrit la réponse dans un nouveau workbook
- sauvegarde vers :
  - `data/{symbole}.xlsx`
  - `data/__{symbole}.xlsx` (temp)

### `CounterAPI(main_path)`

- met à jour le compteur journalier d’appels API dans `data/symbol_list_avapi/config.xlsx`
  - `B2` = date
  - `B3` = compteur

### `GetAllSymbolList(...)`

- lit `symbol_list.csv` (univers disponible)

### `GetAllTickers()`

- lit les tickers importés depuis `HiddenSettings`

---

# Script 2 : Gestion Clients & Transactions

## `ClientManager.bas`

### Responsabilités principales

- `CreateID(...)` : génère un ID client unique (code type + encodage nom/prénom)
- `CheckID(...)` : détecte les doublons dans `Transactions!N`
- `AddNewClient(...)` : ajoute les données client en `Transactions!N:Q`
- `GetClientID(...)`, `FilterLastNames(...)`, `FilterNames(...)` : support filtrage GUI

## `Add Trade.bas`

### `CheckTrade(...)`

- ouvre `data/{symbol}.xlsx`
- vérifie que la date existe dans les données marché
- vérifie que le prix est compris entre le low/high du jour
- vérifie que la quantité est cohérente avec le volume journalier
- si valide → appelle `AddTrade(...)`

### `AddTrade(...)`

Écrit en `Transactions!B:L` :

- ID client, identité, type client
- asset, date, side
- prix moyen, quantité
- valeur brute / nette

Applique un formatage visuel différent pour Buy / Sell.

---

# Script 3 : `AnalyzerAndTrackers.bas` (Moteur Analytique)

## Processus principal

### `MainProcess(client_id, asset, client_type, surname, name)`

1. extrait toutes les transactions du client pour l’asset sélectionné
2. ouvre `data/{asset}.xlsx`
3. calcule les indicateurs :
   - `DailyVolumeTracker`
   - `CumulatedVolumeTracker`
   - `ProfitTracker`
4. calcule le score global (`GlobalScore`)
5. écrit les résultats dans `DashBoard`
6. sauvegarde le workbook analysé dans `reporting/data_output/data_{id}_...xlsx`

## Indicateurs

### `DailyVolumeTracker`

- agrège la quantité traitée par date
- compare au volume marché journalier
- seuils (`IndicatorsConfig`) :
  - `C3` (Retail)
  - `E3` (Institutionnel)
- retourne `OK` / `ALERT`

### `CumulatedVolumeTracker`

- comparaison rolling volume cumulé client vs volume marché rolling
- seuils :
  - Retail → `B4:C4`
  - Institutionnel → `D4:E4`
- retourne `OK` / `ALERT`

### `ProfitTracker`

- agrégation trades par date (qty nette, prix moyen)
- calcule rendement journalier & cumulatif client
- calcule rendement asset + volatilité
- détecte fenêtres anormales via rolling :
  - Retail → `B5`
  - Institutionnel → `D5`

### `GlobalScore`

3 alertes binaires converties en score sur 100 : `0`, `33.3`, `66.7`, `100`

## Écriture Dashboard

### `ShowResult(...)`

Ajoute une ligne dans `DashBoard` avec :

- métadonnées (date, asset, client)
- exposition
- score + statuts indicateurs
- performance portefeuille
- nombre de Buy/Sell

---

# Script 4 : `WordReporting.bas` (Reporting Word + PDF)

## Rôle

### `WordMainProcess(id, export_path)`

- ouvre le template `utils/template/reporting_template.docx`
- charge la ligne d’analyse depuis `DashBoard`
- charge les seuils depuis `IndicatorsConfig`
- remplace les tags section par section
- exporte le dossier de reporting pour l’ID sélectionné

## Artefacts générés

### `SaveDocFile(...)`

Crée :

```text
reporting_{id}_doc_package/
├── reporting_{id}_document.pdf
├── raw_{id}reporting_doc.docx
└── copie data_{id}_*.xlsx
```

---

# Workflow des UserForms

## `UserLogin.frm` / `UserRegister.frm`

- authentification via feuille `User`
- injecte contexte utilisateur dans `DashBoard!T4:T7`
- gestion optionnelle visibilité ruban (admin)

## `dataGui.frm`

- ajout nouveau ticker vs mise à jour existant
- liste issue du CSV + tickers importés
- déclenche `ImportOrRefreshAPIData`

## `managerGui.frm`

- Onglet 1 : création client (validation + génération ID)
- Onglet 2 : ajout transaction (validation + contrôles date/prix/quantité)

## `AnalyzerGui.frm`

- Onglet 1 : analyse client/asset (`MainProcess`)
- Onglet 2 : export package (`WordMainProcess`)

---

# Modifications & Personnalisation

## Modifier les seuils d’indicateurs

Feuille `IndicatorsConfig` :

- Daily volume → `C3` (Retail), `E3` (Institutionnel)
- Cumulated volume → `B4:C4` (Retail), `D4:E4` (Institutionnel)
- Profit rolling window → `B5` (Retail), `D5` (Institutionnel)

## Ajouter de nouveaux assets

1. Mettre à jour `data/symbol_list_avapi/symbol_list.csv`
2. Lancer l’import via `dataGui`

## Personnaliser le reporting

- modifier `FillSection*` dans `WordReporting.bas`
- modifier les tags dans `reporting_template.docx`

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

Thresholds are **configurable** and can be adjusted by the user depending on the client classification:

- **Retail**
- **Institutional**

## Alert Scenarios – Institutional and Retail Clients

### 1) Volume Accumulation → Detection of Abnormally High Trading Volumes

- **Daily transactions** exceeding a predefined threshold, expressed as a percentage of total daily market volume
- **Cumulative purchases over X days** exceeding a defined threshold, based on total traded volume over the same period

**Code implementation:**
- `DailyVolumeTracker` (daily control)
- `CumulatedVolumeTracker` (rolling / cumulative control)

Thresholds and rolling windows are driven by the `IndicatorsConfig` sheet.

---

### 2) Significant Capital Gain → Detection of Potentially Suspicious Profits

- A transaction generating a **daily performance** exceeding the **observed volatility** over the following X days, adjusted depending on the transaction type (**buy** or **sell**)

**Code implementation:**
- `ProfitTracker` (client return vs asset return/volatility comparison, rolling window + alert logic)

---

# Script 1: `Loaders.bas` (Market Data)

## Main Role

`ImportOrRefreshAPIData(symbol)` manages the full lifecycle of a ticker:

- first import if the file does not exist
- temporary refresh import if the file exists
- merge of new rows only
- deduplication and sorting
- persistence of the last imported date in `HiddenSettings`

## Key Functions

### `APILoader(symbol, temp)`

- builds the `TIME_SERIES_DAILY` URL (CSV format)
- calls the API using `MSXML2.XMLHTTP`
- writes the response into a new workbook
- saves to:
  - `data/{symbol}.xlsx`
  - `data/__{symbol}.xlsx` (temporary file)

### `CounterAPI(main_path)`

- updates the daily API call counter in `data/symbol_list_avapi/config.xlsx`
  - `B2` = date
  - `B3` = counter

### `GetAllSymbolList(...)`

- reads `symbol_list.csv` (available universe)

### `GetAllTickers()`

- reads imported tickers from `HiddenSettings`

---

# Script 2: Client & Transaction Management

## `ClientManager.bas`

### Main Responsibilities

- `CreateID(...)`: generates a unique client ID (type code + encoded names)
- `CheckID(...)`: detects duplicates in `Transactions!N`
- `AddNewClient(...)`: appends client data in `Transactions!N:Q`
- `GetClientID(...)`, `FilterLastNames(...)`, `FilterNames(...)`: support dynamic GUI filtering

---

## `Add Trade.bas`

### `CheckTrade(...)`

- opens `data/{symbol}.xlsx`
- verifies that the trade date exists in market data
- verifies that the trade price lies within the day's low/high range
- verifies that the quantity is consistent with daily market volume
- if valid → calls `AddTrade(...)`

### `AddTrade(...)`

Writes to `Transactions!B:L`:

- client ID, identity, client type
- asset, date, side
- average price, quantity
- gross and net values

Applies distinct visual formatting for Buy and Sell transactions.

---

# Script 3: `AnalyzerAndTrackers.bas` (Analytics Engine)

## Main Process

### `MainProcess(client_id, asset, client_type, surname, name)`

1. extracts all client trades for the selected asset
2. opens `data/{asset}.xlsx`
3. computes indicators:
   - `DailyVolumeTracker`
   - `CumulatedVolumeTracker`
   - `ProfitTracker`
4. computes the global score (`GlobalScore`)
5. writes results to `DashBoard`
6. saves the analyzed workbook to `reporting/data_output/data_{id}_...xlsx`

---

## Indicators

### `DailyVolumeTracker`

- aggregates traded quantity by date
- compares it with daily market volume
- thresholds (`IndicatorsConfig`):
  - `C3` (Retail)
  - `E3` (Institutional)
- returns `OK` / `ALERT`

---

### `CumulatedVolumeTracker`

- rolling comparison of cumulative client volume vs rolling market volume
- thresholds:
  - Retail → `B4:C4`
  - Institutional → `D4:E4`
- returns `OK` / `ALERT`

---

### `ProfitTracker`

- aggregates trades by date (net quantity, average price)
- computes daily and cumulative client returns
- computes asset return and volatility
- flags abnormal performance windows using rolling parameters:
  - Retail → `B5`
  - Institutional → `D5`

---

### `GlobalScore`

Three binary alerts mapped to a score out of 100:

- `0`
- `33.3`
- `66.7`
- `100`

---

## Dashboard Writeback

### `ShowResult(...)`

Appends one analysis row in `DashBoard` with:

- metadata (date, asset, client)
- exposure
- score and indicator statuses
- portfolio performance
- number of Buy/Sell transactions

---

# Script 4: `WordReporting.bas` (Word + PDF Reporting)

## Role

### `WordMainProcess(id, export_path)`

- opens the template `utils/template/reporting_template.docx`
- loads the analysis row from `DashBoard`
- loads thresholds from `IndicatorsConfig`
- replaces template tags section by section
- exports the reporting folder for the selected ID

---

## Generated Artifacts

### `SaveDocFile(...)`

Creates:

```text
reporting_{id}_doc_package/
├── reporting_{id}_document.pdf
├── raw_{id}reporting_doc.docx
└── copy of data_{id}_*.xlsx
```

---

# UserForms Workflow

## `UserLogin.frm` / `UserRegister.frm`

- authentication via `User` sheet
- pushes active user context into `DashBoard!T4:T7`
- optional ribbon visibility management (admin check)

---

## `dataGui.frm`

- add new ticker vs update existing ticker
- ticker list populated from CSV/imported list
- triggers `ImportOrRefreshAPIData`

---

## `managerGui.frm`

- Tab 1: create client (validation + ID generation)
- Tab 2: add trade (field validation + date/price/quantity checks)

---

## `AnalyzerGui.frm`

- Tab 1: analyze selected client/asset (`MainProcess`)
- Tab 2: export reporting package (`WordMainProcess`)

---

# Modifications & Customization

## Modify Indicator Thresholds

Edit `IndicatorsConfig` sheet:

- Daily volume → `C3` (Retail), `E3` (Institutional)
- Cumulated volume → `B4:C4` (Retail), `D4:E4` (Institutional)
- Profit rolling window → `B5` (Retail), `D5` (Institutional)

---

## Add New Assets to the Universe

1. Update `data/symbol_list_avapi/symbol_list.csv`
2. Run the import via `dataGui`

---

## Customize the Reporting

- Modify `FillSection*` procedures in `WordReporting.bas`
- Adjust tags in `reporting_template.docx`

# Ads Analytics Pipeline

A data engineering take-home challenge implementing an end-to-end ads spend analytics pipeline: CSV ingestion into DuckDB, KPI modeling (CAC & ROAS), a parameterized CLI for analyst access, and a natural-language-to-SQL demo using Vanna AI.

---

## Project Structure

```
ads-analytics-pipeline/
├── ads_warehouse.duckdb          # Local DuckDB warehouse
├── crear_tabla.py                # Schema creation
├── cargar_Datos.py               # Data ingestion (CSV → DuckDB)
├── kpi_modeling.py               # CAC & ROAS computation + period comparison
├── metrics_access.py             # CLI tool: parameterized metric queries
├── IA_Query.ipynb                # NL→SQL demo using Vanna AI
└── metrics_last30_vs_prior30.json  # Sample output
```

---

## Architecture

```
ads_spend.csv
      │
      ▼
cargar_Datos.py
(load_date + source_file_name metadata added)
      │
      ▼
ads_warehouse.duckdb ──► kpi_modeling.py ──► CAC / ROAS
(DuckDB local file)        (last 30 vs        period comparison
                            prior 30 days)     + % deltas
                               │
                               ▼
                        metrics_access.py
                        (CLI / JSON output)
                               │
                               ▼
                        IA_Query.ipynb
                        (Vanna AI: NL → SQL)
```

---

## Part 1 — Ingestion

`crear_tabla.py` creates the warehouse table with provenance columns:

```sql
CREATE TABLE IF NOT EXISTS ads_spend (
  date DATE,
  platform TEXT,
  account TEXT,
  campaign TEXT,
  country TEXT,
  device TEXT,
  spend DOUBLE,
  clicks INTEGER,
  impressions INTEGER,
  conversions INTEGER,
  load_date TIMESTAMP,       -- when the row was loaded
  source_file_name TEXT      -- which file it came from
);
```

`cargar_Datos.py` reads the CSV, appends metadata, and inserts into DuckDB:

```bash
python crear_tabla.py
python cargar_Datos.py
```

Data persists in `ads_warehouse.duckdb` across runs. Re-running `cargar_Datos.py` appends a new batch with a fresh `load_date`, making it easy to audit reloads.

---

## Part 2 — KPI Modeling

**Definitions:**
- `CAC = spend / conversions`
- `ROAS = (conversions × 100) / spend` *(revenue assumed = conversions × 100)*

`kpi_modeling.py` computes both metrics for the last 30 days and the prior 30 days, then calculates % deltas:

```bash
python kpi_modeling.py
```

**Sample output:**

| Metric | Last 30 | Prior 30 | Delta % |
|--------|---------|----------|---------|
| Spend | 285,036 | 270,823 | +5.25% |
| Conversions | 9,562 | 8,392 | +13.94% |
| CAC | 29.81 | 32.27 | **-7.62%** ✅ |
| ROAS | 3.35 | 3.10 | **+8.06%** ✅ |

CAC decreased and ROAS improved period-over-period, indicating more efficient spend.

---

## Part 3 — Analyst Access

`metrics_access.py` is a CLI tool that exposes metrics as JSON, supporting two modes:

**Query a custom date range:**
```bash
python metrics_access.py --start 2025-05-01 --end 2025-05-31
```

**Automatic last 30 vs prior 30 comparison (relative to latest data):**
```bash
python metrics_access.py --compare-last30
```

**Optional: write output to file:**
```bash
python metrics_access.py --compare-last30 --output metrics_last30_vs_prior30.json
```

**Sample JSON output:**
```json
{
  "last": {
    "start": "2025-06-01",
    "end": "2025-06-30",
    "spend": 285036.15,
    "conversions": 9562,
    "revenue": 956200.0,
    "CAC": 29.81,
    "ROAS": 3.35
  },
  "prior": {
    "start": "2025-05-02",
    "end": "2025-05-31",
    "spend": 270822.66,
    "conversions": 8392,
    "revenue": 839200.0,
    "CAC": 32.27,
    "ROAS": 3.10
  },
  "deltas": {
    "spend_delta_pct": 5.25,
    "conversions_delta_pct": 13.94,
    "CAC_delta_pct": -7.62,
    "ROAS_delta_pct": 8.06
  }
}
```

---

## Part 4 — NL→SQL Agent Demo (Bonus)

`IA_Query.ipynb` demonstrates natural-language-to-SQL using [Vanna AI](https://vanna.ai/).

**How it works:**

1. Vanna is trained on the table schema (DDL) and business metric definitions:
   ```
   CAC = spend / conversions
   ROAS = (conversions * 100) / spend
   Revenue = conversions * 100
   ```

2. Example question-SQL pairs are added as few-shot training examples.

3. A natural language question is sent to Vanna, which generates SQL:

**Input:**
```
Compare CAC and ROAS for last 30 days vs prior 30 days.
```

**Generated SQL:**
```sql
WITH metrics AS (
  SELECT
    CASE
      WHEN date BETWEEN DATE '2025-06-01' AND DATE '2025-06-30' THEN 'last_30'
      WHEN date BETWEEN DATE '2025-05-02' AND DATE '2025-05-31' THEN 'prev_30'
    END AS period,
    SUM(spend) / NULLIF(SUM(conversions), 0)       AS CAC,
    (SUM(conversions) * 100) / NULLIF(SUM(spend), 0) AS ROAS
  FROM ads_spend
  WHERE date BETWEEN DATE '2025-05-02' AND DATE '2025-06-30'
  GROUP BY period
)
SELECT period, CAC, ROAS FROM metrics;
```

**Result:**

| period | CAC | ROAS |
|--------|-----|------|
| prev_30 | 32.27 | 3.10 |
| last_30 | 29.81 | 3.35 |

4. The SQL is executed directly against DuckDB and the result is returned as a DataFrame.

---

## Setup

### Requirements

```bash
pip install duckdb pandas vanna python-dotenv
```

### Environment Variables

Create a `.env` file:

```env
VANNA_API_KEY=your_vanna_api_key
VANNA_MODEL=model_ads_spend
```

### Run in order

```bash
# 1. Create schema
python crear_tabla.py

# 2. Load data
python cargar_Datos.py

# 3. Compute KPIs
python kpi_modeling.py

# 4. Query metrics via CLI
python metrics_access.py --compare-last30

# 5. Open the NL→SQL notebook
jupyter notebook IA_Query.ipynb
```

---

## Key Decisions

- **DuckDB** was chosen for its zero-setup local warehouse, native Parquet/CSV support, and fast analytical SQL — ideal for a self-contained demo.
- **Provenance columns** (`load_date`, `source_file_name`) are added at ingestion so every row can be traced back to its source file and load time.
- **Period comparison** uses the actual max date in the data rather than `CURRENT_DATE`, making results reproducible regardless of when the script runs.
- **Vanna AI** was used for the NL→SQL demo because it supports few-shot training on custom schemas and metric definitions without deploying any infrastructure.

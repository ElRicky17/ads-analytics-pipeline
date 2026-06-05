import duckdb
import pandas as pd

# 1️ Conectar a la base y verificar rango real de fechas
con = duckdb.connect('ads_warehouse.duckdb')

# Revisa las fechas mínimas y máximas en tu tabla
min_max = con.execute("SELECT MIN(date), MAX(date) FROM ads_spend").fetchall()
print(" Rango de fechas en ads_spend:", min_max)

# 2️ Traer datos de los últimos 60 días (puede estar vacío si las fechas son viejas)
query = """
SELECT 
    date,
    spend,
    conversions,
    conversions * 100.0 AS revenue
FROM ads_spend
WHERE date >= CURRENT_DATE - INTERVAL 60 DAY
"""
df = con.execute(query).fetchdf()
print(f" Filas traídas con filtro de 60 días: {len(df)}")
if df.empty:
    print("⚠ No hay datos en los últimos 60 días. Revisa el rango de fechas real.")
else:
    print(" Primeras filas de df:")
    print(df.head())

# 3️ Si está vacío, vuelve a traer TODO para inspección
if df.empty:
    df = con.execute("""
        SELECT date, spend, conversions, conversions * 100.0 AS revenue
        FROM ads_spend
    """).fetchdf()
    print(f" Filas totales en la tabla: {len(df)}")
    print(df.head())

df['date'] = pd.to_datetime(df['date'])

# 4️ Calcular intervalos
last_30_end = df['date'].max()
last_30_start = last_30_end - pd.Timedelta(days=29)
prior_30_end = last_30_start - pd.Timedelta(days=1)
prior_30_start = prior_30_end - pd.Timedelta(days=29)

print(f" Último 30 días: {last_30_start.date()} → {last_30_end.date()}")
print(f" Previos 30 días: {prior_30_start.date()} → {prior_30_end.date()}")

last_30 = df[(df['date'] >= last_30_start) & (df['date'] <= last_30_end)]
prior_30 = df[(df['date'] >= prior_30_start) & (df['date'] <= prior_30_end)]

print(f" Filas en last_30: {len(last_30)}, Filas en prior_30: {len(prior_30)}")

def compute_kpis(data):
    spend = data['spend'].sum()
    conv = data['conversions'].sum()
    revenue = data['revenue'].sum()
    cac = spend / conv if conv else None
    roas = revenue / spend if spend else None
    return spend, conv, cac, roas

spend_l, conv_l, cac_l, roas_l = compute_kpis(last_30)
spend_p, conv_p, cac_p, roas_p = compute_kpis(prior_30)

def pct_delta(new, old):
    if old and old != 0:
        return ((new - old) / old) * 100
    return None

results = {
    "spend_last_30": spend_l,
    "conv_last_30": conv_l,
    "CAC_last_30": cac_l,
    "ROAS_last_30": roas_l,
    "spend_prior_30": spend_p,
    "conv_prior_30": conv_p,
    "CAC_prior_30": cac_p,
    "ROAS_prior_30": roas_p,
    "spend_delta_pct": pct_delta(spend_l, spend_p),
    "conv_delta_pct": pct_delta(conv_l, conv_p),
    "CAC_delta_pct": pct_delta(cac_l, cac_p),
    "ROAS_delta_pct": pct_delta(roas_l, roas_p)
}

df_result = pd.DataFrame([results])
pd.set_option('display.float_format', '{:.2f}'.format)
print("\n👉 Resultado final:")
print(df_result)

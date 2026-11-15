import json
from pathlib import Path
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Stock Scanner EMA 5", page_icon="📈", layout="wide")
st.title("📈 STOCK SCANNER EMA 5")
st.caption("S&P 500 | Daily | CROSS confermati | Pendenza EMA5 minima ±0,10%")

signals_path = Path("signals.csv")
summary_path = Path("scan_summary.json")
errors_path = Path("scan_errors.csv")

if not signals_path.exists():
    st.error("Manca signals.csv. Controlla l'ultima esecuzione di GitHub Actions.")
    st.stop()

try:
    df = pd.read_csv(signals_path)
except pd.errors.EmptyDataError:
    st.error("signals.csv è vuoto e non contiene intestazioni.")
    st.stop()
except Exception as exc:
    st.error(f"Impossibile leggere signals.csv: {exc}")
    st.stop()

required = {"Ticker", "Segnale", "Data", "Chiusura", "EMA5", "Distanza %"}
if not required.issubset(df.columns):
    st.error("Colonne mancanti in signals.csv: " + ", ".join(sorted(required - set(df.columns))))
    st.stop()

for col in ["Chiusura", "EMA5", "Distanza %", "Pendenza EMA %"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

summary = None
if summary_path.exists():
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        st.warning(f"Impossibile leggere scan_summary.json: {exc}")

errors = None
if errors_path.exists():
    try:
        errors = pd.read_csv(errors_path)
    except pd.errors.EmptyDataError:
        errors = pd.DataFrame()
    except Exception as exc:
        st.warning(f"Impossibile leggere scan_errors.csv: {exc}")

up = int((df["Segnale"] == "CROSS UP").sum())
down = int((df["Segnale"] == "CROSS DOWN").sum())

# Non inventiamo il numero di titoli analizzati: dipende dallo schema del riepilogo.
def get_summary_value(obj, candidates):
    if not isinstance(obj, dict):
        return None
    for key in candidates:
        if key in obj and obj[key] is not None:
            return obj[key]
    return None

analyzed = get_summary_value(summary, [
    "analizzati", "analyzed_symbols", "symbols_analyzed", "scanned",
    "scanned_symbols", "titoli_analizzati", "success_count", "successful"
])
scan_time = get_summary_value(summary, [
    "aggiornato_utc", "scan_time", "scanned_at",
    "timestamp", "updated_at", "scan_datetime",
    "generated_at", "last_update", "ultima_scansione"
])
errors_count = get_summary_value(summary, [
    "errors", "error_count", "failed", "failed_symbols", "download_errors"
])
if isinstance(errors_count, (list, dict)):
    errors_count = len(errors_count)
if errors_count is None and errors is not None:
    errors_count = len(errors)

st.subheader("Riepilogo della scansione")
a, b, c, d = st.columns(4)
a.metric("Titoli analizzati", analyzed if analyzed is not None else "N/D")
b.metric("CROSS UP", up)
c.metric("CROSS DOWN", down)
d.metric("Errori / dati mancanti", errors_count if errors_count is not None else "N/D")

latest_session = str(df["Data"].max()) if not df.empty else "Nessun segnale"
st.write("**Ultima seduta nei risultati:**", latest_session)
if scan_time:
    try:
        dt = datetime.fromisoformat(
            str(scan_time).replace("Z", "+00:00")
        )
        dt_italia = dt.astimezone(
            ZoneInfo("Europe/Rome")
        )
        data_formattata = dt_italia.strftime(
            "%d/%m/%Y ore %H:%M"
        )
    except (ValueError, TypeError):
        data_formattata = str(scan_time)
else:
    data_formattata = "Non disponibile"

st.write("**Data e ora della scansione:**", data_formattata)

if summary is None:
    st.info("Riepilogo non disponibile: controlla scan_summary.json nel repository.")
elif isinstance(summary, dict):
    with st.expander("Dettagli completi della scansione (scan_summary.json)"):
        st.json(summary)
else:
    st.warning("Il riepilogo JSON non è un oggetto: verifica lo schema di scan_summary.json.")

# TABELLA SEGNALI EMA5 CON LINK TRADINGVIEW
# ==========================================

from urllib.parse import quote

st.divider()

st.subheader("Segnali EMA 5 Daily")

st.metric("Totale segnali", len(df))

filtro = st.radio(
    "Filtra i segnali",
    ["Tutti", "CROSS UP", "CROSS DOWN"],
    horizontal=True,
)

ordinamento = st.selectbox(
    "Ordina i risultati",
    [
        "Distanza maggiore (positiva)",
        "Distanza minore (negativa)",
        "Distanza assoluta maggiore",
        "Pendenza EMA maggiore",
        "Pendenza EMA minore",
        "Ticker A-Z",
    ],
)

tabella = df.copy()

if filtro != "Tutti":
    tabella = tabella[
        tabella["Segnale"] == filtro
    ]

if ordinamento == "Distanza maggiore (positiva)":
    tabella = tabella.sort_values(
        "Distanza %", ascending=False
    )

elif ordinamento == "Distanza minore (negativa)":
    tabella = tabella.sort_values(
        "Distanza %", ascending=True
    )

elif ordinamento == "Distanza assoluta maggiore":
    tabella = tabella.assign(
        distanza_assoluta=tabella["Distanza %"].abs()
    ).sort_values(
        "distanza_assoluta", ascending=False
    ).drop(columns=["distanza_assoluta"])

elif ordinamento == "Pendenza EMA maggiore":
    tabella = tabella.sort_values(
        "Pendenza EMA %", ascending=False
    )

elif ordinamento == "Pendenza EMA minore":
    tabella = tabella.sort_values(
        "Pendenza EMA %", ascending=True
    )

elif ordinamento == "Ticker A-Z":
    tabella = tabella.sort_values("Ticker")

tabella = tabella.copy()

tabella["Grafico TradingView"] = tabella["Ticker"].apply(
    lambda ticker: (
        "https://www.tradingview.com/chart/?symbol="
        + quote("NASDAQ:" + str(ticker), safe=":")
    )
)

st.dataframe(
    tabella,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Grafico TradingView": st.column_config.LinkColumn(
            "Grafico TradingView",
            display_text="📊 Apri",
        ),
        "Distanza %": st.column_config.NumberColumn(
            "Distanza %",
            format="%.2f%%",
        ),
        "Pendenza EMA %": st.column_config.NumberColumn(
            "Pendenza EMA %",
            format="%.3f%%",
        ),
    },
)

st.download_button(
    "📥 Scarica risultati CSV",
    data=tabella.to_csv(index=False).encode("utf-8"),
    file_name="segnali_ema5.csv",
    mime="text/csv",
)


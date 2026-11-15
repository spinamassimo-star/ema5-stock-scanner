import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import quote

st.set_page_config(
    page_title="Stock Scanner EMA 5",
    page_icon="📈",
    layout="wide"
)

st.title("📈 STOCK SCANNER EMA 5")
st.caption("S&P 500 | Timeframe Daily | Solo nuovi CROSS confermati")

file = Path("signals.csv")

if not file.exists():
    st.warning(
        "Nessuna scansione disponibile. "
        "Dobbiamo ancora eseguire scanner.py."
    )
    st.stop()

df = pd.read_csv(file)

if df.empty:
    st.info("Nessun nuovo CROSS EMA 5 rilevato.")
    st.stop()

st.metric("Segnali rilevati", len(df))

filtro = st.radio(
    "Filtra i segnali",
    ["Tutti", "CROSS UP", "CROSS DOWN"],
    horizontal=True
)

if filtro != "Tutti":
    df = df[df["Segnale"] == filtro]

df = df.copy()

def link_grafico(ticker):
    symbol = quote(str(ticker), safe="")
    return (
        "https://www.tradingview.com/chart/"
        f"?symbol={symbol}"
    )

df["Grafico"] = df["Ticker"].apply(link_grafico)

st.dataframe(
    df,
    column_config={
        "Grafico": st.column_config.LinkColumn(
            "Apri grafico",
            display_text="📊 TradingView"
        ),
        "Distanza %": st.column_config.NumberColumn(
            "Distanza %",
            format="%.2f%%"
        )
    },
    hide_index=True,
    use_container_width=True
)

st.download_button(
    "📥 Scarica risultati CSV",
    data=df.to_csv(index=False),
    file_name="ema5_signals.csv",
    mime="text/csv"
)

st.caption(
    "Segnali tecnici informativi, non raccomandazioni "
    "di investimento. Disponibilità su Scalable Capital "
    "da verificare."
)

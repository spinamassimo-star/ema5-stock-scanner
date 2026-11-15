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
st.caption(
    "S&P 500 | Daily | Nuovi CROSS confermati"
)

file = Path("signals.csv")

if not file.exists():
    st.warning("Scansione non ancora disponibile.")
    st.stop()

df = pd.read_csv(file)

if df.empty:
    st.info("Nessun CROSS rilevato nell'ultima scansione.")
    st.stop()

st.metric("Segnali rilevati", len(df))

st.write("**Ultima seduta nei risultati:**", df["Data"].max())

filtro = st.radio(
    "Filtra i segnali",
    ["Tutti", "CROSS UP", "CROSS DOWN"],
    horizontal=True
)

ordinamento = st.selectbox(
    "Ordina i risultati",
    [
        "Distanza maggiore (positiva)",
        "Distanza minore (negativa)",
        "Distanza assoluta maggiore",
        "Ticker alfabetico"
    ]
)

if filtro != "Tutti":
    df = df[df["Segnale"] == filtro].copy()

if ordinamento == "Distanza maggiore (positiva)":
    df = df.sort_values(
        "Distanza %", ascending=False
    )

elif ordinamento == "Distanza minore (negativa)":
    df = df.sort_values(
        "Distanza %", ascending=True
    )

elif ordinamento == "Distanza assoluta maggiore":
    df = df.assign(
        abs_dist=df["Distanza %"].abs()
    ).sort_values(
        "abs_dist", ascending=False
    ).drop(columns=["abs_dist"])

else:
    df = df.sort_values("Ticker")

def link_grafico(ticker):
    symbol = quote(str(ticker), safe="")
    return (
        "https://www.tradingview.com/chart/"
        f"?symbol={symbol}"
    )

df["Apri grafico"] = df["Ticker"].apply(
    link_grafico
)

st.dataframe(
    df,
    column_config={
        "Apri grafico": st.column_config.LinkColumn(
            "Grafico TradingView",
            display_text="📊 Apri"
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
    "Segnali tecnici a scopo informativo. "
    "Verificare sempre data, prezzi e disponibilita' "
    "del titolo su Scalable Capital."
)



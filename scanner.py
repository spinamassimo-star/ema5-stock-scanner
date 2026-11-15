
import pandas as pd
import yfinance as yf
from datetime import datetime, time
from zoneinfo import ZoneInfo

URL = (
    "https://raw.githubusercontent.com/datasets/"
    "s-and-p-500-companies/main/data/constituents.csv"
)

COLUMNS = [
    "Ticker", "Segnale", "Data",
    "Chiusura", "EMA5", "Distanza %"
]


def get_symbols():
    df = pd.read_csv(URL)
    return sorted(
        df["Symbol"]
        .dropna()
        .astype(str)
        .str.replace(".", "-", regex=False)
        .unique()
        .tolist()
    )


def scan_symbol(symbol):
    try:
        data = yf.download(
            symbol,
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False
        )

        if data.empty:
            return None

        close = data["Close"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = close.dropna().sort_index()

        # Usa soltanto candele giornaliere completate.
        now_ny = datetime.now(ZoneInfo("America/New_York"))
        today_ny = now_ny.date()

        dates = pd.to_datetime(close.index).date

        # Margine di 30 minuti dopo la chiusura ordinaria.
        if now_ny.time() < time(16, 30):
            close = close[
                [d < today_ny for d in dates]
            ]

        if len(close) < 100:
            return None

        ema = close.ewm(
            span=5,
            adjust=False
        ).mean()

        c_prev = float(close.iloc[-2])
        c_last = float(close.iloc[-1])

        e_prev = float(ema.iloc[-2])
        e_last = float(ema.iloc[-1])

        signal = None

        if c_prev <= e_prev and c_last > e_last:
            signal = "CROSS UP"

        elif c_prev >= e_prev and c_last < e_last:
            signal = "CROSS DOWN"

        if signal is None:
            return None

        last_date = pd.Timestamp(close.index[-1]).date()

        return {
            "Ticker": symbol,
            "Segnale": signal,
            "Data": str(last_date),
            "Chiusura": round(c_last, 2),
            "EMA5": round(e_last, 2),
            "Distanza %": round(
                (c_last / e_last - 1) * 100, 2
            )
        }

    except Exception as exc:
        print(f"ERRORE {symbol}: {exc}")
        return None


def main():
    symbols = get_symbols()
    results = []

    print(f"Titoli da analizzare: {len(symbols)}")

    for i, symbol in enumerate(symbols, 1):
        print(f"{i}/{len(symbols)} - {symbol}")

        result = scan_symbol(symbol)

        if result is not None:
            results.append(result)

    df = pd.DataFrame(results, columns=COLUMNS)

    # Mostra solo i segnali relativi alla seduta
    # piu' recente presente nei risultati.
    if not df.empty:
        latest_date = df["Data"].max()
        df = df[df["Data"] == latest_date].copy()

        df = df.sort_values(
            by="Distanza %",
            ascending=False
        )

    df.to_csv("signals.csv", index=False)

    print(f"Segnali trovati: {len(df)}")
    print("File signals.csv aggiornato.")


if __name__ == "__main__":
    main()


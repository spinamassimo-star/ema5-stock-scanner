import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

# Elenco dei componenti S&P 500

URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"

def get_symbols():
    df = pd.read_csv(URL)
    symbols = df["Symbol"].dropna().tolist()
    return [s.replace(".", "-") for s in symbols]


def scan_symbol(symbol):
    try:
        data = yf.download(
            symbol,
            period="3mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False
        )

        if data.empty or len(data) < 10:
            return None

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = close.dropna()

        # Escludiamo l'eventuale candela giornaliera
        # ancora in formazione.
        now_ny = datetime.now(ZoneInfo("America/New_York"))
        last_date = pd.Timestamp(close.index[-1]).date()

        if last_date == now_ny.date() and now_ny.hour < 16:
            close = close.iloc[:-1]

        if len(close) < 10:
            return None

        ema = close.ewm(span=5, adjust=False).mean()

        prev_close = float(close.iloc[-2])
        last_close = float(close.iloc[-1])
        prev_ema = float(ema.iloc[-2])
        last_ema = float(ema.iloc[-1])

        signal = None

        if prev_close <= prev_ema and last_close > last_ema:
            signal = "CROSS UP"

        elif prev_close >= prev_ema and last_close < last_ema:
            signal = "CROSS DOWN"

        if signal is None:
            return None

        return {
            "Ticker": symbol,
            "Segnale": signal,
            "Data": str(close.index[-1].date()),
            "Chiusura": round(last_close, 2),
            "EMA5": round(last_ema, 2),
            "Distanza %": round(
                (last_close / last_ema - 1) * 100, 2
            )
        }

    except Exception as e:
        print(f"Errore {symbol}: {e}")
        return None

def main():
    symbols = get_symbols()
    results = []

    for i, symbol in enumerate(symbols, 1):
        print(f"{i}/{len(symbols)} - {symbol}")
        result = scan_symbol(symbol)

        if result:
            results.append(result)

    columns = [
        "Ticker", "Segnale", "Data",
        "Chiusura", "EMA5", "Distanza %"
    ]

    df = pd.DataFrame(results, columns=columns)
    df.to_csv("signals.csv", index=False)

    print(f"Scansione completata: {len(df)} segnali.")

if __name__ == "__main__":
    main()

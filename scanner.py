import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"

MIN_EMA_SLOPE_PCT = 0.10

COLUMNS = [
    "Ticker",
    "Segnale",
    "Data",
    "Chiusura",
    "EMA5",
    "Distanza %",
    "Pendenza EMA %",
]

HISTORY_FILE = Path("signals_history.csv")


def get_symbols():
    table = pd.read_csv(URL)

    if "Symbol" not in table.columns:
        raise RuntimeError("Elenco S&P 500 senza colonna Symbol")

    symbols = (
        table["Symbol"]
        .dropna()
        .astype(str)
        .str.replace(".", "-", regex=False)
    )

    return sorted(set(symbols))


def scan_symbol(symbol, cutoff_date):
    data = yf.download(
        symbol,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data.empty:
        raise ValueError("Download vuoto")

    close = data["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    close = close.dropna().sort_index()

    close = close[
        pd.to_datetime(close.index).date <= cutoff_date
    ]

    if len(close) < 100:
        raise ValueError("Storico insufficiente")

    last_date = pd.Timestamp(close.index[-1]).date()

    if last_date != cutoff_date:
        raise ValueError(
            f"Ultima barra {last_date}, attesa {cutoff_date}"
        )

    ema = close.ewm(span=5, adjust=False).mean()

    c_prev = float(close.iloc[-2])
    c_last = float(close.iloc[-1])

    e_prev = float(ema.iloc[-2])
    e_last = float(ema.iloc[-1])

    slope = (e_last / e_prev - 1) * 100

    signal = None

    if (
        c_prev <= e_prev
        and c_last > e_last
        and slope >= MIN_EMA_SLOPE_PCT
    ):
        signal = "CROSS UP"

    elif (
        c_prev >= e_prev
        and c_last < e_last
        and slope <= -MIN_EMA_SLOPE_PCT
    ):
        signal = "CROSS DOWN"

    if signal is None:
        return None

    return {
        "Ticker": symbol,
        "Segnale": signal,
        "Data": str(last_date),
        "Chiusura": round(c_last, 2),
        "EMA5": round(e_last, 2),
        "Distanza %": round(
            (c_last / e_last - 1) * 100, 2
        ),
        "Pendenza EMA %": round(slope, 3),
    }


def update_history(current_signals):
    """
    Conserva tutti i segnali delle scansioni precedenti.

    Ogni combinazione di:
    Data + Ticker + Segnale
    viene registrata una sola volta.
    """

    if HISTORY_FILE.exists():
        history = pd.read_csv(
            HISTORY_FILE,
            dtype={"Ticker": str, "Data": str},
        )

        for column in COLUMNS:
            if column not in history.columns:
                history[column] = pd.NA

        history = history[COLUMNS]

    else:
        history = pd.DataFrame(columns=COLUMNS)

    previous_keys = set(
        zip(
            history["Data"].astype(str),
            history["Ticker"].astype(str),
            history["Segnale"].astype(str),
        )
    )

    new_rows = []

    for _, row in current_signals.iterrows():
        key = (
            str(row["Data"]),
            str(row["Ticker"]),
            str(row["Segnale"]),
        )

        if key not in previous_keys:
            new_rows.append(row.to_dict())
            previous_keys.add(key)

    if new_rows:
        additions = pd.DataFrame(new_rows, columns=COLUMNS)

        history = pd.concat(
            [history, additions],
            ignore_index=True,
        )

    history = history.drop_duplicates(
        subset=["Data", "Ticker", "Segnale"],
        keep="first",
    )

    history = history.sort_values(
        ["Data", "Ticker", "Segnale"],
        ascending=[False, True, True],
    )

    history.to_csv(HISTORY_FILE, index=False)

    return len(new_rows), len(history)


def main():
    symbols = get_symbols()

    now_ny = datetime.now(
        ZoneInfo("America/New_York")
    )

    # SPY viene utilizzato per individuare
    # l'ultima seduta di mercato disponibile.

    spy = yf.download(
        "SPY",
        period="1mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if spy.empty:
        raise RuntimeError(
            "Impossibile determinare ultima seduta da SPY"
        )

    dates = sorted(
        set(pd.to_datetime(spy.index).date)
    )

    eligible = [
        d for d in dates
        if d < now_ny.date()
        or (
            d == now_ny.date()
            and now_ny.time() >= time(16, 30)
        )
    ]

    if not eligible:
        raise RuntimeError(
            "Nessuna seduta completata individuata"
        )

    cutoff_date = eligible[-1]

    results = []
    failures = []
    processed = 0

    print(
        f"Seduta richiesta: {cutoff_date}; "
        f"titoli: {len(symbols)}",
        flush=True,
    )

    for i, symbol in enumerate(symbols, 1):
        try:
            row = scan_symbol(
                symbol,
                cutoff_date,
            )

            processed += 1

            if row:
                results.append(row)

        except Exception as exc:
            failures.append({
                "Ticker": symbol,
                "Errore": str(exc),
            })

        if i % 50 == 0:
            print(
                f"Completati {i}/{len(symbols)}",
                flush=True,
            )

    # Protezione contro interruzioni importanti
    # del fornitore dei dati.

    if processed < len(symbols) * 0.90:
        raise RuntimeError(
            f"Scansione incompleta: "
            f"{processed}/{len(symbols)}; "
            "risultati precedenti conservati"
        )

    df = pd.DataFrame(
        results,
        columns=COLUMNS,
    )

    df = df.sort_values(
        "Distanza %",
        ascending=False,
    )

    # Risultati dell'ultima seduta.
    df.to_csv(
        "signals.csv",
        index=False,
    )

    # Errori di download.
    pd.DataFrame(
        failures,
        columns=["Ticker", "Errore"],
    ).to_csv(
        "scan_errors.csv",
        index=False,
    )

    # Nuovo archivio storico.
    nuovi_segnali, totale_storico = update_history(df)

    summary = {
        "seduta": str(cutoff_date),
        "universo": len(symbols),
        "analizzati": processed,
        "errori": len(failures),
        "cross_up": int(
            (df["Segnale"] == "CROSS UP").sum()
        ),
        "cross_down": int(
            (df["Segnale"] == "CROSS DOWN").sum()
        ),
        "nuovi_segnali_storico": nuovi_segnali,
        "totale_segnali_storico": totale_storico,
        "aggiornato_utc": datetime.now(
            ZoneInfo("UTC")
        ).isoformat(),
    }

    Path("scan_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(summary, flush=True)


if __name__ == "__main__":
    main()


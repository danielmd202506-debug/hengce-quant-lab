from __future__ import annotations

import asyncio

import httpx
import pandas as pd


def _secid(code: str) -> str:
    return f"{1 if code.startswith(('5', '6', '9')) else 0}.{code}"


async def fetch_kline(code: str, *, period: int = 101, limit: int = 750) -> tuple[str, pd.DataFrame]:
    if len(code) != 6 or not code.isdigit():
        raise ValueError("证券代码必须为 6 位数字")
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "invt": "2",
        "fltt": "1",
        "secid": _secid(code),
        "klt": str(period),
        "fqt": "1",
        "lmt": str(limit),
        "end": "20500101",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json,text/plain,*/*",
    }
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for attempt in range(3):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                break
            except (httpx.HTTPError, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5 * (attempt + 1))
        else:  # pragma: no cover - loop either breaks or raises.
            raise RuntimeError("行情接口连续重试失败") from last_error
    payload = response.json().get("data")
    if not payload or not payload.get("klines"):
        raise ValueError("未获取到行情数据")
    rows = [line.split(",") for line in payload["klines"]]
    frame = pd.DataFrame(
        rows,
        columns=["date", "open", "close", "high", "low", "volume", "amount", "amplitude", "pct", "change", "turnover"],
    )
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date")
    return payload.get("name", code), frame[["open", "high", "low", "close", "volume"]]


async def fetch_daily(code: str, limit: int = 750) -> tuple[str, pd.DataFrame]:
    return await fetch_kline(code, period=101, limit=limit)


async def fetch_intraday(code: str, minutes: int, limit: int = 500) -> tuple[str, pd.DataFrame]:
    if minutes not in (30, 60):
        raise ValueError("分钟周期仅支持 30 或 60")
    return await fetch_kline(code, period=minutes, limit=limit)


async def fetch_weekly(code: str, limit: int = 260) -> tuple[str, pd.DataFrame]:
    return await fetch_kline(code, period=102, limit=limit)

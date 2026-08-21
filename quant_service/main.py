from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd

from engine import run_backtest
from market_data import fetch_daily


app = FastAPI(title="Hengce Quant Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "framework": "Backtrader"}


class BacktestRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    closes: list[float] = Field(min_length=22, max_length=2000)
    fast: int = Field(5, ge=2, le=60)
    slow: int = Field(20, ge=5, le=250)
    commission: float = Field(ge=0, le=0.02)


@app.post("/backtest")
def backtest(request: BacktestRequest) -> dict:
    if request.fast >= request.slow:
        raise HTTPException(400, "短期均线必须小于长期均线")
    close = pd.Series(request.closes, dtype="float64").to_numpy()
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1_000_000,
        },
        index=pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(close), freq="B"),
    )
    result = run_backtest(
        frame,
        fast=request.fast,
        slow=request.slow,
        commission=request.commission,
    )
    return {
        "code": request.code,
        "commission": request.commission,
        "bars": len(frame),
        "latest_date": frame.index[-1].date().isoformat(),
        **result.as_dict(),
    }


@app.get("/analyze/{code}")
async def analyze(
    code: str,
    fast: int = Query(5, ge=2, le=60),
    slow: int = Query(20, ge=5, le=250),
    commission: float = Query(0.0003, ge=0, le=0.02),
) -> dict:
    if fast >= slow:
        raise HTTPException(400, "短期均线必须小于长期均线")
    try:
        name, frame = await fetch_daily(code)
        result = run_backtest(frame, fast=fast, slow=slow, commission=commission)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "行情或量化计算暂时不可用") from exc
    return {
        "code": code,
        "name": name,
        "commission": commission,
        "bars": len(frame),
        "latest_date": frame.index[-1].date().isoformat(),
        **result.as_dict(),
    }

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from engine import run_backtest
from market_data import fetch_daily, fetch_intraday


HOLDINGS = (
    {"code": "000965", "type": "个股", "commission": 0.000086},
    {"code": "159755", "type": "ETF", "commission": 0.00005},
    {"code": "159870", "type": "ETF", "commission": 0.00005},
)
OUTPUT = Path(__file__).resolve().parents[1] / "public" / "quant-signals.json"


async def generate() -> None:
    signals: dict[str, object] = {}
    errors: dict[str, str] = {}

    for holding in HOLDINGS:
        code = holding["code"]
        try:
            name, frame = await fetch_daily(code, limit=750)
            result = run_backtest(
                frame,
                fast=5,
                slow=20,
                commission=float(holding["commission"]),
            ).as_dict()
            timeframes: dict[str, object] = {}
            for minutes in (30, 60):
                try:
                    _, intraday = await fetch_intraday(code, minutes, limit=500)
                    intraday_result = run_backtest(
                        intraday,
                        fast=5,
                        slow=20,
                        commission=float(holding["commission"]),
                    ).as_dict()
                    timeframes[f"{minutes}m"] = {
                        "signal": intraday_result["signal"],
                        "fast_ma": intraday_result["fast_ma"],
                        "slow_ma": intraday_result["slow_ma"],
                        "bars": len(intraday),
                        "latest_date": intraday.index[-1].strftime("%Y-%m-%d %H:%M"),
                    }
                except Exception as exc:
                    errors[f"{code}:{minutes}m"] = str(exc)
                await asyncio.sleep(0.5)
            signals[code] = {
                **result,
                "code": code,
                "name": name,
                "type": holding["type"],
                "bars": len(frame),
                "latest_date": frame.index[-1].strftime("%Y-%m-%d"),
                "commission": holding["commission"],
                "timeframes": timeframes,
            }
        except Exception as exc:  # Keep other holdings available if one feed fails.
            errors[code] = str(exc)

    if not signals:
        raise RuntimeError(f"全部行情计算失败: {errors}")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frequency_minutes": 5,
        "strategy": "Backtrader MA5/MA20",
        "signals": signals,
        "errors": errors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(signals)} signals to {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(generate())

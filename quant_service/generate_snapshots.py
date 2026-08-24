from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from engine import run_backtest
from market_data import fetch_daily, fetch_weekly


HOLDINGS = (
    {"code": "000965", "type": "个股", "commission": 0.000086},
    {"code": "159755", "type": "ETF", "commission": 0.00005},
    {"code": "159870", "type": "ETF", "commission": 0.00005},
)
OUTPUT = Path(__file__).resolve().parents[1] / "public" / "quant-signals.json"


async def generate() -> None:
    previous: dict[str, object] = {}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = {}
    signals: dict[str, object] = dict(previous.get("signals", {}))
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
            previous_signal = signals.get(code, {})
            previous_frames = previous_signal.get("timeframes", {}) if isinstance(previous_signal, dict) else {}
            timeframes: dict[str, object] = {}
            if isinstance(previous_frames, dict) and "weekly" in previous_frames:
                timeframes["weekly"] = previous_frames["weekly"]
            try:
                _, weekly = await fetch_weekly(code, limit=260)
                weekly_result = run_backtest(
                    weekly,
                    fast=5,
                    slow=20,
                    commission=float(holding["commission"]),
                ).as_dict()
                timeframes["weekly"] = {
                    "signal": weekly_result["signal"],
                    "fast_ma": weekly_result["fast_ma"],
                    "slow_ma": weekly_result["slow_ma"],
                    "bars": len(weekly),
                    "latest_date": weekly.index[-1].strftime("%Y-%m-%d"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as exc:
                errors[f"{code}:weekly"] = str(exc)
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
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # Preserve the last valid snapshot for this holding.
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
    print(f"Wrote {len(signals)} signals to {OUTPUT}; {len(errors)} fetch errors preserved")


if __name__ == "__main__":
    asyncio.run(generate())

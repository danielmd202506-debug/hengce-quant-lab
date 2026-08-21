from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import backtrader as bt
import pandas as pd


class MovingAverageStrategy(bt.Strategy):
    params = dict(fast=5, slow=20)

    def __init__(self) -> None:
        self.fast_ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.fast)
        self.slow_ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.slow)
        self.cross = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self) -> None:
        if not self.position and self.cross > 0:
            self.order_target_percent(target=0.95)
        elif self.position and self.cross < 0:
            self.close()


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe: float | None
    trades: int
    won: int
    lost: int
    signal: str
    fast_ma: float
    slow_ma: float
    framework: str = "Backtrader"

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _value(tree: dict[str, Any], *path: str, default: Any = 0) -> Any:
    current: Any = tree
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def run_backtest(
    frame: pd.DataFrame,
    *,
    fast: int = 5,
    slow: int = 20,
    cash: float = 100_000,
    commission: float = 0.0003,
) -> BacktestResult:
    if len(frame) < slow + 2:
        raise ValueError(f"至少需要 {slow + 2} 个交易日的数据")

    data = frame.copy().sort_index()
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close"])

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    cerebro.addstrategy(MovingAverageStrategy, fast=fast, slow=slow)
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name="sharpe", riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    strategy = cerebro.run()[0]
    returns = strategy.analyzers.returns.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    sharpe = strategy.analyzers.sharpe.get_analysis().get("sharperatio")
    trades = strategy.analyzers.trades.get_analysis()

    fast_ma = float(data.close.tail(fast).mean())
    slow_ma = float(data.close.tail(slow).mean())
    latest = float(data.close.iloc[-1])
    if fast_ma > slow_ma and latest > fast_ma:
        signal = "持有/观察买入"
    elif fast_ma < slow_ma and latest < fast_ma:
        signal = "减仓/退出"
    else:
        signal = "等待"

    return BacktestResult(
        total_return=round(float(returns.get("rtot", 0)) * 100, 2),
        annual_return=round(float(returns.get("rnorm100", 0)), 2),
        max_drawdown=round(float(_value(drawdown, "max", "drawdown")), 2),
        sharpe=round(float(sharpe), 2) if sharpe is not None else None,
        trades=int(_value(trades, "total", "closed")),
        won=int(_value(trades, "won", "total")),
        lost=int(_value(trades, "lost", "total")),
        signal=signal,
        fast_ma=round(fast_ma, 4),
        slow_ma=round(slow_ma, 4),
    )

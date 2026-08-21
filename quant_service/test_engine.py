import unittest

import pandas as pd

from engine import run_backtest


class EngineTest(unittest.TestCase):
    def test_backtest_returns_framework_metrics(self) -> None:
        dates = pd.date_range("2024-01-01", periods=160, freq="B")
        close = [10 + i * 0.02 + (0.4 if (i // 20) % 2 else 0) for i in range(160)]
        frame = pd.DataFrame(
            {
                "open": close,
                "high": [x * 1.01 for x in close],
                "low": [x * 0.99 for x in close],
                "close": close,
                "volume": [100_000] * 160,
            },
            index=dates,
        )
        result = run_backtest(frame)
        self.assertEqual(result.framework, "Backtrader")
        self.assertIsInstance(result.max_drawdown, float)
        self.assertIn(result.signal, {"持有/观察买入", "减仓/退出", "等待"})


if __name__ == "__main__":
    unittest.main()

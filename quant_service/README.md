# Hengce Quant Service

Python/Backtrader service for auditable daily-strategy backtests.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`
- 股票：`GET /analyze/000965?fast=5&slow=20&commission=0.000086`
- ETF：`GET /analyze/159755?fast=5&slow=20&commission=0.00005`
- 前端优先使用 `POST /backtest`，把已获取的真实收盘价传给 Backtrader，避免重复请求行情源。
# GitHub Actions 快照

`.github/workflows/quant-snapshots.yml` 会在工作日每 5 分钟运行一次
`generate_snapshots.py`，并更新 `public/quant-signals.json`。前端优先读取该快照，
读取不到时才回退到本机 FastAPI。

如果前端与快照不在同一域名，在构建前设置：

```bash
NEXT_PUBLIC_QUANT_SNAPSHOT_URL=https://raw.githubusercontent.com/OWNER/REPO/BRANCH/public/quant-signals.json
```

私有仓库的 Raw 地址不能被匿名浏览器直接读取；这种情况下需要公开 Pages/对象存储，
或者让承载前端的平台同步部署生成后的文件。

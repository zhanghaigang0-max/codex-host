#!/usr/bin/env python3
"""Daily market snapshot and rule-based risk dashboard. No trading execution."""
from __future__ import annotations

import csv
import json
import math
import statistics
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
ASSETS = [
    {"symbol": "NVDA", "kind": "stock", "source": "Stooq", "url": "https://stooq.com/q/d/l/?s=nvda.us&i=d"},
    {"symbol": "QQQ", "kind": "stock", "source": "Stooq", "url": "https://stooq.com/q/d/l/?s=qqq.us&i=d"},
    {"symbol": "BTCUSDT", "kind": "crypto", "source": "Binance public market data", "url": "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=100"},
    {"symbol": "ETHUSDT", "kind": "crypto", "source": "Binance public market data", "url": "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1d&limit=100"},
]

def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 market-dashboard/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8")

def get_closes(asset: dict) -> tuple[list[float], str]:
    raw = fetch_text(asset["url"])
    if asset["kind"] == "stock":
        rows = list(csv.DictReader(raw.splitlines()))
        closes = [float(row["Close"]) for row in rows if row.get("Close") not in (None, "", "N/D")]
        last_date = rows[-1]["Date"] if rows else "unknown"
    else:
        rows = json.loads(raw)
        closes = [float(row[4]) for row in rows]
        last_date = datetime.fromtimestamp(rows[-1][0] / 1000, tz=timezone.utc).date().isoformat() if rows else "unknown"
    if len(closes) < 20:
        raise ValueError(f"{asset['symbol']}: not enough daily data ({len(closes)} rows)")
    return closes, last_date

def sma(values: list[float], period: int) -> float | None:
    return sum(values[-period:]) / period if len(values) >= period else None

def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    recent = changes[-period:]
    gains = sum(max(x, 0) for x in recent) / period
    losses = sum(max(-x, 0) for x in recent) / period
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100 - (100 / (1 + gains / losses))

def analyze(asset: dict) -> dict:
    closes, as_of = get_closes(asset)
    price = closes[-1]
    ma20, ma50 = sma(closes, 20), sma(closes, 50)
    strength = rsi(closes)
    returns = [(closes[i] / closes[i - 1]) - 1 for i in range(max(1, len(closes) - 20), len(closes))]
    annualization_days = 252 if asset['kind'] == 'stock' else 365
    volatility = statistics.pstdev(returns) * math.sqrt(annualization_days) if len(returns) > 1 else None
    if ma50 is not None and price > ma20 > ma50 and strength is not None and strength < 70:
        signal, trend = "偏多", "价格位于20日均线上方，且20日均线高于50日均线"
    elif ma50 is not None and price < ma20 < ma50 and strength is not None and strength > 30:
        signal, trend = "偏空", "价格位于20日均线下方，且20日均线低于50日均线"
    else:
        signal, trend = "观望", "均线结构或RSI条件尚未形成一致方向"
    return {
        "symbol": asset["symbol"], "kind": asset["kind"], "source": asset["source"],
        "as_of": as_of, "close": round(price, 6), "sma20": round(ma20, 6) if ma20 else None,
        "sma50": round(ma50, 6) if ma50 else None, "rsi14": round(strength, 2) if strength is not None else None,
        "annualized_volatility_20d": round(volatility, 4) if volatility is not None else None,
        "signal": signal, "trend_note": trend, "observations": len(closes),
    }

def fmt(value, suffix=""):
    return "暂无" if value is None else f"{value}{suffix}"

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    beijing_now = now.astimezone(timezone(timedelta(hours=8)))
    results, errors = [], []
    for asset in ASSETS:
        try:
            results.append(analyze(asset))
        except Exception as exc:
            errors.append({"symbol": asset["symbol"], "error": str(exc)})
    payload = {"generated_at_utc": now.isoformat(), "disclaimer": "仅供研究，不构成投资建议；无自动交易功能。", "assets": results, "errors": errors}
    (DATA_DIR / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# AI 金融决策中心｜每日市场观察",
        "",
        f"- 生成时间：{now.strftime('%Y-%m-%d %H:%M UTC')}（北京时间 {beijing_now.strftime('%Y-%m-%d %H:%M')}）",
        "- 当前版本：行情采集 + 规则指标分析（尚未接入生成式 AI，不把规则信号称为 AI 判断）",
        "- 覆盖资产：NVDA、QQQ、BTC、ETH",
        "",
        "> 风险提示：本报告仅供学习研究，不构成投资建议。信号由简单规则生成，不能单独作为买卖依据。本系统不会连接交易账户或执行下单。",
        "",
        "## 市场概览",
        "",
        "| 标的 | 数据日期 | 最新价 | SMA20 | SMA50 | RSI14 | 年化波动率* | 规则信号 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        lines.append(f"| {item['symbol']} | {item['as_of']} | {item['close']} | {fmt(item['sma20'])} | {fmt(item['sma50'])} | {fmt(item['rsi14'])} | {fmt(item['annualized_volatility_20d'], '%')} | **{item['signal']}** |")
    if errors:
        lines += ["", "## 数据获取异常", ""]
        lines += [f"- {e['symbol']}：{e['error']}" for e in errors]
    lines += ["", "## 观察说明", ""]
    for item in results:
        lines.append(f"- **{item['symbol']}**：{item['trend_note']}。收盘/最新日线值 {item['close']}；数据日期 {item['as_of']}。")
    lines += ["", "* 年化波动率根据最近约20个日收益率估算；股票按252个交易日、加密货币按365天年化，跨资产比较仍需谨慎。", "", "## 下一步升级", "", "1. 加入新闻与宏观事件来源，并标注出处和时间。", "2. 接入多个 AI 分别分析，汇总分歧与置信度。", "3. 用历史数据回测规则，记录准确率、最大回撤和误报。", "4. 经用户明确授权后再考虑模拟盘；真实交易默认关闭。", ""]
    (REPORT_DIR / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    history = DATA_DIR / "history.jsonl"
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"Report generated: {len(results)} assets, {len(errors)} errors")

if __name__ == "__main__":
    main()

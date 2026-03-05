#!/usr/bin/env python3
"""
fetch_etf_data.py — 获取 ETF 实时价格和 MA20 均线

数据源（均无需 API Key，国内服务器可用）:
  实时价: 腾讯财经 qt.gtimg.cn（主）→ 东方财富 push2（备）
  MA20:   腾讯财经 K线接口（主）→ akshare（备，需安装）

用法:
    python3 fetch_etf_data.py
    python3 fetch_etf_data.py --codes sh510310 sz159338
    python3 fetch_etf_data.py --json

输出示例:
    510310 (沪深300ETF): 当前价=3.985, MA20=3.921, 偏离度=+1.63%
    159338 (中证A500ETF): 当前价=1.152, MA20=1.178, 偏离度=-2.21%
"""

import argparse
import json
import urllib.request
from datetime import datetime


ETF_CONFIGS = {
    "sh510310": {"name": "沪深300ETF", "display_code": "510310"},
    "sz159338": {"name": "中证A500ETF", "display_code": "159338"},
}


def fetch_realtime_price_tencent(codes: list[str]) -> dict:
    """腾讯财经实时行情（主接口，国内服务器稳定可用）
    响应格式: v_sh510310="1~名称~代码~现价~昨收~今开~..."
    字段索引: [0]=类型 [1]=名称 [2]=代码 [3]=现价 [4]=昨收 [5]=今开
    """
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("gbk", errors="replace")
    except Exception as e:
        raise RuntimeError(f"腾讯财经接口请求失败: {e}")

    result = {}
    for line in raw.strip().splitlines():
        if "=" not in line or '~' not in line:
            continue
        key_part, val_part = line.split("=", 1)
        # key: v_sh510310 → sh510310
        raw_key = key_part.strip()
        code = raw_key[2:] if raw_key.startswith("v_") else raw_key
        fields = val_part.strip().strip('"').strip(";").split("~")
        if len(fields) < 4:
            continue
        try:
            price = float(fields[3])  # 现价
            if price == 0 and len(fields) > 4:
                price = float(fields[4])  # 昨收价 fallback
            if price > 0:
                result[code] = price
        except (ValueError, IndexError):
            continue
    return result


def fetch_realtime_price_eastmoney(codes: list[str]) -> dict:
    """东方财富实时行情（备用接口）
    secids 格式: 1.510310（沪市）, 0.159338（深市）
    """
    secids = []
    for c in codes:
        prefix = "1" if c.startswith("sh") else "0"
        num = c[2:]
        secids.append(f"{prefix}.{num}")
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        "?fltt=2&invt=2&fields=f2,f12,f14&secids=" + ",".join(secids)
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.eastmoney.com"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = {}
        for item in data.get("data", {}).get("diff", []):
            code_num = item.get("f12", "")
            price = item.get("f2")
            if code_num and price and float(price) > 0:
                # 匹配回 sh/sz 前缀
                for c in codes:
                    if c[2:] == str(code_num):
                        result[c] = float(price)
        return result
    except Exception as e:
        raise RuntimeError(f"东方财富接口请求失败: {e}")


def fetch_realtime_price(codes: list[str]) -> dict:
    """获取实时价格：腾讯（主）→ 东方财富（备）"""
    try:
        prices = fetch_realtime_price_tencent(codes)
        if prices:
            return prices
    except Exception:
        pass
    return fetch_realtime_price_eastmoney(codes)


def fetch_ma20_tencent(display_code: str, market_prefix: str) -> float | None:
    """通过腾讯财经接口获取近 30 日收盘价，计算 MA20（无需第三方库，国内稳定可用）"""
    # 腾讯接口：sh510310 用 qfqday，sz159338 用 day
    url = (
        f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?_var=kline_dayqfq&param={market_prefix}{display_code},day,,,30,qfq&r=0.1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
        json_str = raw.split("=", 1)[1].strip().rstrip(";")
        data = json.loads(json_str)
        stock_data = data.get("data", {}).get(f"{market_prefix}{display_code}", {})
        # sh 系列走 qfqday，sz 系列走 day（实测）
        klines = stock_data.get("qfqday") or stock_data.get("day") or []
        if not klines or len(klines) < 5:
            return None
        # 每条格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
        closes = []
        for kl in klines:
            try:
                closes.append(float(kl[2]))
            except (IndexError, ValueError):
                pass
        if len(closes) < 5:
            return None
        last20 = closes[-20:] if len(closes) >= 20 else closes
        return sum(last20) / len(last20)
    except Exception:
        return None


def fetch_ma20_akshare(display_code: str, market_prefix: str) -> float | None:
    """通过 akshare 获取近 20 日收盘价，计算 MA20（备用，需 pip install akshare）"""
    try:
        import akshare as ak
        df = ak.fund_etf_hist_em(symbol=display_code, period="daily",
                                  start_date="", end_date="", adjust="")
        if df is None or len(df) < 20:
            return None
        closes = df["收盘"].tail(20).astype(float).tolist()
        return sum(closes) / len(closes)
    except Exception:
        return None


def get_etf_data(codes: list[str]) -> list[dict]:
    """主函数：获取实时价格 + MA20，计算偏离度"""
    # Step 1: 实时价格
    prices = fetch_realtime_price(codes)

    results = []
    for code in codes:
        cfg = ETF_CONFIGS.get(code, {})
        display_code = cfg.get("display_code", code.replace("sh", "").replace("sz", ""))
        name = cfg.get("name", display_code)
        market_prefix = code[:2]

        current_price = prices.get(code)
        if current_price is None:
            results.append({"code": display_code, "name": name,
                            "error": "无法获取实时价格"})
            continue

        # Step 2: MA20（优先腾讯财经接口，备用 akshare）
        ma20 = fetch_ma20_tencent(display_code, market_prefix)
        if ma20 is None:
            ma20 = fetch_ma20_akshare(display_code, market_prefix)

        deviation = None
        if ma20 and ma20 > 0:
            deviation = (current_price - ma20) / ma20

        results.append({
            "code": display_code,
            "name": name,
            "current_price": round(current_price, 4),
            "ma20": round(ma20, 4) if ma20 else None,
            "deviation": round(deviation, 6) if deviation is not None else None,
            "deviation_pct": f"{deviation * 100:+.2f}%" if deviation is not None else "N/A",
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="获取 A股 ETF 实时价格和 MA20")
    parser.add_argument("--codes", nargs="+",
                        default=["sh510310", "sz159338"],
                        help="ETF 代码列表（带市场前缀，如 sh510310）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    data = get_etf_data(args.codes)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 55)
        for item in data:
            if "error" in item:
                print(f"{item['code']} ({item['name']}): ⚠️ {item['error']}")
            else:
                ma20_str = f"{item['ma20']}" if item['ma20'] else "N/A"
                print(f"{item['code']} ({item['name']})")
                print(f"  当前价: {item['current_price']}")
                print(f"  MA20:   {ma20_str}")
                print(f"  偏离度: {item['deviation_pct']}")
                print()


if __name__ == "__main__":
    main()

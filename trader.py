import requests
import json
import os
import datetime

# --- 初始配置 ---
INITIAL_CASH = 10000.0
DATA_FILE = "data/portfolio.json"
LOG_FILE = "data/trade_log.csv"

def load_portfolio():
    """加载资产数据，如果不存在则初始化"""
    # 修复关键点：先创建文件夹，确保路径存在
    if not os.path.exists("data"):
        os.makedirs("data")
        
    if not os.path.exists(DATA_FILE):
        return {
            "cash": INITIAL_CASH,
            "btc": 0.0,
            "last_price": 0.0,
            "total_value": INITIAL_CASH
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def get_btc_price():
    """获取比特币当前价格 (USD)"""
    try:
        url = "https://api.coindesk.com/v1/bpi/currentprice.json"
        resp = requests.get(url, timeout=10).json()
        return float(resp["bpi"]["USD"]["rate_float"])
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def execute_trade(portfolio, current_price):
    """执行交易策略"""
    last_price = portfolio["last_price"]
    trade_action = "HOLD"
    log_msg = ""

    # 1. 初始化
    if last_price == 0:
        portfolio["last_price"] = current_price
        trade_action = "INIT"
        log_msg = "初始化价格监测"

    # 2. 跌 > 2% -> 买入 $100
    elif current_price < last_price * 0.98:
        if portfolio["cash"] >= 100:
            buy_btc = 100 / current_price
            portfolio["btc"] += buy_btc
            portfolio["cash"] -= 100
            trade_action = "BUY"
            log_msg = f"下跌抄底: 买入 $100 ({buy_btc:.6f} BTC)"
        else:
            log_msg = "现金不足"

    # 3. 涨 > 2% -> 卖出 $100
    elif current_price > last_price * 1.02:
        btc_to_sell = 100 / current_price
        if portfolio["btc"] >= btc_to_sell:
            portfolio["btc"] -= btc_to_sell
            portfolio["cash"] += 100
            trade_action = "SELL"
            log_msg = "上涨止盈: 卖出 $100"
        else:
            log_msg = "持仓不足"
    
    else:
        log_msg = "波动过小 (Hold)"

    # 更新资产
    portfolio["total_value"] = portfolio["cash"] + (portfolio["btc"] * current_price)
    portfolio["last_price"] = current_price # 更新今日价格
    
    # 记录日志
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    # 检查文件是否存在以决定是否写表头
    file_exists = os.path.exists(LOG_FILE)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("Date,Action,Price,Total Value,Details\n")
        f.write(f"{timestamp},{trade_action},{current_price:.2f},{portfolio['total_value']:.2f},{log_msg}\n")

    # 保存 JSON
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)
        
    return trade_action, log_msg

def update_readme(portfolio):
    """更新 README 看板"""
    recent_logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 跳过表头，取最后 5 条
            for line in lines[1:][-5:]:
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    action = parts[1]
                    icon = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
                    recent_logs += f"- {icon} **{parts[0]}**: {parts[4]} (Price: ${parts[2]})\n"

    profit_pct = ((portfolio["total_value"] - INITIAL_CASH) / INITIAL_CASH) * 100
    color = "🟢" if profit_pct >= 0 else "🔴"

    content = f"""
# 💰 AI Auto-Trader (Paper Trading)

这是一个模拟交易机器人，每天自动根据 BTC 价格波动进行买卖。

## 📊 资产概览 (Initial: ${INITIAL_CASH})
| 💵 现金余额 | 🪙 BTC 持仓 | 📈 总资产净值 | 🚀 收益率 |
| :---: | :---: | :---: | :---: |
| ${portfolio['cash']:.2f} | {portfolio['btc']:.6f} BTC | **${portfolio['total_value']:.2f}** | {color} {profit_pct:.2f}% |

---

### 📝 最近交易记录
{recent_logs}

---
*Last Update: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    # 1. 无论如何先加载(并创建)数据文件夹
    port = load_portfolio()
    
    # 2. 获取价格
    price = get_btc_price()
    
    if price:
        print(f"BTC Price: {price}")
        action, msg = execute_trade(port, price)
        update_readme(port)
        print(f"Done. Action: {action}")
    else:
        print("Failed to fetch price.")

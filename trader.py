import requests
import json
import os
import datetime

# --- 初始配置 ---
INITIAL_CASH = 10000.0
# 数据存储文件
DATA_FILE = "data/portfolio.json"
LOG_FILE = "data/trade_log.csv"

def load_portfolio():
    """加载资产数据，如果不存在则初始化"""
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
        resp = requests.get(url).json()
        return float(resp["bpi"]["USD"]["rate_float"])
    except:
        return None

def execute_trade(portfolio, current_price):
    """执行简单的交易策略"""
    last_price = portfolio["last_price"]
    trade_action = "HOLD"
    trade_amount = 0.0
    log_msg = ""

    # 策略逻辑：
    # 1. 第一次运行：只记录价格，不动
    if last_price == 0:
        portfolio["last_price"] = current_price
        return "INIT", "初始化价格"

    # 2. 如果跌了 > 2% -> 抄底买入 $100
    if current_price < last_price * 0.98:
        if portfolio["cash"] >= 100:
            buy_btc = 100 / current_price
            portfolio["btc"] += buy_btc
            portfolio["cash"] -= 100
            trade_action = "BUY"
            log_msg = f"价格下跌，买入 100 USD (获得 {buy_btc:.6f} BTC)"

    # 3. 如果涨了 > 2% -> 止盈卖出 $100
    elif current_price > last_price * 1.02:
        btc_to_sell = 100 / current_price
        if portfolio["btc"] >= btc_to_sell:
            portfolio["btc"] -= btc_to_sell
            portfolio["cash"] += 100
            trade_action = "SELL"
            log_msg = f"价格上涨，卖出 100 USD"
    
    else:
        log_msg = "波动太小，保持持有 (Hold)"

    # 更新总资产
    portfolio["total_value"] = portfolio["cash"] + (portfolio["btc"] * current_price)
    portfolio["last_price"] = current_price # 更新今日价格供明天参考
    
    # 记录日志
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a") as f:
        # 如果是新文件，先写表头
        if os.stat(LOG_FILE).st_size == 0:
            f.write("Date,Action,Price,Total Value,Details\n")
        f.write(f"{timestamp},{trade_action},{current_price:.2f},{portfolio['total_value']:.2f},{log_msg}\n")

    # 保存状态
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)
        
    return trade_action, log_msg

def update_readme(portfolio):
    """更新看板"""
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
        # 取最近 5 条记录
        recent_logs = "".join([f"- {line}" for line in lines[-5:]])

    # 计算收益率
    profit_pct = ((portfolio["total_value"] - INITIAL_CASH) / INITIAL_CASH) * 100
    color = "🟢" if profit_pct >= 0 else "🔴"

    content = f"""
# 💰 AI Auto-Trader (Paper Trading)

这是一个模拟交易机器人，每天自动根据 BTC 价格波动进行买卖。

## 📊 资产概览
| 💵 现金余额 | 🪙 BTC 持仓 | 📈 总资产净值 | 🚀 收益率 |
| :---: | :---: | :---: | :---: |
| ${portfolio['cash']:.2f} | {portfolio['btc']:.6f} BTC | **${portfolio['total_value']:.2f}** | {color} {profit_pct:.2f}% |

---

### 📝 最近交易记录
{recent_logs}

---
*本策略仅供娱乐和 GitHub 活跃度演示，不构成投资建议。*
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    price = get_btc_price()
    if price:
        port = load_portfolio()
        action, msg = execute_trade(port, price)
        update_readme(port)
        print(f"Done. Action: {action}, Msg: {msg}")
    else:
        print("Failed to fetch price.")

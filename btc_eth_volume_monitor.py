#!/usr/bin/env python3
"""
BTC & ETH 永续合约成交量监控
监控 OKX 上 BTC-USDT-SWAP 和 ETH-USDT-SWAP 的 5 分钟成交量
当超过设定阈值时发送 Telegram 通知
"""
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 北京时间工具函数
def get_beijing_now_str():
    """获取当前北京时间字符串"""
    utc_now = datetime.now(timezone.utc)
    beijing_now = utc_now + timedelta(hours=8)
    return beijing_now.strftime('%Y-%m-%d %H:%M:%S')

# 数据目录
DATA_DIR = Path('/home/user/webapp/data/volume_monitor')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 配置文件
CONFIG_FILE = DATA_DIR / 'volume_thresholds.json'
STATE_FILE = DATA_DIR / 'volume_state.json'

# 默认阈值配置
DEFAULT_CONFIG = {
    'BTC-USDT-SWAP': {
        'enabled': True,
        'threshold': 1000000000,  # 10亿 USDT
        'name': 'BTC永续'
    },
    'ETH-USDT-SWAP': {
        'enabled': True,
        'threshold': 500000000,   # 5亿 USDT
        'name': 'ETH永续'
    }
}

# Telegram 配置
TG_BOT_TOKEN = '7738360227:AAHOdNEzsSy5W9kQkDu7y6xFaFITw6nCfyI'
TG_CHAT_ID = '1837795395'


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_state():
    """加载状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_state(state):
    """保存状态"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_5min_candle(symbol):
    """
    获取 OKX 5分钟 K线数据
    返回最新一根K线的成交量（单位：USDT）
    """
    url = 'https://www.okx.com/api/v5/market/candles'
    params = {
        'instId': symbol,
        'bar': '5m',
        'limit': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] == '0' and data['data']:
            # OKX K线数据格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            # volCcyQuote 是以报价货币(USDT)计价的成交量
            candle = data['data'][0]
            timestamp = int(candle[0])
            volume_usdt = float(candle[7])  # volCcyQuote
            volume_base = float(candle[5])  # vol (基础货币数量)
            
            return {
                'timestamp': timestamp,
                'volume_usdt': volume_usdt,
                'volume_base': volume_base,
                'success': True
            }
        else:
            print(f"❌ 获取 {symbol} K线失败: {data.get('msg', 'Unknown error')}")
            return {'success': False, 'error': data.get('msg', 'Unknown error')}
            
    except Exception as e:
        print(f"❌ 请求 {symbol} K线异常: {e}")
        return {'success': False, 'error': str(e)}


def send_telegram_alert(symbol, volume_usdt, threshold, name):
    """发送 Telegram 警报"""
    volume_billion = volume_usdt / 1_000_000_000
    threshold_billion = threshold / 1_000_000_000
    
    message = f"""
🔔 <b>成交量警报</b>

📊 <b>{name}</b> ({symbol})
⏰ 时间: {get_beijing_now_str()}

📈 <b>5分钟成交量</b>: {volume_billion:.2f}亿 USDT
⚠️ <b>阈值</b>: {threshold_billion:.2f}亿 USDT

🔥 成交量超过阈值 <b>{((volume_usdt / threshold - 1) * 100):.1f}%</b>
"""
    
    url = f'https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage'
    params = {
        'chat_id': TG_CHAT_ID,
        'text': message.strip(),
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=params, timeout=10)
        response.raise_for_status()
        print(f"✅ Telegram 通知已发送: {name}")
        return True
    except Exception as e:
        print(f"❌ Telegram 通知发送失败: {e}")
        return False


def monitor_loop():
    """监控主循环"""
    print(f"[{get_beijing_now_str()}] 🚀 BTC & ETH 成交量监控启动...")
    print(f"📁 配置文件: {CONFIG_FILE}")
    print(f"📁 状态文件: {STATE_FILE}")
    
    # 加载配置
    config = load_config()
    print(f"\n📊 监控配置:")
    for symbol, cfg in config.items():
        if cfg['enabled']:
            threshold_billion = cfg['threshold'] / 1_000_000_000
            print(f"  • {cfg['name']} ({symbol}): {threshold_billion:.2f}亿 USDT")
    
    print(f"\n⏰ 每 5 分钟检查一次，开始监控...\n")
    
    # 上次警报时间（避免重复发送）
    last_alert_time = {}
    
    while True:
        try:
            # 重新加载配置（支持动态修改）
            config = load_config()
            current_time = time.time()
            
            for symbol, cfg in config.items():
                if not cfg['enabled']:
                    continue
                
                # 获取最新 5 分钟K线
                result = get_5min_candle(symbol)
                
                if not result['success']:
                    continue
                
                volume_usdt = result['volume_usdt']
                threshold = cfg['threshold']
                name = cfg['name']
                
                # 显示当前数据
                volume_billion = volume_usdt / 1_000_000_000
                threshold_billion = threshold / 1_000_000_000
                print(f"[{get_beijing_now_str()}] {name}: {volume_billion:.2f}亿 USDT (阈值: {threshold_billion:.2f}亿)")
                
                # 检查是否超过阈值
                if volume_usdt > threshold:
                    # 检查是否在冷却期内（15分钟内不重复发送）
                    last_alert = last_alert_time.get(symbol, 0)
                    if current_time - last_alert > 900:  # 15分钟 = 900秒
                        print(f"🔔 {name} 成交量超过阈值！发送通知...")
                        if send_telegram_alert(symbol, volume_usdt, threshold, name):
                            last_alert_time[symbol] = current_time
                    else:
                        remaining = int(900 - (current_time - last_alert))
                        print(f"⏳ {name} 在冷却期内，{remaining}秒后可再次发送")
                
                # 保存状态
                state = load_state()
                state[symbol] = {
                    'last_check': get_beijing_now_str(),
                    'volume_usdt': volume_usdt,
                    'volume_billion': volume_billion,
                    'threshold_billion': threshold_billion
                }
                save_state(state)
            
            print()  # 空行
            
            # 等待 5 分钟
            time.sleep(300)
            
        except KeyboardInterrupt:
            print(f"\n[{get_beijing_now_str()}] ⚠️ 收到中断信号，正在退出...")
            break
        except Exception as e:
            print(f"[{get_beijing_now_str()}] ❌ 监控异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == '__main__':
    monitor_loop()

#!/usr/bin/env python3
"""
BTC & ETH 5分钟成交量监控
监控 OKX BTC-USDT-SWAP 和 ETH-USDT-SWAP 的 5 分钟成交量
当成交量超过设定阈值时发送 Telegram 通知
"""
import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta

# 北京时间工具函数
def get_beijing_now():
    """获取当前北京时间"""
    return datetime.now() + timedelta(hours=8)

def get_beijing_now_str():
    """获取当前北京时间字符串"""
    return get_beijing_now().strftime('%Y-%m-%d %H:%M:%S')

# Telegram 配置（使用与其他监控相同的配置）
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003227444260')

# 数据目录
DATA_DIR = Path('/home/user/webapp/data/volume_monitor')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 配置文件（与 API 保持一致）
CONFIG_FILE = DATA_DIR / 'volume_thresholds.json'
STATE_FILE = DATA_DIR / 'volume_state.json'

# 默认配置 (M USDT)
DEFAULT_CONFIG = {
    'BTC-USDT-SWAP': {
        'enabled': True,
        'threshold': 100_000_000,  # 100M USDT
        'name': 'BTC永续合约'
    },
    'ETH-USDT-SWAP': {
        'enabled': True,
        'threshold': 50_000_000,  # 50M USDT
        'name': 'ETH永续合约'
    }
}


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
    获取指定币种的最新**已完成**5分钟K线数据
    返回: (timestamp, volume, close_price) 或 None
    """
    try:
        url = f"https://www.okx.com/api/v5/market/candles"
        params = {
            'instId': symbol,
            'bar': '5m',
            'limit': '2'  # 获取最近2根K线
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['code'] == '0' and data['data']:
            # data['data'][0] 是最新的K线（可能未完成）
            # data['data'][1] 是上一根K线（已完成）
            
            # 检查第一根K线是否已完成
            if len(data['data']) >= 1:
                latest_candle = data['data'][0]
                is_confirmed = latest_candle[8] == '1'
                
                # 如果最新K线已确认（完成），使用它
                if is_confirmed:
                    candle = latest_candle
                # 否则使用上一根已完成的K线
                elif len(data['data']) >= 2:
                    candle = data['data'][1]
                else:
                    # 没有已完成的K线数据
                    return None
                
                # OKX K线数据格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                # ts: 时间戳, vol: 成交量(张), volCcy: 成交量(币), volCcyQuote: 成交量(计价货币USDT)
                timestamp = int(candle[0])
                volume_usdt = float(candle[7])  # 使用 USDT 计价的成交量
                close_price = float(candle[4])
                
                return timestamp, volume_usdt, close_price
        
        return None
        
    except Exception as e:
        print(f"[{get_beijing_now_str()}] 获取 {symbol} K线数据失败: {e}")
        return None


def send_telegram_alert(symbol, config_name, volume, threshold, price, timestamp):
    """发送 Telegram 告警"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{get_beijing_now_str()}] Telegram 配置未设置，跳过发送")
        return False
    
    try:
        # 转换时间戳为北京时间
        dt = datetime.fromtimestamp(timestamp / 1000)
        beijing_time = dt + timedelta(hours=8)
        time_str = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 格式化成交量（单位：M）
        volume_m = volume / 1_000_000
        threshold_m = threshold / 1_000_000
        
        message = f"""🚨 <b>成交量告警</b>

📊 <b>{config_name}</b>
⏰ 时间: {time_str}
💰 价格: ${price:,.2f}
📈 5分钟成交量: <b>{volume_m:.2f}M</b>
⚠️ 阈值: {threshold_m:.2f}M

超过阈值 <b>{((volume/threshold - 1) * 100):.1f}%</b>"""
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"[{get_beijing_now_str()}] Telegram 告警发送成功: {config_name}")
            return True
        else:
            print(f"[{get_beijing_now_str()}] Telegram 告警发送失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"[{get_beijing_now_str()}] 发送 Telegram 告警异常: {e}")
        return False


def check_volume_alert(symbol, config, state):
    """检查成交量并发送告警"""
    if not config.get('enabled', False):
        return
    
    result = get_5min_candle(symbol)
    if not result:
        return
    
    timestamp, volume, price = result
    threshold = config['threshold']
    config_name = config['name']
    
    # 检查是否超过阈值
    if volume > threshold:
        # 检查是否已经为这个时间点发送过告警
        state_key = f"{symbol}_{timestamp}"
        if state_key not in state:
            print(f"[{get_beijing_now_str()}] {config_name} 成交量超过阈值: ${volume:,.0f} > ${threshold:,.0f}")
            
            # 发送告警
            if send_telegram_alert(symbol, config_name, volume, threshold, price, timestamp):
                # 记录已发送
                state[state_key] = {
                    'timestamp': timestamp,
                    'volume': volume,
                    'price': price,
                    'alert_time': get_beijing_now_str()
                }
                save_state(state)
    
    # 记录最新数据到 JSONL
    record_volume_data(symbol, timestamp, volume, price, threshold)


def record_volume_data(symbol, timestamp, volume, price, threshold):
    """记录成交量数据到 JSONL（避免重复记录同一时间戳）"""
    try:
        beijing_date = get_beijing_now().strftime('%Y%m%d')
        jsonl_file = DATA_DIR / f'volume_{symbol.replace("-", "_")}_{beijing_date}.jsonl'
        
        # 检查是否已经记录过这个时间戳
        recorded_timestamps = set()
        if jsonl_file.exists():
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        recorded_timestamps.add(data.get('timestamp'))
                    except:
                        pass
        
        # 如果这个时间戳已经记录过，跳过
        if timestamp in recorded_timestamps:
            print(f"[{get_beijing_now_str()}] {symbol} K线 {timestamp} 已记录，跳过")
            return
        
        record = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp / 1000 + 8*3600).strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'volume': volume,
            'price': price,
            'threshold': threshold,
            'exceeded': volume > threshold,
            'recorded_at': get_beijing_now_str()
        }
        
        with open(jsonl_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"[{get_beijing_now_str()}] ✅ 记录 {symbol} K线数据: {record['datetime']} 成交量: {volume/1_000_000:.2f}M")
            
    except Exception as e:
        print(f"[{get_beijing_now_str()}] 记录成交量数据失败: {e}")


def monitor_loop():
    """主监控循环"""
    print(f"[{get_beijing_now_str()}] BTC & ETH 成交量监控启动...")
    print(f"[{get_beijing_now_str()}] 数据目录: {DATA_DIR}")
    print(f"[{get_beijing_now_str()}] Telegram Bot: {'已配置' if TELEGRAM_BOT_TOKEN else '未配置'}")
    
    while True:
        try:
            config = load_config()
            state = load_state()
            
            # 检查 BTC
            if 'BTC-USDT-SWAP' in config:
                check_volume_alert('BTC-USDT-SWAP', config['BTC-USDT-SWAP'], state)
            
            # 检查 ETH
            if 'ETH-USDT-SWAP' in config:
                check_volume_alert('ETH-USDT-SWAP', config['ETH-USDT-SWAP'], state)
            
            # 每5分钟检查一次（与K线周期对齐）
            time.sleep(300)
            
        except KeyboardInterrupt:
            print(f"\n[{get_beijing_now_str()}] 监控已停止")
            break
        except Exception as e:
            print(f"[{get_beijing_now_str()}] 监控异常: {e}")
            time.sleep(60)


if __name__ == '__main__':
    monitor_loop()

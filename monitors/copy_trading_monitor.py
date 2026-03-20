#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跟单监控系统
监控目标账户的盈亏情况，当达到触发条件时自动为跟单账户开仓
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
import traceback

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / 'data' / 'copy_trading'
TELEGRAM_CONFIG = PROJECT_ROOT / 'config' / 'configs' / 'telegram_config.json'

# API配置
API_BASE = 'http://localhost:9002'
ABC_STATE_API = f'{API_BASE}/abc-position/api/current-state'
OKX_TRADING_API = f'{API_BASE}/api/okx-trading/place-order'

# 账户映射
ACCOUNT_MAPPING = {
    'A': 'main',
    'B': 'poit_main',
    'C': 'fangfang12',
    'D': 'dadanini'
}

ACCOUNT_NAMES = {
    'A': '主账户',
    'B': 'POIT',
    'C': 'fangfang12',
    'D': 'dadanini'
}

# OKX账户配置
OKX_ACCOUNTS = {
    'main': {
        'api_key': 'b0c18f2d-e014-4ae8-9c3c-cb02161de4db',
        'secret_key': '92F864C599B2CE2EC5186AD14C8B4110',
        'passphrase': 'Tencent@123'
    },
    'poit_main': {
        'api_key': '8650e46c-059b-431d-93cf-55f8c79babdb',
        'secret_key': '4C2BD2AC6A08615EA7F36A6251857FCE',
        'passphrase': 'Wu666666.'
    },
    'fangfang12': {
        'api_key': 'e5867a9a-93b7-476f-81ce-093c3aacae0d',
        'secret_key': '4624EE63A9BF3F84250AC71C9A37F47D',
        'passphrase': 'Tencent@123'
    },
    'dadanini': {
        'api_key': '1463198a-fad0-46ac-9ad8-2a386461782c',
        'secret_key': '1D112283B7456290056C253C56E9F3A6',
        'passphrase': 'Tencent@123'
    }
}


def send_telegram_message(message: str) -> bool:
    """发送Telegram消息"""
    try:
        if not TELEGRAM_CONFIG.exists():
            print(f"⚠️ Telegram配置文件不存在: {TELEGRAM_CONFIG}")
            return False
        
        with open(TELEGRAM_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        bot_token = config.get('bot_token')
        chat_id = config.get('chat_id')
        
        if not bot_token or not chat_id:
            print("⚠️ Telegram配置不完整")
            return False
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 发送Telegram消息失败: {e}")
        return False


def load_config(account_id: str) -> dict:
    """加载跟单配置"""
    config_file = CONFIG_DIR / f'copy_config_{account_id}.jsonl'
    
    if not config_file.exists():
        print(f"⚠️ 配置文件不存在: {config_file}")
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1].strip())
    except Exception as e:
        print(f"❌ 加载配置失败 ({account_id}): {e}")
    
    return None


def save_config(account_id: str, config: dict):
    """保存跟单配置"""
    config_file = CONFIG_DIR / f'copy_config_{account_id}.jsonl'
    
    try:
        # 添加时间戳
        config['updated_at'] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(config, ensure_ascii=False) + '\n')
        
        print(f"✅ 配置已保存 ({account_id})")
    except Exception as e:
        print(f"❌ 保存配置失败 ({account_id}): {e}")


def get_account_state() -> dict:
    """获取账户状态"""
    try:
        response = requests.get(ABC_STATE_API, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {}).get('accounts', {})
    except Exception as e:
        print(f"❌ 获取账户状态失败: {e}")
    
    return {}


def check_trigger_condition(account_state: dict, trigger_type: str, trigger_percent: float) -> bool:
    """检查是否满足触发条件"""
    pnl_pct = account_state.get('pnl_pct', 0)
    
    if trigger_type == 'profit':
        # 盈利触发：pnl_pct >= trigger_percent
        return pnl_pct >= trigger_percent
    elif trigger_type == 'loss':
        # 亏损触发：pnl_pct <= -trigger_percent
        return pnl_pct <= -trigger_percent
    
    return False


def get_top_coins(count: int = 8, ascending: bool = False) -> list:
    """获取常用币涨幅排名"""
    # 常用币列表
    common_coins = [
        'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'DOGE', 'ADA', 'TRX',
        'TON', 'LINK', 'DOT', 'MATIC', 'LTC', 'BCH', 'UNI', 'ATOM'
    ]
    
    try:
        # 获取币价数据
        response = requests.get(f'{API_BASE}/api/coin-price-tracker/latest', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                prices = data.get('data', {})
                
                # 计算涨幅
                coin_changes = []
                for coin in common_coins:
                    if coin in prices:
                        change_24h = prices[coin].get('change_24h', 0)
                        coin_changes.append({
                            'symbol': f'{coin}-USDT-SWAP',
                            'change_24h': change_24h
                        })
                
                # 排序
                coin_changes.sort(key=lambda x: x['change_24h'], reverse=not ascending)
                
                # 返回前N个
                return [c['symbol'] for c in coin_changes[:count]]
    except Exception as e:
        print(f"❌ 获取币种排名失败: {e}")
    
    # 默认返回ETH
    return ['ETH-USDT-SWAP']


def place_order(follower_account: str, config: dict) -> bool:
    """执行开仓"""
    try:
        okx_account_key = ACCOUNT_MAPPING.get(follower_account)
        if not okx_account_key:
            print(f"❌ 无效的账户ID: {follower_account}")
            return False
        
        okx_config = OKX_ACCOUNTS.get(okx_account_key)
        if not okx_config:
            print(f"❌ 找不到OKX配置: {okx_account_key}")
            return False
        
        strategy_type = config.get('strategy_type', 'manual')
        position_side = config.get('position_side', 'long')
        cost = config.get('cost', 10)
        leverage = config.get('leverage', 50)
        
        # 确定交易币种
        symbols = []
        if strategy_type == 'manual':
            symbols = [config.get('symbol', 'ETH-USDT-SWAP')]
        elif strategy_type == 'top_gainers_long':
            symbols = get_top_coins(8, ascending=False)  # 涨幅前8，做多
        elif strategy_type == 'top_gainers_short':
            symbols = get_top_coins(8, ascending=False)  # 涨幅前8，做空
        elif strategy_type == 'top_losers_long':
            symbols = get_top_coins(8, ascending=True)   # 涨幅后8，做多
        elif strategy_type == 'top_losers_short':
            symbols = get_top_coins(8, ascending=True)   # 涨幅后8，做空
        
        success_count = 0
        failed_count = 0
        
        for symbol in symbols:
            try:
                # 构建下单请求
                order_data = {
                    'apiKey': okx_config['api_key'],
                    'apiSecret': okx_config['secret_key'],
                    'passphrase': okx_config['passphrase'],
                    'instId': symbol,
                    'tdMode': 'cross',
                    'side': 'buy' if position_side == 'long' else 'sell',
                    'posSide': position_side,
                    'ordType': 'market',
                    'sz': str(cost),
                    'lever': str(leverage)
                }
                
                response = requests.post(OKX_TRADING_API, json=order_data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"✅ 开仓成功: {symbol} {position_side} {cost}U")
                        success_count += 1
                    else:
                        print(f"❌ 开仓失败: {symbol} - {result.get('error', '未知错误')}")
                        failed_count += 1
                else:
                    print(f"❌ API请求失败: {symbol} - HTTP {response.status_code}")
                    failed_count += 1
                
                # 避免频繁请求
                time.sleep(0.5)
            
            except Exception as e:
                print(f"❌ 开仓异常: {symbol} - {e}")
                failed_count += 1
        
        return success_count > 0
    
    except Exception as e:
        print(f"❌ 执行开仓失败: {e}")
        print(traceback.format_exc())
        return False


def monitor_copy_trading():
    """监控跟单系统"""
    print("\n" + "="*60)
    print(f"🚀 跟单监控系统启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 获取当前账户状态
    accounts_state = get_account_state()
    
    if not accounts_state:
        print("⚠️ 无法获取账户状态，跳过本次检查")
        return
    
    # 遍历所有跟单账户
    for follower_id in ['A', 'B', 'C', 'D']:
        config = load_config(follower_id)
        
        if not config:
            continue
        
        # 检查是否启用
        if not config.get('enabled', False):
            continue
        
        # 检查是否已执行
        if config.get('executed', False):
            continue
        
        target_account = config.get('target_account', '')
        
        # 检查目标账户
        if not target_account or target_account not in accounts_state:
            print(f"⚠️ {ACCOUNT_NAMES[follower_id]}: 目标账户无效 ({target_account})")
            continue
        
        # 不能跟踪自己
        if target_account == follower_id:
            print(f"⚠️ {ACCOUNT_NAMES[follower_id]}: 不能跟踪自己")
            continue
        
        target_state = accounts_state[target_account]
        trigger_type = config.get('trigger_type', 'profit')
        trigger_percent = config.get('trigger_percent', 0)
        
        # 更新最后检查时间
        config['last_check'] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        
        # 检查触发条件
        if check_trigger_condition(target_state, trigger_type, trigger_percent):
            pnl_pct = target_state.get('pnl_pct', 0)
            
            print(f"\n🎯 触发条件满足!")
            print(f"   跟单账户: {ACCOUNT_NAMES[follower_id]} ({follower_id})")
            print(f"   目标账户: {ACCOUNT_NAMES[target_account]} ({target_account})")
            print(f"   当前盈亏: {pnl_pct:.2f}%")
            print(f"   触发类型: {'盈利' if trigger_type == 'profit' else '亏损'}")
            print(f"   触发阈值: {trigger_percent}%")
            
            # 执行开仓
            success = place_order(follower_id, config)
            
            if success:
                # 标记为已执行
                config['executed'] = True
                config['last_trigger'] = datetime.now(timezone(timedelta(hours=8))).isoformat()
                config['trigger_pnl'] = pnl_pct
                
                # 发送Telegram通知
                message = f"""
🎯 <b>跟单系统触发通知</b>

👤 <b>跟单账户:</b> {ACCOUNT_NAMES[follower_id]} ({follower_id})
📊 <b>目标账户:</b> {ACCOUNT_NAMES[target_account]} ({target_account})
💰 <b>目标盈亏:</b> {pnl_pct:.2f}%
📈 <b>触发类型:</b> {'盈利' if trigger_type == 'profit' else '亏损'} ≥ {trigger_percent}%
🔔 <b>策略类型:</b> {config.get('strategy_type', 'manual')}
📍 <b>开仓方向:</b> {'做多' if config.get('position_side') == 'long' else '做空'}
💵 <b>开仓成本:</b> {config.get('cost', 10)}U
⚡ <b>杠杆倍数:</b> {config.get('leverage', 50)}x
✅ <b>执行状态:</b> 已开仓
⏰ <b>触发时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                send_telegram_message(message)
                
                print(f"✅ 跟单执行成功，已标记为已执行")
            else:
                print(f"❌ 跟单执行失败")
            
            # 保存配置
            save_config(follower_id, config)
        else:
            # 未触发，只保存检查时间
            if config.get('last_check'):
                save_config(follower_id, config)


def main():
    """主循环"""
    print("="*60)
    print("🚀 跟单监控系统")
    print("="*60)
    print(f"📂 配置目录: {CONFIG_DIR}")
    print(f"🔄 检查间隔: 30秒")
    print("="*60)
    
    while True:
        try:
            monitor_copy_trading()
        except Exception as e:
            print(f"❌ 监控异常: {e}")
            print(traceback.format_exc())
        
        # 等待30秒
        time.sleep(30)


if __name__ == '__main__':
    main()

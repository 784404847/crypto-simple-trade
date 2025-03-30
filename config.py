#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from pathlib import Path
import os
import fcntl

CONFIG_FILE = os.getenv('CONFIG_FILE', 'config.json')


def load_config():
    """
    加载配置文件，如果不存在则创建默认配置。

    返回:
        dict: 配置文件的字典形式。如果加载失败或文件不存在，则返回默认配置。
        None: 如果加载过程中发生错误，则返回None。
    """
    config_path = Path(CONFIG_FILE)

    try:
        if config_path.exists():
            # 打开配置文件并加共享锁，防止其他进程写入
            with open(config_path, 'r', encoding='utf-8') as f:
                fcntl.flock(f, fcntl.LOCK_SH)  # 加共享锁
                config = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)  # 释放锁
                return config
        else:
            # 如果配置文件不存在，创建默认配置并保存
            default_config = {
                'exchanges': {}
            }
            save_config(default_config)
            return default_config
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading config: {e}")
        return None


def save_config(config):
    """
    保存配置到文件。

    参数:
        config (dict): 要保存的配置字典。
    """
    try:
        # 打开配置文件并加排他锁，防止其他进程读取或写入
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)  # 加排他锁
            json.dump(config, f, indent=4)
            fcntl.flock(f, fcntl.LOCK_UN)  # 释放锁
    except IOError as e:
        print(f"Error saving config: {e}")


def add_exchange_api(exchange_id, key_id, api_key, secret, password=None):
    """
    添加或更新交易所API密钥。

    参数:
        exchange_id (str): 交易所的唯一标识符。
        key_id (str): API密钥的唯一标识符。
        api_key (str): API密钥。
        secret (str): API密钥的密钥。
        password (str, optional): API密钥的密码，默认为None。

    返回:
        bool: 如果成功添加或更新API密钥，则返回True；否则返回False。
    """
    config = load_config()

    if config is None:
        return False

    # 如果交易所不存在，则创建新的交易所条目
    if exchange_id not in config['exchanges']:
        config['exchanges'][exchange_id] = {}

    # 添加或更新API密钥
    config['exchanges'][exchange_id][key_id] = {
        'apiKey': api_key,
        'secret': secret
    }

    # 如果提供了密码，则添加到配置中
    if password:
        config['exchanges'][exchange_id][key_id]['password'] = password

    save_config(config)
    return True


def remove_exchange_api(exchange_id, key_id):
    """
    删除交易所API密钥。

    参数:
        exchange_id (str): 交易所的唯一标识符。
        key_id (str): API密钥的唯一标识符。

    返回:
        bool: 如果成功删除API密钥，则返回True；否则返回False。
    """
    config = load_config()

    if config is None:
        return False

    # 如果交易所和API密钥存在，则删除
    if exchange_id in config['exchanges'] and key_id in config['exchanges'][exchange_id]:
        del config['exchanges'][exchange_id][key_id]

        # 如果交易所下没有其他API密钥，则删除整个交易所
        if not config['exchanges'][exchange_id]:
            del config['exchanges'][exchange_id]

        save_config(config)
        return True

    return False

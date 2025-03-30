#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import ccxt
from config import load_config, add_exchange_api, remove_exchange_api
import logger

# 获取日志记录器
log = logger.get_logger('config_manager')


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """打印页面标题"""
    print("=" * 50)
    print("        交易所API密钥管理工具")
    print("=" * 50)
    print()


def list_exchanges():
    """列出所有支持的交易所"""
    print("支持的交易所:")
    exchanges = ccxt.exchanges
    for i, exchange in enumerate(exchanges):
        print(f"{i + 1}. {exchange}")
    print()


def show_current_config():
    """显示当前配置的交易所和API密钥"""
    config = load_config()

    print("当前配置:")
    if not config['exchanges']:
        print("  尚未配置任何交易所API密钥")

    for exchange_id, keys in config['exchanges'].items():
        print(f"  交易所: {exchange_id}")
        for key_id, key_data in keys.items():
            # 显示部分API密钥，保护隐私
            api_key = key_data['apiKey']
            masked_api_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '****'

            print(f"    - 账户ID: {key_id}")
            print(f"      API Key: {masked_api_key}")
    print()


def add_api_key():
    """添加新的API密钥"""
    clear_screen()
    print_header()

    print("添加新的API密钥")
    print("-" * 30)

    # 显示支持的交易所
    list_exchanges()

    # 获取用户输入并进行验证
    exchange_id = input("请输入交易所ID (例如: binance): ").strip().lower()
    if not exchange_id or exchange_id not in ccxt.exchanges:
        log.warning(f"用户尝试添加不支持的交易所 '{exchange_id}'")
        print(f"错误: 不支持的交易所 '{exchange_id}'")
        input("按任意键继续...")
        return

    key_id = input("请输入账户标识符 (例如: main_account): ").strip()
    if not key_id:
        print("错误: 账户标识符不能为空")
        input("按任意键继续...")
        return

    api_key = input("请输入API Key: ").strip()
    if not api_key:
        print("错误: API Key不能为空")
        input("按任意键继续...")
        return

    secret = input("请输入Secret Key: ").strip()
    if not secret:
        print("错误: Secret Key不能为空")
        input("按任意键继续...")
        return

    # 某些交易所需要额外的密码
    password = None
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange_instance = exchange_class()
        if 'password' in exchange_instance.requiredCredentials:
            password = input("请输入额外的密码 (如需要): ").strip()
    except Exception as e:
        log.error(f"初始化交易所实例失败: {e}")
        print("\n初始化交易所实例失败!")
        input("按任意键继续...")
        return

    # 添加API密钥
    log.info(f"添加 {exchange_id} 交易所的 {key_id} 账户API密钥")
    try:
        if add_exchange_api(exchange_id, key_id, api_key, secret, password):
            log.info(f"成功添加 {exchange_id} 的API密钥")
            print(f"\n成功添加 {exchange_id} 的API密钥!")
        else:
            log.error(f"添加 {exchange_id} 的API密钥失败")
            print("\n添加API密钥失败!")
    except Exception as e:
        log.error(f"添加API密钥时发生错误: {e}")
        print("\n添加API密钥时发生错误!")

    input("按任意键继续...")


def remove_api_key():
    """删除API密钥"""
    clear_screen()
    print_header()

    print("删除API密钥")
    print("-" * 30)

    # 显示当前配置
    show_current_config()

    # 获取用户输入并进行基本验证
    exchange_id = input("请输入要删除的交易所ID: ").strip().lower()
    if not exchange_id:
        print("交易所ID不能为空!")
        return

    key_id = input("请输入要删除的账户标识符: ").strip()
    if not key_id:
        print("账户标识符不能为空!")
        return

    # 确认删除
    confirm = input(f"确定要删除 {exchange_id} 的 {key_id} 账户密钥? (y/n): ").strip().lower()

    if confirm == 'y':
        log.info(f"尝试删除 {exchange_id} 交易所的 {key_id} 账户API密钥")
        try:
            if remove_exchange_api(exchange_id, key_id):
                log.info(f"成功删除 {exchange_id} 的 {key_id} 账户密钥")
                print(f"\n成功删除 {exchange_id} 的 {key_id} 账户密钥!")
            else:
                log.warning(f"删除 {exchange_id} 的 {key_id} 账户密钥失败，可能不存在")
                print("\n删除失败! 请检查交易所ID和账户标识符是否正确。")
        except Exception as e:
            log.error(f"删除 {exchange_id} 的 {key_id} 账户密钥时发生异常: {e}")
            print("\n删除过程中发生错误，请稍后重试。")
    else:
        log.info("用户取消删除API密钥操作")
        print("\n操作已取消!")

    input("按回车键继续...")


def test_api_connection():
    """
    测试与指定交易所的API连接,显示当前配置的交易所和API密钥。
    用户输入交易所ID和账户标识符后，加载配置并验证输入的有效性。
    如果输入有效，初始化交易所并测试连接，获取账户余额信息并显示。
    如果连接失败，捕获异常并显示错误信息。
    """
    clear_screen()
    print_header()

    print("测试API连接")
    print("-" * 30)

    # 显示当前配置
    show_current_config()

    # 获取用户输入
    exchange_id = input("请输入要测试的交易所ID: ").strip().lower()
    key_id = input("请输入要测试的账户标识符: ").strip()

    # 加载配置
    try:
        config = load_config()
        if not config:
            log.error("配置加载失败: 无法加载配置文件")
            print("\n错误: 无法加载配置文件!")
            input("按任意键继续...")
            return
    except Exception as e:
        log.error(f"配置加载失败: {str(e)}", exc_info=True)
        print(f"\n错误: 无法加载配置文件! 原因: {str(e)}")
        input("按任意键继续...")
        return

    if (exchange_id not in config['exchanges'] or
            key_id not in config['exchanges'][exchange_id]):
        log.warning(f"测试连接失败: 找不到 {exchange_id} 的 {key_id} 账户密钥")
        print(f"\n错误: 找不到 {exchange_id} 的 {key_id} 账户密钥!")
        input("按任意键继续...")
        return

    try:
        # 初始化交易所
        log.info(f"测试 {exchange_id} 交易所的 {key_id} 账户连接")
        exchange_class = getattr(ccxt, exchange_id)

        exchange = exchange_class({
            'apiKey': config['exchanges'][exchange_id][key_id]['apiKey'],
            'secret': config['exchanges'][exchange_id][key_id]['secret'],
            'password': config['exchanges'][exchange_id][key_id].get('password', ''),
            'enableRateLimit': True
        })
        # 从配置中读取测试网模式和代理
        exchange.set_sandbox_mode(config.get('sandbox_mode', False))
        exchange.proxies = config.get('proxies', {})

        # 测试连接
        print(f"\n正在测试与 {exchange_id} 的连接...")
        balance = exchange.fetch_balance()

        # 计算有余额的币种数量
        non_zero_balances = sum(1 for amount in balance['total'].values() if amount > 0)
        log.info(f"连接测试成功，获取到 {non_zero_balances} 个有余额的币种")

        print("\n连接成功! 已获取账户余额信息:")
        print("-" * 40)

        # 显示账户余额
        for currency, amount in balance['total'].items():
            if amount > 0:
                print(f"{currency}: {amount}")

    except ccxt.NetworkError as e:
        log.error(f"网络错误: {str(e)}", exc_info=True)
        print(f"\n连接失败! 网络错误: {str(e)}")
    except ccxt.ExchangeError as e:
        log.error(f"交易所错误: {str(e)}", exc_info=True)
        print(f"\n连接失败! 交易所错误: {str(e)}")
    except Exception as e:
        log.error(f"未知错误: {str(e)}", exc_info=True)
        print(f"\n连接失败! 错误: {str(e)}")

    input("\n按键继续...")


def main_menu():
    """
    API密钥管理工具的主菜单，负责显示菜单选项并根据用户选择调用相应的功能。
    它通过无限循环持续显示菜单，直到用户选择退出。
    用户可以选择添加API密钥、删除API密钥、测试API连接或退出程序
    """
    log.info("启动API密钥管理工具")
    while True:
        clear_screen()
        print_header()
        show_current_config()

        print("菜单选项:")
        print("1. 添加新的API密钥")
        print("2. 删除现有API密钥")
        print("3. 测试API连接")
        print("4. 退出")

        choice = input("\n请选择操作 (1-4): ").strip()

        if choice == '1':
            log.info("用户选择：添加新的API密钥")
            try:
                add_api_key()
            except Exception as e:
                log.error(f"添加API密钥时发生错误: {e}")
                print("\n添加API密钥时发生错误，请重试!")
        elif choice == '2':
            log.info("用户选择：删除现有API密钥")
            try:
                remove_api_key()
            except Exception as e:
                log.error(f"删除API密钥时发生错误: {e}")
                print("\n删除API密钥时发生错误，请重试!")
        elif choice == '3':
            log.info("用户选择：测试API连接")
            try:
                test_api_connection()
            except Exception as e:
                log.error(f"测试API连接时发生错误: {e}")
                print("\n测试API连接时发生错误，请重试!")
        elif choice == '4':
            log.info("用户选择退出API密钥管理工具")
            print("\n感谢使用! 再见!")
            break
        else:
            log.warning("用户输入了无效的选项")
            print("\n无效选择，请重试!")
            continue  # 直接返回菜单，无需等待用户按键


if __name__ == "__main__":
    main_menu()

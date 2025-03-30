#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import os
import sys
import csv
import time
import json
import ccxt
import asyncio
import curses
from datetime import datetime, timedelta
from config import load_config
import logger

# 获取日志记录器
log = logger.get_logger('simple_trade')


class SimpleTradeApp:
    def __init__(self):
        self.config = load_config()
        self.exchanges = {}
        self.current_exchange = None
        self.current_api_key = None
        self.current_symbol = None
        self.price = 0
        self.amount = 0
        self.stdscr = None
        log.info("初始化交易应用程序")
        self.init_exchanges()
        self.price_multiplier = 1
        self.amount_multiplier = 1
        self.trade_side = 'buy'  # 默认交易方向为买入

    def init_exchanges(self):
        """
        该函数用于初始化与多个交易所的连接。 它遍历配置中的交易所和账户信息，并设置测试网模式和代理。
        如果初始化成功，将交易所实例存储在self.exchanges中；
        如果失败，记录错误日志。
        最后检查是否成功初始化了任何交易所，并输出相应日志。
        """
        log.info("开始初始化交易所连接")
        for exchange_id, keys in self.config['exchanges'].items():
            for key_id, key_data in keys.items():
                try:
                    log.debug(f"正在初始化交易所 {exchange_id} 账户 {key_id}")
                    exchange_class = getattr(ccxt, exchange_id)
                    exchange = exchange_class({
                        'apiKey': key_data['apiKey'],
                        'secret': key_data['secret'],
                        'password': key_data.get('password', ''),
                        'enableRateLimit': True,
                    })

                    # 从配置中读取测试网模式和代理
                    exchange.set_sandbox_mode(self.config.get('sandbox_mode', False))
                    exchange.proxies = self.config.get('proxies', {})

                    if not exchange_id in self.exchanges:
                        self.exchanges[exchange_id] = {}
                    self.exchanges[exchange_id][key_id] = exchange
                    log.info(f"成功初始化交易所 {exchange_id} 账户 {key_id}")
                except ccxt.NetworkError as e:
                    log.error(f"网络错误导致初始化{exchange_id}交易所失败: {str(e)}", exc_info=True)
                except ccxt.AuthenticationError as e:
                    log.error(f"API密钥错误导致初始化{exchange_id}交易所失败: {str(e)}", exc_info=True)
                except Exception as e:
                    log.error(f"初始化{exchange_id}交易所失败: {str(e)}", exc_info=True)

        if not self.exchanges:
            log.warning("没有成功初始化任何交易所，请检查配置")
        else:
            log.info(f"成功初始化 {len(self.exchanges)} 个交易所")

    def select_exchange_and_key(self):
        """选择交易所和API密钥"""
        if not self.exchanges:
            log.warning("没有可用的交易所，无法选择")
            return False

        # 列表选择界面
        exchanges_list = []
        for exchange_id, keys in self.exchanges.items():
            for key_id in keys:
                exchanges_list.append((exchange_id, key_id))

        log.info("显示交易所和账户选择页面")
        selected = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "交易所和账户选择页面", curses.A_BOLD)
            self.stdscr.addstr(1, 0, "上下键选择, 回车确认, q退出", curses.A_NORMAL)

            for i, (exchange_id, key_id) in enumerate(exchanges_list):
                if i == selected:
                    self.stdscr.addstr(i + 3, 0, f"* {exchange_id} - {key_id}", curses.A_REVERSE)
                else:
                    self.stdscr.addstr(i + 3, 0, f"  {exchange_id} - {key_id}")

            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(exchanges_list) - 1:
                selected += 1
            elif key == ord('\n'):  # Enter key
                self.current_exchange = exchanges_list[selected][0]
                self.current_api_key = exchanges_list[selected][1]
                log.info(f"用户选择了交易所 {self.current_exchange} 账户 {self.current_api_key}")
                return True
            elif key == ord('q'):
                log.info("用户退出交易所选择")
                return False

    def select_symbol(self):
        """选择交易产品"""
        exchange = self.exchanges[self.current_exchange][self.current_api_key]

        try:
            log.info(f"正在加载 {self.current_exchange} 的交易产品列表")
            markets = exchange.load_markets()
            symbols = list(markets.keys())
            log.info(f"成功加载 {len(symbols)} 个交易产品")

            selected = 0
            input_buffer = ""  # 用于存储用户输入的搜索文本

            while True:
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, f"交易产品选择 - {self.current_exchange}", curses.A_BOLD)
                self.stdscr.addstr(1, 0, "上下键选择, 回车确认, 直接输入搜索, Esc清除搜索, q返回", curses.A_NORMAL)
                self.stdscr.addstr(2, 0, f"搜索: {input_buffer}", curses.A_NORMAL)

                # 根据输入过滤交易产品
                filtered_symbols = [s for s in symbols if input_buffer.lower() in s.lower()]

                # 计算可用行数（减去标题和说明行）
                max_rows = self.stdscr.getmaxyx()[0] - 4
                display_offset = 3

                # 防止选择索引超出范围
                if len(filtered_symbols) == 0:
                    selected = 0
                    self.stdscr.addstr(display_offset, 0, "没有匹配的交易产品", curses.A_NORMAL)
                else:
                    selected = min(selected, len(filtered_symbols) - 1)
                    start_idx = max(0, selected - 10)
                    for i, symbol in enumerate(filtered_symbols[start_idx:start_idx + min(20, max_rows)]):
                        display_idx = start_idx + i
                        if display_idx == selected:
                            self.stdscr.addstr(i + display_offset, 0, f"* {symbol}", curses.A_REVERSE)
                        else:
                            self.stdscr.addstr(i + display_offset, 0, f"  {symbol}")

                self.stdscr.refresh()

                key = self.stdscr.getch()

                if key == 27:  # Esc键 - 清除搜索内容
                    input_buffer = ""
                    selected = 0
                elif key == curses.KEY_UP and selected > 0:
                    selected -= 1
                elif key == curses.KEY_DOWN and selected < len(filtered_symbols) - 1:
                    selected += 1
                elif key == ord('\n'):  # Enter键 - 确认选择
                    if filtered_symbols:
                        self.current_symbol = filtered_symbols[selected]
                        log.info(f"用户选择了交易产品 {self.current_symbol}")

                        # 获取市场价格精度等信息
                        market = markets[self.current_symbol]
                        log.info(f"获取交易产品信息成功: {market}")
                        self.min_price_precision = market['precision']['price']
                        self.price_precision = self.min_price_precision
                        self.min_amount_precision = market['precision']['amount']
                        self.amount_precision = self.min_amount_precision
                        self.min_amount = self.amount_precision
                        self.min_value = market.get('limits', {}).get('cost', {}).get('min', 0)

                        log.debug(
                            f"交易产品信息: 价格精度={self.price_precision}, 数量精度={self.amount_precision}, 最小数额={self.min_value}")

                        # 获取当前价格
                        ticker = exchange.fetch_ticker(self.current_symbol)
                        self.price = ticker['last']
                        self.amount = self.amount_precision
                        if self.price is not None and self.price > 0 and self.min_value is not None and self.min_value > 0:
                            # 根据价格进度和下单额度计算下单数量
                            self.min_amount = (round(self.min_value / self.price / self.amount_precision,
                                                     0) + 1) * self.amount_precision
                            self.amount = self.min_amount

                        log.info(f"当前价格: {self.price}, 初始下单数量: {self.amount}")

                        return True
                elif key == ord('q'):
                    log.info("用户退出交易产品选择")
                    return False
                elif key == 127 or key == 8:  # Backspace键 - 删除输入的最后一个字符
                    input_buffer = input_buffer[:-1]
                    selected = 0
                elif 32 <= key <= 126:
                    input_buffer += chr(key)
                    selected = 0  # 重置选择索引

        except Exception as e:
            log.error(f"获取交易产品失败: {str(e)}", exc_info=True)
            self.show_error(f"获取交易产品失败: {str(e)}")
            return False

    def main_trading_screen(self):
        """主交易界面"""
        exchange = self.exchanges[self.current_exchange][self.current_api_key]
        log.info(f"进入主交易界面 exchange {exchange}")
        while True:
            try:
                # 获取最新市场数据
                ticker = exchange.fetch_ticker(self.current_symbol)
                log.debug(f"获取最新市场数据成功: {ticker}")

                balances = exchange.fetch_balance()
                log.debug(f"获取账户余额成功: {balances}")

                # 解析交易对获取base和quote
                market = exchange.market(self.current_symbol)
                base = market['base']
                quote = market['quote']

                base_balance = balances.get(base, {}).get('free', 0)
                quote_balance = balances.get(quote, {}).get('free', 0)

                # 显示交易界面
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, f"交易界面 - {self.current_exchange}", curses.A_BOLD)
                self.stdscr.addstr(0, 50, f"{base}余额: {base_balance:.8f}", curses.A_NORMAL)
                self.stdscr.addstr(0, 80, f"{quote}余额: {quote_balance:.8f}", curses.A_NORMAL)

                self.stdscr.addstr(2, 0, f"交易对: {self.current_symbol}", curses.A_NORMAL)
                self.stdscr.addstr(3, 0, f"市场价格: {ticker['last']:.8f}", curses.A_NORMAL)
                self.stdscr.addstr(4, 0,
                                   f"买入价: {ticker['bid'] if ticker['bid'] else 'None'} | 卖出价: {ticker['ask'] if ticker['ask'] else 'None'}",
                                   curses.A_NORMAL)

                # 添加交易方向显示，买入显示绿色，卖出显示红色
                side_color = curses.color_pair(2) if self.trade_side == 'buy' else curses.color_pair(1)
                self.stdscr.addstr(5, 0, f"交易方向: {self.trade_side.upper()}", side_color | curses.A_BOLD)

                self.stdscr.addstr(6, 0, f"当前价格: {self.price:.8f}", curses.A_NORMAL)

                self.stdscr.addstr(7, 0, f"下单数量: {self.amount:.8f}", curses.A_NORMAL)
                self.stdscr.addstr(8, 0, f"价格精度: {self.price_precision:.8f}", curses.A_NORMAL)
                self.stdscr.addstr(9, 0, f"数量精度: {self.amount_precision:.8f}", curses.A_NORMAL)
                self.stdscr.addstr(10, 0, f"最小下单量: {self.min_amount:.8f}", curses.A_NORMAL)

                # 操作说明
                self.stdscr.addstr(20, 0, "操作说明:", curses.A_BOLD)
                self.stdscr.addstr(21, 0, "s: 选择交易产品 | ↑/↓: 调整价格 | a/z: 调整数量 | 空格: 下单")
                self.stdscr.addstr(22, 0, "r: 重置参数 | o: 查看挂单 | h: 查看历史成交 | b: 查看余额")
                self.stdscr.addstr(23, 0, "w: 10x价格精度 | e: 0.1x价格精度 | t: 切换交易方向 | q: 退出")

                self.stdscr.refresh()

                # 处理输入
                key = self.stdscr.getch()

                if key == ord('q'):
                    log.info("用户选择退出交易界面")
                    break
                elif key == ord('w'):
                    self.price_precision = max(self.price_precision * 10, self.min_price_precision)
                elif key == ord('e'):
                    self.price_precision = max(self.price_precision / 10, self.min_price_precision)
                elif key == curses.KEY_UP:
                    # 价格上调
                    old_price = self.price
                    self.price += self.price_precision
                    self.price = round(self.price / self.price_precision, 0) * self.price_precision
                    log.debug(f"价格上调: {old_price} -> {self.price} precision {self.price_precision}")
                elif key == curses.KEY_DOWN:
                    # 价格下调
                    old_price = self.price
                    self.price -= self.price_precision
                    self.price = max(self.price_precision,
                                     round(self.price / self.price_precision, 0) * self.price_precision)
                    log.debug(f"价格下调: {old_price} -> {self.price}")
                elif key == ord('a'):
                    # 数量上调
                    old_amount = self.amount
                    self.amount += (self.amount_precision * 10)
                    self.amount = round(self.amount / self.amount_precision, 0) * self.amount_precision
                    log.debug(f"数量上调: {old_amount} -> {self.amount}")
                elif key == ord('z'):
                    # 数量下调
                    old_amount = self.amount
                    self.amount -= (self.amount_precision * 10)
                    self.amount = max(self.min_amount,
                                      round(self.amount / self.amount_precision, 0) * self.amount_precision)
                    log.debug(f"数量下调: {old_amount} -> {self.amount}")
                elif key == ord(' '):
                    # 下单
                    if self.amount < self.min_amount:
                        log.warning(f"下单数量 {self.amount} 小于最小数量 {self.min_amount}")
                        self.show_error(f"下单数量必须大于最小数量 {self.min_amount}")
                    else:
                        try:
                            log.info(
                                f"尝试下单: 交易对={self.current_symbol}, 方向={self.trade_side}, 数量={self.amount}")
                            order = exchange.create_limit_order(
                                symbol=self.current_symbol,
                                side=self.trade_side,
                                amount=self.amount,
                                price=self.price
                            )
                            log.info(f"下单成功: 订单ID={order['id']}")
                            self.show_message(f"下单成功: {order['id']}")
                            self.save_order_to_csv(order)
                        except Exception as e:
                            log.error(f"下单失败: {str(e)}", exc_info=True)
                            self.show_error(f"下单错误: {str(e)}")
                elif key == ord('r'):
                    # 重置参数
                    log.info("用户重置交易参数")
                    ticker = exchange.fetch_ticker(self.current_symbol)
                    self.price = ticker['last']
                    self.amount = self.min_amount
                    self.price_precision = self.min_price_precision
                    self.amount_precision = self.min_amount_precision
                    log.debug(f"参数重置为: 价格={self.price}, 数量={self.amount}")
                elif key == ord('o'):
                    # 查看挂单
                    log.info("用户查看挂单列表")
                    self.view_open_orders()
                elif key == ord('b'):
                    # 查看余额
                    log.info("用户查看余额")
                    self.view_balances()
                elif key == ord('h'):
                    # 查看历史订单
                    log.info("用户查看成交历史")
                    self.view_trade_history()
                elif key == ord('s'):
                    # 选择新的交易产品
                    log.info("用户选择新的交易产品")
                    if self.select_symbol():
                        continue
                elif key == ord('t'):
                    # 切换交易方向
                    self.trade_side = 'sell' if self.trade_side == 'buy' else 'buy'
                    log.info(f"用户切换交易方向为: {self.trade_side}")

            except Exception as e:
                self.show_error(f"错误: {str(e)}")
                time.sleep(2)

    def show_error(self, message):
        """显示错误信息"""
        log.error(f"错误: {message}", exc_info=True)
        height, width = self.stdscr.getmaxyx()
        self.stdscr.addstr(height - 2, 0, "下单失败", curses.A_BOLD | curses.COLOR_RED)
        self.stdscr.addstr(height - 1, 0, f"下单错误: {message}", curses.A_BOLD | curses.COLOR_RED)
        self.stdscr.refresh()
        time.sleep(2)

    def show_message(self, message):
        """显示消息"""
        log.info(f"消息: {message}")
        height, width = self.stdscr.getmaxyx()
        self.stdscr.addstr(height - 2, 0, "下单成功", curses.A_BOLD)
        self.stdscr.addstr(height - 1, 0, message, curses.A_NORMAL)
        self.stdscr.refresh()
        time.sleep(2)

    def view_open_orders(self):
        """查看挂单列表"""
        exchange = self.exchanges[self.current_exchange][self.current_api_key]

        try:
            log.info(f"获取 {self.current_exchange} 的挂单列表")
            orders = exchange.fetch_open_orders(self.current_symbol)
            log.info(f"成功获取symbol {self.current_symbol} {len(orders)}  个挂单")

            # 按照时间倒序
            orders.sort(key=lambda x: x['timestamp'], reverse=True)

            selected = 0  # 选中的订单索引

            while True:  # 外层循环，用于刷新订单列表
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, f"挂单列表 - {self.current_exchange}", curses.A_BOLD)
                self.stdscr.addstr(1, 0, "上下键选择, 回车撤单, q返回", curses.A_NORMAL)

                if not orders:
                    self.stdscr.addstr(3, 0, "暂无挂单", curses.A_NORMAL)
                else:
                    self.stdscr.addstr(2, 0, "订单ID", curses.A_UNDERLINE)
                    self.stdscr.addstr(2, 20, "交易对", curses.A_UNDERLINE)
                    self.stdscr.addstr(2, 35, "类型", curses.A_UNDERLINE)
                    self.stdscr.addstr(2, 45, "方向", curses.A_UNDERLINE)
                    self.stdscr.addstr(2, 55, "价格", curses.A_UNDERLINE)
                    self.stdscr.addstr(2, 70, "数量", curses.A_UNDERLINE)
                    self.stdscr.addstr(2, 85, "时间", curses.A_UNDERLINE)

                    display_count = min(15, len(orders))  # 限制显示条数

                    # 防止选择索引越界
                    selected = min(selected, display_count - 1) if display_count > 0 else 0

                    for i in range(display_count):
                        order = orders[i]
                        date_str = datetime.fromtimestamp(order['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

                        # 如果是选中的行，使用高亮显示
                        attr = curses.A_REVERSE if i == selected else curses.A_NORMAL

                        self.stdscr.addstr(i + 3, 0, str(order['id'])[:15], attr)
                        self.stdscr.addstr(i + 3, 20, order['symbol'], attr)
                        self.stdscr.addstr(i + 3, 35, order['type'], attr)
                        self.stdscr.addstr(i + 3, 45, order['side'], attr)
                        self.stdscr.addstr(i + 3, 55, str(order['price']), attr)
                        self.stdscr.addstr(i + 3, 70, str(order['amount']), attr)
                        self.stdscr.addstr(i + 3, 85, date_str, attr)

                self.stdscr.refresh()

                # 处理键盘输入
                key = self.stdscr.getch()

                if key == ord('q'):
                    log.info("用户退出挂单列表页面")
                    break
                elif key == curses.KEY_UP and selected > 0:
                    selected -= 1
                elif key == curses.KEY_DOWN and selected < len(orders) - 1:
                    selected += 1
                elif key == ord('\n') and orders:  # 回车键撤单
                    try:
                        order_to_cancel = orders[selected]
                        order_id = order_to_cancel['id']
                        symbol = order_to_cancel['symbol']

                        # 显示确认信息
                        self.stdscr.addstr(20, 0, f"确认撤销订单 {order_id}? (y/n)", curses.A_BOLD)
                        self.stdscr.refresh()

                        # 等待确认
                        confirm_key = self.stdscr.getch()
                        if confirm_key == ord('y'):
                            log.info(f"用户确认撤销订单: {order_id}, 交易对: {symbol}")

                            # 撤销订单
                            result = exchange.cancel_order(order_id, symbol)
                            log.info(f"撤单成功: {result}")

                            # 显示成功信息
                            self.stdscr.addstr(21, 0, f"撤单成功: {order_id}", curses.A_NORMAL)
                            self.stdscr.refresh()
                            time.sleep(1)

                            # 重新获取订单列表
                            orders = exchange.fetch_open_orders(self.current_symbol)
                            log.info(f"刷新订单列表，现有 {len(orders)} 个挂单")

                            # 重置选择索引
                            selected = 0 if selected >= len(orders) else selected
                        else:
                            log.info("用户取消撤单操作")
                    except Exception as e:
                        log.error(f"撤单失败: {str(e)}", exc_info=True)
                        self.stdscr.addstr(21, 0, f"撤单失败: {str(e)}", curses.A_BOLD | curses.COLOR_RED)
                        self.stdscr.refresh()
                        time.sleep(2)

        except Exception as e:
            log.error(f"获取挂单失败: {str(e)}", exc_info=True)
            self.show_error(f"获取挂单失败: {str(e)}")

    def view_balances(self):
        """查看余额页面"""
        exchange = self.exchanges[self.current_exchange][self.current_api_key]

        try:
            log.info(f"获取 {self.current_exchange} 的账户余额")
            balances = exchange.fetch_balance()

            # 计算有余额的币种数量
            non_zero_balances = sum(1 for amount in balances['total'].values() if amount > 0)
            log.info(f"成功获取余额，有 {non_zero_balances} 个币种有余额")

            self.stdscr.clear()
            self.stdscr.addstr(0, 0, f"余额列表 - {self.current_exchange}", curses.A_BOLD)
            self.stdscr.addstr(1, 0, "按q返回", curses.A_NORMAL)

            self.stdscr.addstr(2, 0, "币种", curses.A_UNDERLINE)
            self.stdscr.addstr(2, 15, "可用", curses.A_UNDERLINE)
            self.stdscr.addstr(2, 30, "冻结", curses.A_UNDERLINE)
            self.stdscr.addstr(2, 45, "总量", curses.A_UNDERLINE)

            row = 3
            for currency, data in balances['total'].items():
                if data > 0:  # 只显示有余额的币种
                    free = balances['free'].get(currency, 0)
                    used = balances['used'].get(currency, 0)

                    self.stdscr.addstr(row, 0, currency, curses.A_NORMAL)
                    self.stdscr.addstr(row, 15, f"{free:.8f}", curses.A_NORMAL)
                    self.stdscr.addstr(row, 30, f"{used:.8f}", curses.A_NORMAL)
                    self.stdscr.addstr(row, 45, f"{data:.8f}", curses.A_NORMAL)

                    row += 1
                    if row > 20:  # 限制显示条数
                        break

            self.stdscr.refresh()

            # 等待按键返回
            while True:
                key = self.stdscr.getch()
                if key == ord('q'):
                    log.info("用户退出余额页面")
                    break

        except Exception as e:
            log.error(f"获取余额失败: {str(e)}", exc_info=True)
            self.show_error(f"获取余额失败: {str(e)}")

    def view_trade_history(self):
        """查看成交历史"""
        exchange = self.exchanges[self.current_exchange][self.current_api_key]

        try:
            # 获取过去一天的成交
            since = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
            log.info(f"获取 {self.current_symbol} 的成交历史，时间范围：过去1天")
            trades = exchange.fetch_my_trades(symbol=self.current_symbol, since=since)
            log.info(f"成功获取 {len(trades)} 条成交记录")
            # 倒序处理
            trades.reverse()

            self.stdscr.clear()
            self.stdscr.addstr(0, 0, f"成交历史 - {self.current_symbol}", curses.A_BOLD)
            self.stdscr.addstr(1, 0, "按q返回", curses.A_NORMAL)

            if not trades:
                self.stdscr.addstr(3, 0, "暂无成交记录", curses.A_NORMAL)
            else:
                self.stdscr.addstr(2, 0, "成交ID", curses.A_UNDERLINE)
                self.stdscr.addstr(2, 15, "订单ID", curses.A_UNDERLINE)
                self.stdscr.addstr(2, 30, "方向", curses.A_UNDERLINE)
                self.stdscr.addstr(2, 40, "价格", curses.A_UNDERLINE)
                self.stdscr.addstr(2, 55, "数量", curses.A_UNDERLINE)
                self.stdscr.addstr(2, 70, "时间", curses.A_UNDERLINE)

                for i, trade in enumerate(trades):
                    if i > 30:  # 限制显示条数
                        break

                    date_str = datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

                    self.stdscr.addstr(i + 3, 0, str(trade['id'])[:10], curses.A_NORMAL)
                    self.stdscr.addstr(i + 3, 15, str(trade['order'])[:10], curses.A_NORMAL)
                    self.stdscr.addstr(i + 3, 30, trade['side'], curses.A_NORMAL)
                    self.stdscr.addstr(i + 3, 40, f"{trade['price']:.8f}", curses.A_NORMAL)
                    self.stdscr.addstr(i + 3, 55, f"{trade['amount']:.8f}", curses.A_NORMAL)
                    self.stdscr.addstr(i + 3, 70, date_str, curses.A_NORMAL)

            self.stdscr.refresh()

            # 等待按键返回
            while True:
                key = self.stdscr.getch()
                if key == ord('q'):
                    log.info("用户退出成交历史页面")
                    break

        except Exception as e:
            log.error(f"获取成交历史失败: {str(e)}", exc_info=True)
            self.show_error(f"获取成交历史失败: {str(e)}")

    def save_order_to_csv(self, order):
        """保存下单录到CSV文件"""
        filename = f"order_{self.current_exchange}_{self.current_api_key}.csv"

        # 检查文件是否存在
        file_exists = os.path.isfile(filename)

        try:
            log.info(f"保存下单记录到文件 {filename}")
            with open(filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'exchange', 'api_key', 'symbol', 'order_id',
                              'side', 'price', 'amount', 'cost', 'status']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'exchange': self.current_exchange,
                    'api_key': self.current_api_key,
                    'symbol': self.current_symbol,
                    'order_id': order['id'],
                    'side': order['side'],
                    'price': self.price,
                    'amount': self.amount,
                    'cost': self.price * self.amount,
                    'status': order['status']
                }
                writer.writerow(record)
                log.info(f"成功保存订单记录: {record}")
        except Exception as e:
            log.error(f"保存订单记录失败: {str(e)}", exc_info=True)

    def run(self):
        """
        负责启动交易应用程序。它首先初始化终端界面和颜色设置，
        然后进入主循环，依次执行选择交易所、选择交易产品、进入交易主界面等操作。
        如果用户选择退出或发生错误，程序会捕获异常并恢复终端设置。
        """
        try:
            log.info("开始运行交易应用程序")
            # 初始化终端界面和颜色
            self.stdscr = curses.initscr()
            curses.start_color()
            # 将终端设置为"cbreak"模式，允许立即读取输入而不等待回车键
            curses.cbreak()
            # 禁止输入字符在终端上回显。
            curses.noecho()
            self.stdscr.keypad(True)
            # 初始化颜色
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

            log.info("终端界面初始化成功")
            # 主循环
            while True:
                if not self.select_exchange_and_key():
                    log.info("用户退出程序")
                    break

                if not self.select_symbol():
                    log.info("用户取消选择交易产品，返回交易所选择")
                    continue
                # 进入交易主界面
                self.main_trading_screen()

        except curses.error as e:
            log.error(f"终端初始化错误: {str(e)}", exc_info=True)
            print(f"终端初始化错误: {str(e)}")
        except KeyboardInterrupt:
            log.info("用户中断程序")
        except Exception as e:
            log.error(f"程序发生错误: {str(e)}", exc_info=True)
            print(f"程序错误: {str(e)}")
        finally:
            # 恢复终端设置
            if self.stdscr is not None:
                self.stdscr.keypad(False)
                curses.echo()
                curses.nocbreak()
                curses.endwin()
            log.info("交易应用程序已关闭")


def main():
    log.info("==== 简易加密货币交易系统启动 ====")
    app = SimpleTradeApp()
    app.run()
    log.info("==== 简易加密货币交易系统关闭 ====")


if __name__ == "__main__":
    main()

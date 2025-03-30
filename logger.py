#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading

# 创建日志目录
LOG_DIR = 'logs'
try:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
except OSError as e:
    print(f"无法创建日志目录 {LOG_DIR}: {e}")
    raise

# 日志文件路径
LOG_FILE_LOCK = threading.Lock()


def get_log_file():
    with LOG_FILE_LOCK:
        return os.path.join(LOG_DIR, f'trade_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')


LOG_FILE = get_log_file()


# 配置根日志记录器
def setup_logger(logger_name=None, log_level=logging.INFO, max_bytes=10 * 1024 * 1024, backup_count=5):
    """
    设置日志记录器，返回配置好的日志对象

    参数:
    - logger_name: 日志记录器名称，如果为None，则使用根日志记录器
    - log_level: 日志级别，默认为INFO
    - max_bytes: 日志文件最大大小，默认为10MB
    - backup_count: 保留的备份文件数量，默认为5

    返回:
    - 配置好的日志记录器对象
    """
    # 获取日志记录器
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    # 如果已经配置过处理程序，则直接返回
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(log_level)

    # 创建文件处理程序 (RotatingFileHandler，限制文件大小并自动轮换)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=max_bytes,  # 可配置的文件大小
        backupCount=backup_count,  # 可配置的备份文件数量
        encoding='utf-8'
    )

    # 设置格式化器
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 设置处理程序的格式化器
    file_handler.setFormatter(formatter)

    # 添加处理程序到日志记录器
    logger.addHandler(file_handler)

    return logger


# 默认日志记录器
logger = setup_logger()


def get_logger(name=None):
    """
    获取指定名称的日志记录器

    参数:
    - name: 日志记录器名称，如果为None，则返回默认日志记录器

    返回:
    - 日志记录器对象
    """
    if name:
        return setup_logger(name)
    return logger


# 简便的日志记录函数
def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    logger.exception(msg, *args, **kwargs)

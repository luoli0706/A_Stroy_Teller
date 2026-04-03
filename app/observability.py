import logging
import os
from datetime import datetime
from pathlib import Path
from app.config import LOG_DIR

def create_run_logger():
    """创建一个具备强制落盘能力的运行日志记录器。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_name = f"run_{timestamp}.log"
    log_file_path = LOG_DIR / log_file_name

    # 统一使用名为 'story_teller' 的基础 logger 结构
    logger = logging.getLogger(f"run_{timestamp}")
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加 Handler
    if not logger.handlers:
        # 文件输出
        fh = logging.FileHandler(log_file_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        
        # 格式化
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        
        # 控制台输出（可选，因为测试脚本也会打印）
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger, str(log_file_path)

def log_event(logger_name: str, message: str, level: int = logging.INFO):
    """确保日志能即时写入。"""
    logger = logging.getLogger(logger_name)
    logger.log(level, message)
    # 强制刷新所有 FileHandler
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()

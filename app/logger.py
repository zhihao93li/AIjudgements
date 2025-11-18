"""日志配置"""

import sys
from pathlib import Path
from loguru import logger

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


def setup_logger():
    """配置 loguru 日志"""
    
    # 移除默认的 handler
    logger.remove()
    
    # 添加控制台输出（带颜色）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    
    # 添加文件输出（所有级别）
    logger.add(
        log_dir / "ai_judge_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # 每天轮转
        retention="7 days",  # 保留 7 天
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
    )
    
    # 添加错误日志文件
    logger.add(
        log_dir / "ai_judge_error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="30 days",  # 错误日志保留 30 天
        compression="zip",
        encoding="utf-8",
    )
    
    logger.info("日志系统初始化完成")


# 自动设置日志
setup_logger()


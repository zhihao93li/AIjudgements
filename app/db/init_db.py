"""数据库初始化脚本"""

import asyncio
from app.db.database import init_database
from loguru import logger


async def main():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    await init_database()
    logger.success("数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())


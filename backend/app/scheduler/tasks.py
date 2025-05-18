import asyncio
from datetime import datetime

from loguru import logger

from app.scheduler.manager import scheduler_manager


async def sample_task() -> None:
    """
    示例定时任务
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"示例定时任务执行时间: {current_time}")
    # 这里可以添加实际的业务逻辑
    await asyncio.sleep(1)  # 模拟异步操作


async def db_cleanup_task() -> None:
    """
    数据库清理任务
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"数据库清理任务执行时间: {current_time}")
    # 这里可以添加实际的数据库清理逻辑
    await asyncio.sleep(2)  # 模拟异步操作


def register_tasks() -> None:
    """
    注册所有定时任务
    """
    # 每5分钟执行一次示例任务
    scheduler_manager.add_job(
        func=sample_task,
        job_id="sample_task",
        trigger="interval",
        minutes=5,
    )
    
    # 每天凌晨3点执行数据库清理任务
    scheduler_manager.add_job(
        func=db_cleanup_task,
        job_id="db_cleanup_task",
        trigger="cron",
        hour=3,
        minute=0,
    ) 
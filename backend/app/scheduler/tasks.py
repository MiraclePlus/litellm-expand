import asyncio
from datetime import datetime

from app.logger import logger


async def _sample_task_impl() -> None:
    """
    示例定时任务的异步实现
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"示例定时任务执行时间: {current_time}")
    # 这里可以添加实际的业务逻辑
    await asyncio.sleep(1)  # 模拟异步操作


def sample_task() -> None:
    """
    示例定时任务的非异步包装器
    
    APScheduler在处理异步函数时可能会有问题，因此我们使用这个包装函数
    来确保异步函数被正确执行。
    """
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    try:
        # 在该循环中运行异步任务
        loop.run_until_complete(_sample_task_impl())
    finally:
        # 关闭循环
        loop.close()


async def _db_cleanup_task_impl() -> None:
    """
    数据库清理任务的异步实现
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"数据库清理任务执行时间: {current_time}")
    # 这里可以添加实际的数据库清理逻辑
    await asyncio.sleep(2)  # 模拟异步操作


def db_cleanup_task() -> None:
    """
    数据库清理任务的非异步包装器
    
    APScheduler在处理异步函数时可能会有问题，因此我们使用这个包装函数
    来确保异步函数被正确执行。
    """
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    try:
        # 在该循环中运行异步任务
        loop.run_until_complete(_db_cleanup_task_impl())
    finally:
        # 关闭循环
        loop.close()


# def register_tasks() -> None:
#     """
#     注册所有定时任务
#     """
#     # 每5分钟执行一次示例任务
#     # scheduler_manager.add_job(
#     #     func=sample_task,
#     #     job_id="sample_task",
#     #     trigger="interval",
#     #     minutes=5,
#     # )
    
#     # 每天凌晨3点执行数据库清理任务
#     # scheduler_manager.add_job(
#     #     func=db_cleanup_task,
#     #     job_id="db_cleanup_task",
#     #     trigger="cron",
#     #     hour=3,
#     #     minute=0,
#     # )
    
#     # 每小时执行一次Identity评估数据生成任务
#     scheduler_manager.add_job(
#         func=identity_eval_task,
#         job_id="identity_eval_task",
#         trigger="interval",
#         # hours=1,
#         seconds=1,
#         next_run_time=datetime.now() + timedelta(seconds=10),  # Start 10 seconds from now
#     ) 
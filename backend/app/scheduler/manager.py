from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.scheduler.identity_eval_task import identity_eval_task
from app.scheduler.llm_connectivity_task import llm_connectivity_task
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from app.core.config import settings

from app.logger import logger


class SchedulerManager:
    """定时任务管理器"""

    def __init__(self) -> None:
        self._scheduler: Optional[AsyncIOScheduler] = None

    def init_scheduler(self, app: FastAPI) -> None:
        """
        初始化调度器

        Args:
            app: FastAPI应用实例
        """
        # 配置作业存储
        # jobstores = {
        #     "default": SQLAlchemyJobStore(url=str(settings.SQLALCHEMY_DATABASE_URI))
        # }

        # 配置执行器
        executors = {"default": ThreadPoolExecutor(20)}

        # 创建调度器
        self._scheduler = AsyncIOScheduler(
            # jobstores=jobstores,
            executors=executors,
            timezone="Asia/Shanghai",
        )

        # 启动时清理所有失效的任务
        self._scheduler.remove_all_jobs()

        # 注册所有任务
        self._register_jobs()

        # 启动调度器
        self._scheduler.start()

        # 将调度器添加到应用程序状态
        app.state.scheduler = self._scheduler

    async def shutdown(self) -> None:
        """关闭调度器"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("调度器已关闭")

    def _register_jobs(self) -> None:

        if settings.ENVIRONMENT != "local":  # 仅在非开发环境下注册任务
            self._scheduler.add_job(
                identity_eval_task,
                "cron",
                id="identity_eval_task",
                replace_existing=True,
                max_instances=1,  # 最大实例数
                hour=0, minute=0,  # 每天 0 点执行
                # next_run_time=datetime.now(ZoneInfo('Asia/Shanghai')) + timedelta(seconds=10),
            )
            logger.info(f"注册定时任务: identity_eval_task")

            # 注册LLM连通性检测任务
            self._scheduler.add_job(
                llm_connectivity_task,
                "interval",
                id="llm_connectivity_task",
                replace_existing=True,
                hours=1,  # 每小时执行一次
                # next_run_time=datetime.now() + timedelta(seconds=10),
            )
            logger.info(f"注册定时任务: llm_connectivity_task")

        # 评测分数基准值差异
        # self._scheduler.add_job(
        #     intellectual_fluctuation_task,
        #     trigger="interval",
        #     id="intellectual_fluctuation_task",
        #     replace_existing=True,
        #     days=1,
        #     next_run_time=datetime.now() + timedelta(seconds=10),
        # )
        # logger.info(f"注册定时任务: intellectual_fluctuation_task")

        # 每5分钟执行一次示例任务

        # self._scheduler.add_job(
        #     sample_task,
        #     trigger="interval",
        #     id="sample_task",
        #     replace_existing=True,
        #     seconds=5,  # 每5秒执行一次示例任务
        # )

        # logger.info(f"注册定时任务: sample_task")


# 创建定时任务管理器实例
scheduler_manager = SchedulerManager()

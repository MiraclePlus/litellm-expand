from typing import Any, Callable, Dict, List, Optional

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI


from app.core.config import settings
from app.logger import logger

class SchedulerManager:
    """定时任务管理器"""

    def __init__(self) -> None:
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._jobs: List[Dict[str, Any]] = []

    def init_scheduler(self, app: FastAPI) -> None:
        """
        初始化调度器
        
        Args:
            app: FastAPI应用实例
        """
        # 配置作业存储
        jobstores = {
            "default": SQLAlchemyJobStore(url=str(settings.SQLALCHEMY_DATABASE_URI))
        }
        
        # 配置执行器
        executors = {
            "default": ThreadPoolExecutor(20)
        }
        
        # 创建调度器
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone="Asia/Shanghai"
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
    
    def add_job(
        self,
        func: Callable,
        job_id: str,
        trigger: str = "interval",
        **trigger_args: Any
    ) -> None:
        """
        添加定时任务到注册列表
        
        Args:
            func: 要执行的函数
            job_id: 任务ID
            trigger: 触发器类型，可以是'date', 'interval', 或 'cron'
            trigger_args: 触发器参数
        """
        self._jobs.append({
            "func": func,
            "id": job_id,
            "trigger": trigger,
            "trigger_args": trigger_args
        })
    
    def _register_jobs(self) -> None:
        """注册所有预定义的任务"""
        if not self._scheduler:
            logger.error("调度器尚未初始化")
            return
            
        for job in self._jobs:
            trigger_cls = self._get_trigger(job["trigger"], job["trigger_args"])
            self._scheduler.add_job(
                job["func"],
                trigger=trigger_cls,
                id=job["id"],
                replace_existing=True
            )
            logger.info(f"注册定时任务: {job['id']}")
    
    def _get_trigger(self, trigger_type: str, trigger_args: Dict[str, Any]) -> Any:
        """
        获取触发器对象
        
        Args:
            trigger_type: 触发器类型
            trigger_args: 触发器参数
            
        Returns:
            触发器对象
        """
        if trigger_type == "date":
            return DateTrigger(**trigger_args)
        elif trigger_type == "interval":
            return IntervalTrigger(**trigger_args)
        elif trigger_type == "cron":
            return CronTrigger(**trigger_args)
        else:
            raise ValueError(f"不支持的触发器类型: {trigger_type}")


# 创建定时任务管理器实例
scheduler_manager = SchedulerManager() 
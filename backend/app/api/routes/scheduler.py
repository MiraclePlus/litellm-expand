from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_superuser
from app.models import User

router = APIRouter(
    prefix="/scheduler",
    tags=["scheduler"],
    dependencies=[Depends(get_current_active_superuser)],
)


class JobInfo(BaseModel):
    """任务信息模型"""
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    next_run_time: Optional[str] = Field(None, description="下次执行时间")
    trigger: str = Field(..., description="触发器类型")
    trigger_args: Dict = Field(..., description="触发器参数")


@router.get(
    "/jobs", 
    response_model=List[JobInfo], 
    summary="获取所有定时任务",
    description="获取系统中所有注册的定时任务信息"
)
def get_all_jobs(request: Request, _: User = Depends(get_current_active_superuser)) -> List[Dict]:
    """
    获取所有定时任务信息
    
    Args:
        request: 请求对象
        _: 当前超级管理员用户
        
    Returns:
        任务信息列表
    """
    scheduler = request.app.state.scheduler
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="调度器未启动"
        )
    
    job_list = []
    for job in scheduler.get_jobs():
        trigger_args = {}
        
        # 获取触发器参数
        if hasattr(job.trigger, 'interval'):
            trigger_type = 'interval'
            trigger_args = {'seconds': job.trigger.interval.total_seconds()}
        elif hasattr(job.trigger, 'fields'):
            trigger_type = 'cron'
            for field in job.trigger.fields:
                if field.name != 'expression':
                    trigger_args[field.name] = str(field)
        else:
            trigger_type = 'date'
        
        # 格式化下次执行时间
        next_run_time = None
        if job.next_run_time:
            next_run_time = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        
        job_list.append({
            "id": job.id,
            "name": job.id,  # 使用ID作为名称
            "next_run_time": next_run_time,
            "trigger": trigger_type,
            "trigger_args": trigger_args
        })
    
    return job_list


@router.post(
    "/jobs/{job_id}/pause", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="暂停定时任务",
    description="根据任务ID暂停指定的定时任务"
)
def pause_job(
    job_id: str, 
    request: Request, 
    _: User = Depends(get_current_active_superuser)
) -> None:
    """
    暂停定时任务
    
    Args:
        job_id: 任务ID
        request: 请求对象
        _: 当前超级管理员用户
    """
    scheduler = request.app.state.scheduler
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="调度器未启动"
        )
    
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {job_id} 的任务"
        )
    
    scheduler.pause_job(job_id)


@router.post(
    "/jobs/{job_id}/resume", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="恢复定时任务",
    description="根据任务ID恢复指定的定时任务"
)
def resume_job(
    job_id: str, 
    request: Request, 
    _: User = Depends(get_current_active_superuser)
) -> None:
    """
    恢复定时任务
    
    Args:
        job_id: 任务ID
        request: 请求对象
        _: 当前超级管理员用户
    """
    scheduler = request.app.state.scheduler
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="调度器未启动"
        )
    
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {job_id} 的任务"
        )
    
    scheduler.resume_job(job_id) 
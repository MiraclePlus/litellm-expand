from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import SessionDep
from app.models import IdentityEval, IdentityEvalPublic, IdentityEvalsPublic

router = APIRouter(tags=["identity_eval"], prefix="/identity-eval")


@router.get("/", response_model=IdentityEvalsPublic)
def get_identity_evals(
    *,
    session: SessionDep,
    start_date: date = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: date = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ai_model_id: Optional[str] = None,
    dataset_name: Optional[str] = None,
    dataset_key: Optional[str] = None,
    subset: Optional[str] = None,
    metric: Optional[str] = None,
) -> IdentityEvalsPublic:
    """
    获取身份评估数据，支持按日期范围和其他字段过滤
    """
    # 构建查询
    query = select(IdentityEval)
    
    # 应用日期过滤条件
    if start_date:
        query = query.where(IdentityEval.date >= start_date)
    if end_date:
        query = query.where(IdentityEval.date <= end_date)
    
    # 应用其他过滤条件
    if ai_model_id:
        query = query.where(IdentityEval.ai_model_id == ai_model_id)
    if dataset_name:
        query = query.where(IdentityEval.dataset_name == dataset_name)
    if dataset_key:
        query = query.where(IdentityEval.dataset_key == dataset_key)
    if subset:
        query = query.where(IdentityEval.subset == subset)
    if metric:
        query = query.where(IdentityEval.metric == metric)
    
    # 按日期排序
    query = query.order_by(IdentityEval.date)
    
    # 执行查询
    results = session.exec(query).all()
    
    return IdentityEvalsPublic(data=results, count=len(results))


@router.get("/chart-data", response_model=Dict[str, List[Dict[str, Any]]])
def get_chart_data(
    *,
    session: SessionDep,
    start_date: date = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: date = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    dataset_name: Optional[str] = None,
    dataset_key: Optional[str] = None,
    subset: Optional[str] = None,
    metric: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取用于图表展示的数据，按ai_model_id分组
    """
    # 构建查询
    query = select(IdentityEval)
    
    # 应用日期过滤条件
    if start_date:
        query = query.where(IdentityEval.date >= start_date)
    if end_date:
        query = query.where(IdentityEval.date <= end_date)
    
    # 应用其他过滤条件
    if dataset_name:
        query = query.where(IdentityEval.dataset_name == dataset_name)
    if dataset_key:
        query = query.where(IdentityEval.dataset_key == dataset_key)
    if subset:
        query = query.where(IdentityEval.subset == subset)
    if metric:
        query = query.where(IdentityEval.metric == metric)
    
    # 按日期排序
    query = query.order_by(IdentityEval.date)
    
    # 执行查询
    results = session.exec(query).all()
    
    # 按ai_model_id分组数据
    grouped_data = {}
    for result in results:
        model_id = result.ai_model_id
        if model_id not in grouped_data:
            grouped_data[model_id] = []
        
        grouped_data[model_id].append({
            "date": result.date.isoformat(),
            "dataset_name": result.dataset_name,
            "dataset_key": result.dataset_key,
            "subset": result.subset,
            "metric": result.metric,
            "score": result.score,
            "num": result.num
        })
    
    return grouped_data 
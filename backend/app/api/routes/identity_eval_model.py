from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
import requests
from sqlmodel import Session, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import IdentityEvalModel, User
from app.core.config import settings
router = APIRouter(tags=["identity_eval_model"], prefix="/identity-eval-model")


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_model(
    *,
    session: SessionDep,
    model: IdentityEvalModel,
    _: User = Depends(get_current_active_superuser)
) -> IdentityEvalModel:
    """
    创建新的模型记录
    """
    # 检查模型ID是否已存在
    existing_model = session.exec(
        select(IdentityEvalModel).where(IdentityEvalModel.ai_model_id == model.ai_model_id)
    ).first()
    if existing_model:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"模型 {model.ai_model_id} 已存在"
        )
    
    # 创建新记录
    session.add(model)
    session.commit()
    session.refresh(model)
    return model

API_URL = settings.LITE_API_URL
API_KEY = "sk-ZY_wnuzes5znMQV31EXRlw"

@router.get("/", response_model=List[IdentityEvalModel])
def get_all_models(
    *,
    session: SessionDep
) -> List[IdentityEvalModel]:
    """
    获取所有模型记录
    """
    models = session.exec(select(IdentityEvalModel)).all()
    
    # 向https://llm-proxy.miracleplus.com/models 发送请求，获取所有模型
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(f"{API_URL}/models", headers=headers)
    llm_models = response.json()['data']

    # 合并models和llm_models
    for model in llm_models:
        if model['id'] not in [m.ai_model_id for m in models]:
            models.append(IdentityEvalModel(ai_model_id=model['id'], dataset_keys=[]))

    return models


@router.get("/{ai_model_id}", response_model=IdentityEvalModel)
def get_model(
    *,
    session: SessionDep,
    ai_model_id: str
) -> IdentityEvalModel:
    """
    获取指定ID的模型记录
    """
    model = session.exec(
        select(IdentityEvalModel).where(IdentityEvalModel.ai_model_id == ai_model_id)
    ).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型 {ai_model_id} 不存在"
        )
    return model


@router.put("/{ai_model_id}", response_model=IdentityEvalModel)
def update_model(
    *,
    session: SessionDep,
    ai_model_id: str,
    model_update: IdentityEvalModel,
    _: User = Depends(get_current_active_superuser)
) -> IdentityEvalModel:
    """
    更新模型记录
    """
    # 查找现有模型
    db_model = session.exec(
        select(IdentityEvalModel).where(IdentityEvalModel.ai_model_id == ai_model_id)
    ).first()
    if not db_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型 {ai_model_id} 不存在"
        )
    
    # 确保模型ID不变
    if model_update.ai_model_id != ai_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改模型ID"
        )
    
    # 更新数据
    db_model.dataset_keys = model_update.dataset_keys
    db_model.updated_at = model_update.updated_at
    
    session.add(db_model)
    session.commit()
    session.refresh(db_model)
    
    return db_model


@router.delete("/{ai_model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    *,
    session: SessionDep,
    ai_model_id: str,
    _: User = Depends(get_current_active_superuser)
) -> None:
    """
    删除模型记录
    """
    # 查找现有模型
    db_model = session.exec(
        select(IdentityEvalModel).where(IdentityEvalModel.ai_model_id == ai_model_id)
    ).first()
    if not db_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型 {ai_model_id} 不存在"
        )
    
    # 删除模型
    session.delete(db_model)
    session.commit()


@router.patch("/{ai_model_id}/dataset-keys", response_model=IdentityEvalModel)
def update_dataset_keys(
    *,
    session: SessionDep,
    ai_model_id: str,
    dataset_keys: List[str],
    _: User = Depends(get_current_active_superuser)
) -> IdentityEvalModel:
    """
    更新模型的数据集键列表
    """
    # 查找现有模型
    db_model = session.exec(
        select(IdentityEvalModel).where(IdentityEvalModel.ai_model_id == ai_model_id)
    ).first()
    if not db_model:
        # 模型不存在，则创建一个新模型
        db_model = IdentityEvalModel(ai_model_id=ai_model_id, dataset_keys=dataset_keys)
        session.add(db_model)
    else:
        # 更新数据集键
        db_model.dataset_keys = dataset_keys
    
    session.commit()
    session.refresh(db_model)
    
    return db_model 
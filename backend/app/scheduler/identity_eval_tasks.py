import asyncio
from dataclasses import dataclass
import random
from datetime import datetime, date
from typing import Optional, Dict, Union
import functools

from sqlmodel import Session, select
from app.core.db import engine
from app.logger import logger
from app.models import IdentityEval

@dataclass
class EvalDataset:
    dataset_name: str
    dataset_args: Optional[Dict[str, Union[str, dict]]] = None
    dataset_limit: int = 25
    eval_concurrency: int = 16
    eval_cache: str = f"evalscope/{date.today()}"


USED_DATASET = {
    "AIME24": EvalDataset("aime24", {"aime24": {"few_shot_num": 3}}),
    "AIME25": EvalDataset("aime25", {"aime25": {"few_shot_num": 3}}),
    "GPQA_DIAMOND": EvalDataset(
        "gpqa",
        {"gpqa": {"subset_list": ["gpqa_diamond"], "few_shot_num": 3}},
    ),
    "MMLU_PRO_LAW": EvalDataset(
        "mmlu_pro", {"mmlu_pro": {"subset_list": ["law"], "few_shot_num": 3}}
    ),
    "MMLU_PRO_BUSINESS": EvalDataset(
        "mmlu_pro", {"mmlu_pro": {"subset_list": ["business"], "few_shot_num": 3}}
    ),
    "MMLU_PRO_PHILOSOPHY": EvalDataset(
        "mmlu_pro", {"mmlu_pro": {"subset_list": ["philosophy"], "few_shot_num": 3}}
    ),
    "LIVE_CODE_BENCH": EvalDataset(
        "live_code_bench",
        {
            "live_code_bench": {
                "subset_list": ["release_latest"],
                "extra_params": {
                    "start_date": "2024-11-28",
                    "end_date": "2025-01-01",
                },
                "filters": {"remove_until": "</think>"},
                "few_shot_num": 3,
            }
        },
    ),
}

CACHE_PATH = "evalscope/"
TEMPERATURE = 0.0

async def _identity_eval_task_impl() -> None:
    """
    Identity评估数据生成任务的实际异步实现
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Identity评估数据生成任务执行时间: {current_time}")

    await asyncio.sleep(1)  # 模拟异步操作

    # 准备随机数据
    models = [
        {"model_id": "gpt-4.1-azure", "dataset_keys": ["AIME25"]},
        {"model_id": "gpt-4.1-mini", "dataset_keys": ["AIME25"]},
        {
            "model_id": "pinefield.us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "dataset_keys": [
                "AIME24",
                "AIME25",
                "GPQA_DIAMOND",
                "MMLU_PRO_LAW",
                "MMLU_PRO_BUSINESS",
                "MMLU_PRO_PHILOSOPHY",
                "LIVE_CODE_BENCH",
            ],
        },
        {
            "model_id": "grok-3-mini-beta-jiang",
            "dataset_keys": [
                "AIME24",
                "AIME25",
                "GPQA_DIAMOND",
                "MMLU_PRO_LAW",
                "MMLU_PRO_BUSINESS",
                "MMLU_PRO_PHILOSOPHY",
                "LIVE_CODE_BENCH",
            ],
        },
        {
            "model_id": "pinefield.us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "dataset_keys": [
                "AIME24",
                "AIME25",
                "GPQA_DIAMOND",
                "MMLU_PRO_LAW",
                "MMLU_PRO_BUSINESS",
                "MMLU_PRO_PHILOSOPHY",
                "LIVE_CODE_BENCH",
            ],
        },
        {
            "model_id": "o4-mini-jiang",
            "dataset_keys": [
                "AIME24",
                "AIME25",
                "GPQA_DIAMOND",
                "MMLU_PRO_LAW",
                "MMLU_PRO_BUSINESS",
                "MMLU_PRO_PHILOSOPHY",
                "LIVE_CODE_BENCH",
            ],
        },
    ]

    try:
        # 创建数据库会话
        with Session(engine) as session:
            # 随机选择数据
            model_config = random.choice(models)
            dataset = random.choice(model_config["dataset_keys"])
            today = date.today()
            dataset_key = dataset
            subset = dataset
            num = random.randint(100, 1000)
            
            # 获取数据集配置
            if dataset_key in USED_DATASET:
                dataset_args = USED_DATASET[dataset_key].dataset_args
                dataset_limit = USED_DATASET[dataset_key].dataset_limit
                eval_concurrency = USED_DATASET[dataset_key].eval_concurrency
                eval_cache = USED_DATASET[dataset_key].eval_cache
            
            # 随机生成一个评估分数
            score = round(random.uniform(0.7, 0.99), 2)
            
            # 创建新记录
            new_eval = IdentityEval(
                ai_model_id=model_config["model_id"],
                dataset_name=dataset_key,
                metric="accuracy",
                score=score,
                date=today,
                dataset_key=dataset_key,
                subset=dataset_key,
                num=num,
                updated_at="CURRENT_TIMESTAMP",
            )

            # 检查是否已存在相同记录(ai_model_id + dataset_name + date组合唯一)
            existing = session.exec(
                select(IdentityEval).where(
                    IdentityEval.ai_model_id == model_config["model_id"],
                    IdentityEval.dataset_name == dataset_key,
                    IdentityEval.date == today,
                )
            ).first()

            if existing:
                # 更新现有记录
                existing.score = score
                existing.metric = "accuracy"
                existing.dataset_key = dataset_key
                existing.subset = subset
                existing.num = num
                existing.updated_at = "CURRENT_TIMESTAMP"
                session.add(existing)
                logger.info(f"更新IdentityEval记录: {model_config['model_id']}/{dataset_key}")
            else:
                # 添加新记录
                session.add(new_eval)
                logger.info(f"添加新IdentityEval记录: {model_config['model_id']}/{dataset_key}")

            # 提交事务
            session.commit()

    except Exception as e:
        logger.error(f"Identity评估数据生成任务异常: {str(e)}")


def identity_eval_task():
    """
    Identity评估数据生成任务的非异步包装器
    
    APScheduler在处理异步函数时可能会有问题，因此我们使用这个包装函数
    来确保异步函数被正确执行。
    """
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    try:
        # 在该循环中运行异步任务
        loop.run_until_complete(_identity_eval_task_impl())
    finally:
        # 关闭循环
        loop.close()

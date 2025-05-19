from dataclasses import dataclass
from json import dumps
from datetime import date
from typing import Optional, Dict, Union
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.scheduler.intellectual_fluctuation_task import intellectual_fluctuation_task
from requests import RequestException
import requests
from sqlalchemy import func
from sqlmodel import Session, select
from app.core.db import engine
from app.logger import logger
from app.models import IdentityEval, IdentityEvalModel
from evalscope import TaskConfig, run_task
from evalscope.constants import EvalType


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

API_URL = "https://llm-proxy.miracleplus.com/v1" if settings.ENVIRONMENT == "local" else "http://10.128.32.124/v1"
API_KEY = "sk-ZY_wnuzes5znMQV31EXRlw"
    

def _identity_eval_task_impl(
    model_name: str,
    datasets: dict[str, EvalDataset],
) -> None:
    """
    Identity评估数据生成任务的实际异步实现
    """
    for dataset_key, dataset in datasets.items():
        logger.info(f"开始基准测试模型: {model_name}，数据集: {dataset_key}")
        try:
            task_config = TaskConfig(
                model=model_name,
                datasets=[dataset.dataset_name],
                dataset_args=dataset.dataset_args,
                eval_type=EvalType.SERVICE,
                api_url=API_URL,
                api_key=API_KEY,
                timeout=3600,
                eval_batch_size=dataset.eval_concurrency,
                limit=dataset.dataset_limit,
                generation_config={"temperature": TEMPERATURE, "do_sample": True},
                dataset_dir=CACHE_PATH,
                judge_worker_num=1,  # > 1 could run into deadlock
                use_cache=f"evalscope/{date.today()}",
            )

            # report = run_task(task_config)
            # report = report[dataset.dataset_name]
            report = None

            # 创建数据库会话
            with Session(engine) as session:
                # 创建新记录
                new_eval = IdentityEval(
                    ai_model_id=model_name,
                    dataset_key=dataset_key,
                    dataset_name=dataset.dataset_name,
                    date=date.today(),
                )

                if report is not None:
                    new_eval.score = report.metrics[0].score
                    new_eval.metric = report.metrics[0].name
                    new_eval.subset = ",".join(report.metrics[0].categories[0].name)
                    new_eval.num = report.metrics[0].num
                else:
                    new_eval.score = -1
                    new_eval.metric = ""
                    new_eval.subset = ""
                    new_eval.num = 0

                # 检查是否已存在相同记录(ai_model_id + dataset_key + date组合唯一)
                existing = session.exec(
                    select(IdentityEval).where(
                        IdentityEval.ai_model_id == model_name,
                        IdentityEval.dataset_key == dataset_key,
                        IdentityEval.date == date.today(),
                    )
                ).first()

                if existing:
                    # 更新现有记录
                    existing.score = new_eval.score
                    existing.metric = new_eval.metric
                    existing.dataset_key = dataset_key
                    existing.subset = new_eval.subset
                    existing.num = new_eval.num
                    session.add(existing)
                    logger.info(f"更新IdentityEval记录: {model_name}/{dataset_key}")
                else:
                    # 添加新记录
                    session.add(new_eval)
                    logger.info(f"添加新IdentityEval记录: {model_name}/{dataset_key}")
                # 提交事务
                session.commit()

        except Exception as e:
            logger.error(f"{model_name}/{dataset_key} 基准测试任务异常: {str(e)}")
            _send_message_to_feishu(
                f"Error running task for [{model_name}] on [{dataset_key}]: {e}"
            )


def _send_message_to_feishu(param):
    # Send a message to Feishu
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "msg_type": "text",
        "content": {
            "text": param,
        },
    }
    try:
        webhook_url = (
            "https://open.feishu.cn/open-apis/bot/v2/hook/52d1469f-1fed-40ee-aa7b-39df5159c945"
            if settings.ENVIRONMENT != "local"
            else "https://open.feishu.cn/open-apis/bot/v2/hook/3fb5fbbe-37c0-4788-b6d4-5333f5c0a4d6"
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")


def identity_eval_task():
    """
    使用多线程同时运行多个_identity_eval_task_impl实例
    """
    # 设置线程数量
    num_threads = 5

    # 准备数据
    models = []
    # 创建数据库会话
    with Session(engine) as session:
        models = session.exec(select(IdentityEvalModel.ai_model_id, IdentityEvalModel.dataset_keys).where(func.cardinality(IdentityEvalModel.dataset_keys) > 0)).all()

    logger.info(
        f"启动Identity评估数据生成任务，线程数：{num_threads}, 模型：{','.join(map(lambda x: x.ai_model_id, models))}"
    )

    # 使用线程池执行多个任务实例
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # 提交num_threads个任务
        futures = []

        for model in models:
            dataset_keys = model.dataset_keys
            # 过滤出models中'dataset_keys'长度大于0的模型
            if len(dataset_keys) > 0:
                model_name = model.ai_model_id
                # 过滤出dataset_keys中存在的USED_DATASET中的数据集
                datasets = {}
                for dataset_key in dataset_keys:
                    if dataset_key in USED_DATASET:
                        datasets[dataset_key] = USED_DATASET[dataset_key]
                futures.append(
                    executor.submit(_identity_eval_task_impl, model_name, datasets)
                )

        if not futures:
            logger.info("没有可用的模型或数据集，跳过基准测试")
            return

        # 等待所有任务完成
        for future in futures:
            try:
                future.result()  # 获取结果，如果有异常会在这里抛出
            except Exception as e:
                logger.error(f"Identity评估任务线程异常: {str(e)}")

    logger.info(f"所有Identity评估数据生成任务已完成")

    # 立即执行 intellectual_fluctuation_task
    intellectual_fluctuation_task(models)

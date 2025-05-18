from dataclasses import dataclass
from json import dumps
import random
from datetime import date
from typing import Optional, Dict, Union
from concurrent.futures import ThreadPoolExecutor

from requests import RequestException
import requests
from sqlmodel import Session, select
from app.core.db import engine
from app.logger import logger
from app.models import IdentityEval
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
                api_url="https://llm-proxy.miracleplus.com//v1",
                api_key="sk-ZY_wnuzes5znMQV31EXRlw",
                timeout=3600,
                eval_batch_size=dataset.eval_concurrency,
                limit=dataset.dataset_limit,
                generation_config={"temperature": TEMPERATURE, "do_sample": True},
                dataset_dir=CACHE_PATH,
                judge_worker_num=1,  # > 1 could run into deadlock
                use_cache=f"evalscope/{date.today()}",
            )

            report = run_task(task_config)
            report = report[dataset.dataset_name]

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
                    existing.score = report.metrics[0].score
                    existing.metric = report.metrics[0].name
                    existing.dataset_key = dataset_key
                    existing.subset = ",".join(report.metrics[0].categories[0].name)
                    existing.num = report.metrics[0].num
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
                f"Error running task for [{model_name}] on [{dataset_key}]: {e}",
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/52d1469f-1fed-40ee-aa7b-39df5159c945",
            )

def _send_message_to_feishu(param, webhook_url):
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
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except RequestException as e:
        print(f"Error sending message to Feishu: {e}")


def identity_eval_task():
    """
    使用多线程同时运行多个_identity_eval_task_impl实例
    """
    # 设置线程数量
    num_threads = 5

    # 准备数据
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

    logger.info(
        f"启动Identity评估数据生成任务，线程数：{num_threads}, 模型数：{len(models)}"
    )

    # 使用线程池执行多个任务实例
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # 提交num_threads个任务
        futures = [
            executor.submit(_identity_eval_task_impl) for _ in range(num_threads)
        ]

        # 等待所有任务完成
        for future in futures:
            try:
                future.result()  # 获取结果，如果有异常会在这里抛出
            except Exception as e:
                logger.error(f"Identity评估任务线程异常: {str(e)}")

    logger.info(f"所有Identity评估数据生成任务已完成")

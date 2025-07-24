from datetime import datetime, timedelta, date
from json import dumps
from app.core.config import settings
from app.logger import logger
from app.models import IdentityEval, IdentityEvalModel
import requests
from sqlalchemy import func
from sqlmodel import Session, select
from app.core.db import engine


def intellectual_fluctuation_task(models: list[IdentityEvalModel] | None = None):
    # 准备数据
    if models is None:
        # 创建数据库会话
        with Session(engine) as session:
            models = session.exec(select(IdentityEvalModel.ai_model_id, IdentityEvalModel.dataset_keys).where(func.cardinality(IdentityEvalModel.dataset_keys) > 0)).all()

    logger.info(f"启动智力波动任务，模型：{','.join(map(lambda x: x.ai_model_id, models))}")

    # 记录差异的模型数据集分数，等所有计算完成后统计一发送飞书消息
    diff: dict[str, int | None] = {}

    with Session(engine) as session:
        # 获取模型评测分数
        for model in models:
            model_id = model.ai_model_id
            dataset_keys = model.dataset_keys
            for dataset_key in dataset_keys:
                try:
                    # 查询模型今天的分数
                    today_query = select(IdentityEval).where(
                        IdentityEval.ai_model_id == model_id,
                        IdentityEval.dataset_key == dataset_key,
                        IdentityEval.date == date.today(),
                        IdentityEval.score != -1,
                    )
                    today_result = session.exec(today_query).first()

                    # 如果今天没有分数，则跳过
                    if not today_result:
                        diff[f"{model_id}/{dataset_key}"] = None
                        continue

                    # 查询模型与数据集的近三天的分数
                    query = select(IdentityEval).where(
                        IdentityEval.ai_model_id == model_id,
                        IdentityEval.dataset_key == dataset_key,
                        IdentityEval.date >= date.today() - timedelta(days=3),
                        IdentityEval.date < date.today(),
                        IdentityEval.score != -1,
                    )
                    logger.debug(f"查询条件：{query}")
                    three_days_result = session.exec(query).all()
                    # 只有满三天条件的分数才算
                    if len(three_days_result) < 3:
                        diff[f"{model_id}/{dataset_key}"] = None
                        continue
                    # 计算前三天分数的平均值
                    mean_score = sum(r.score for r in three_days_result) / len(
                        three_days_result
                    )
                    # 计算当天分数
                    current_score = today_result.score
                    # 计算分数差异
                    # score_diff = abs(mean_score - current_score)
                    score_diff = round(current_score - mean_score, 2)
                    # 计算差异百分比
                    # diff_percent = score_diff / mean_score * 100
                    diff_percent = score_diff * 100
                    diff[f"{model_id}/{dataset_key}"] = int(diff_percent)
                except Exception as e:
                    logger.error(
                        f"{model_id}/{dataset_key}评测分数基准值差异计算错误", e
                    )

    logger.info(f"智力波动任务完成，差异模型数据集分数：{diff}")
    messages = []
    for key, diff_percent in diff.items():
        if diff_percent is None:
            messages.append(f"⚫️ {key}: 基准值差异计算跳过，数据不足")
        elif diff_percent >= 0 and diff_percent <= 5:  # 上升/不变绿色
            messages.append(f"🟢 {key}: {diff_percent}%")
        elif diff_percent <= 0 and diff_percent > -5:  # 下降黄色
            messages.append(f"🟡 {key}: {diff_percent}%")
        else:  # 超5%红色
            messages.append(f"🔴 {key}: {diff_percent}%")
            
    _send_message_to_feishu("\r\n".join(messages))

def _send_message_to_feishu(message):
    # Send a message to Feishu
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "msg_type": "text",
        "content": {
            "text": f"评测分数基准值差异: \r\n{message}",
        },
    }
    try:
        webhook_url = (
            settings.EVALUATION_FEISHU_WEBHOOK_URL
            if settings.ENVIRONMENT != "local"
            else "https://open.feishu.cn/open-apis/bot/v2/hook/3fb5fbbe-37c0-4788-b6d4-5333f5c0a4d6"  # 使用配置中的Webhook URL
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")

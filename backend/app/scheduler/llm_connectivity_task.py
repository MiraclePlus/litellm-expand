
from json import dumps
from app.core.config import settings
from app.logger import logger
from app.models import IdentityEvalModel
import requests
from sqlalchemy import func
from sqlmodel import Session, select
from app.core.db import engine

API_URL = "https://llm-proxy.miracleplus.com/v1"
API_KEY = "sk-GC6dxzp_Ci4sECy8kJDtQQ"

def llm_connectivity_task():
    # 准备数据
    models = []

    # 创建数据库会话
    with Session(engine) as session:
        models = session.exec(select(IdentityEvalModel.ai_model_id).where(func.cardinality(IdentityEvalModel.dataset_keys) > 0)).all()

    # 失败的模型
    failed_models = []

    for model_id in models:
        logger.info(f"开始检测模型连通性: {model_id}")
        try:
            response = requests.post(
                f"{API_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                },
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("choices") and response_data["choices"][0].get("message", {}).get("content"):
                    logger.info(f"✅ 模型 {model_id} 连通性检测成功")
                    continue
                
            error_message = response.content.decode('utf-8') if response.content else response.status_code
            failed_models.append(f"❌ 模型 {model_id} 连通性检测失败: {error_message}")
            logger.error(f"❌ 模型 {model_id} 连通性检测失败:  {error_message}")
        except Exception as e:
            logger.error(f"❌ 模型 {model_id} 连通性检测失败:  {e}")
            failed_models.append(f"❌ 模型 {model_id} 连通性检测失败:  {e}")

    if failed_models:
        _send_message_to_feishu("\r\n".join(failed_models))

def _send_message_to_feishu(message):
    # Send a message to Feishu
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "msg_type": "text",
        "content": {
            "text": f"检测模型连通性: \r\n{message}",
        },
    }
    try:
        webhook_url = (
            "https://open.feishu.cn/open-apis/bot/v2/hook/52d1469f-1fed-40ee-aa7b-39df5159c945"
            if settings.ENVIRONMENT != "local"
            else settings.CONNECTIVITY_TEST_FEISHU_WEBHOOK_URL  # 使用配置中的Webhook URL
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")
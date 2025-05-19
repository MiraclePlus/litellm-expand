
from json import dumps
from app.core.config import settings
from app.logger import logger
import requests

API_URL = "https://llm-proxy.miracleplus.com/v1" if settings.ENVIRONMENT == "local" else "http://host.docker.internal:8000/v1"
API_KEY = "sk-GC6dxzp_Ci4sECy8kJDtQQ"

def llm_connectivity_task():
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

    # 失败的模型
    failed_models = []

    for model in models:
        model_id = model["model_id"]
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
            else "https://open.feishu.cn/open-apis/bot/v2/hook/3fb5fbbe-37c0-4788-b6d4-5333f5c0a4d6"
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")
from app.logger import logger
from app.core.db import llm_engine
from sqlmodel import Session, text
from app.core.config import settings
from requests import RequestException
import requests
from json import dumps


def user_over_quota_alert_task():
    logger.info("user_over_quota_alert_task")

    # 创建数据库会话
    with Session(llm_engine) as session:
        # 执行SQL查询，查找预算使用率超过90%的用户

        result = session.exec(text(f"""
            SELECT * FROM "LiteLLM_UserTable" 
            WHERE max_budget > 0 AND spend / max_budget >= {settings.USAGE_RATE / 100}
        """)).all()
        
        messages = []
        for row in result:
            logger.info(f"用户 {row.user_email} 预算使用率超过{settings.USAGE_RATE}%: 预算: {row.max_budget}, 已花费: {row.spend}")
            messages.append(f"🔴用户 {row.user_email} 预算使用率超过{settings.USAGE_RATE}%: 预算: {row.max_budget}, 已花费: {row.spend}")

        if messages:      
            _send_message_to_feishu(f"用户预算使用预警: \r\n{'\r\n'.join(messages)}")


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
            else settings.USAGE_FEISHU_WEBHOOK_URL
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")

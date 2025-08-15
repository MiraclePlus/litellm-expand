import enum
from json import dumps
from typing import Literal, Optional
from fastapi import APIRouter, Request, logger
import requests
from sqlmodel import Field
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/webhook", tags=["webhook"])


class Litellm_EntityType(enum.Enum):
    """
    Enum for types of entities on litellm

    This enum allows specifying the type of entity that is being tracked in the database.
    """

    KEY = "key"
    USER = "user"
    END_USER = "end_user"
    TEAM = "team"
    TEAM_MEMBER = "team_member"
    ORGANIZATION = "organization"

    # global proxy level entity
    PROXY = "proxy"


class CallInfo(BaseModel):
    """Used for slack budget alerting"""

    spend: float
    max_budget: Optional[float] = None
    soft_budget: Optional[float] = None
    token: Optional[str] = Field(default=None, description="Hashed value of that key")
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    team_alias: Optional[str] = None
    user_email: Optional[str] = None
    key_alias: Optional[str] = None
    projected_exceeded_date: Optional[str] = None
    projected_spend: Optional[float] = None
    event_group: Litellm_EntityType


class WebhookEvent(CallInfo):
    event: Literal[
        "budget_crossed",
        "soft_budget_crossed",
        "threshold_crossed",
        "projected_limit_exceeded",
        "key_created",
        "internal_user_created",
        "spend_tracked",
    ]
    event_message: str  # human-readable description of event
    event_group: Litellm_EntityType


@router.post("/alerting")
def alerting(event: WebhookEvent):

    messages = []
    match event.event:
        # 支出已超过预算上限。
        case "budget_crossed":
            messages.append(f"🔴 {event.event_group.value}的支出已超过预算上限.")
        # 支出已超过阈值（当前在达到预算的 85% 和 95% 时发送）
        case "threshold_crossed":
            messages.append(f"🔴 {event.event_group.value}的支出已超过阈值.")
        case _:
            return {"message": "skip"}

    max_budget = event.max_budget
    if max_budget:
        messages.append(f"最大预算: {max_budget}")

    key_id = event.token
    if key_id:
        messages.append(f"KeyID: {key_id}")

    key_alias = event.key_alias
    if key_alias:
        messages.append(f"Key别名: {key_alias}")

    customer_id = event.customer_id
    if customer_id:
        messages.append(f"客户ID: {customer_id}")

    user_id = event.user_id
    if user_id:
        messages.append(f"用户ID: {user_id}")

    user_email = event.user_email
    if user_email:
        messages.append(f"用户邮箱: {user_email}")

    team_id = event.team_id
    if team_id:
        messages.append(f"团队ID: {team_id}")

    team_alias = event.team_alias
    if team_alias:
        messages.append(f"团队别名: {team_alias}")

    event_message = event.event_message
    if event_message:
        messages.append(f"预警信息: {event_message}".replace("\n", ""))

    if messages:
        _send_message_to_feishu("\n".join(messages))

    return {"message": "ok"}


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
            settings.USAGE_FEISHU_WEBHOOK_URL
            if settings.ENVIRONMENT != "local"
            else "https://open.feishu.cn/open-apis/bot/v2/hook/3fb5fbbe-37c0-4788-b6d4-5333f5c0a4d6"
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")

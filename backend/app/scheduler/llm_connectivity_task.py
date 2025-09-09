import base64
import hashlib
from json import dumps

import nacl.secret
import nacl.utils
import requests

from app.core.config import settings
from app.logger import logger


def llm_connectivity_task():
    models = ["gpt-5", "o4-mini", "claude-sonnet-4-20250514", "gala-claude-sonnet-4-20250514", "gemini-2.5-pro"]
    message = ""
    for model in models:
        response = requests.get(
            f"{settings.LITE_API_URL}/health?model={model}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.LITE_API_KEY}",
            },
        )

        if response.status_code == 200:
            logger.info(f"litellm 健康检查请求成功")
            response_data = response.json()

            unhealthy_endpoints = response_data.get("unhealthy_endpoints")
            if unhealthy_endpoints:

                for endpoint in unhealthy_endpoints:
                    model_name = endpoint.get('model')
                    if model_name.startswith("o3-deep-research"):
                        continue
                    service = "unknown"
                    if endpoint.get("litellm_credential_name"):
                        service = endpoint["litellm_credential_name"]
                    elif endpoint.get("api_base"):
                        api_base = endpoint.get("api_base")
                        if api_base.startswith("https://aigc.x-see.cn/v1"):
                            service = "xiaojingai"
                        elif api_base.startswith("https://www.furion-tech.com/v1"):
                            service = "jiang"
                        else:
                            service = api_base

                    error_message = endpoint.get('error')
                    # 移除stack trace:之后的内容
                    if error_message:
                        error_message = error_message.split("stack trace:")[0]
                    message += f"❌ 模型: [{endpoint.get('model')}], 服务商: [{service}], 连通性检测失败: {error_message}\r\n"

            else:
                logger.info(f"litellm 健康检查通过")
        else:
            logger.error(f"litellm 健康检查请求失败: {response.status_code}")
            message += f"❌ 模型: [{model}], litellm 健康检查请求失败: {response.status_code}\r\n"

    if message:
        _send_message_to_feishu(message)


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
            settings.CONNECTIVITY_TEST_FEISHU_WEBHOOK_URL
            if settings.ENVIRONMENT != "local"
            else "https://open.feishu.cn/open-apis/bot/v2/hook/3fb5fbbe-37c0-4788-b6d4-5333f5c0a4d6"
        )
        response = requests.post(webhook_url, headers=headers, data=dumps(data))
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"发送飞书消息失败: {e}")


def decrypt_value(value: bytes, signing_key: str) -> str:
    value = base64.b64decode(value)
    # get 32 byte master key #
    hash_object = hashlib.sha256(signing_key.encode())
    hash_bytes = hash_object.digest()

    # initialize secret box #
    box = nacl.secret.SecretBox(hash_bytes)

    # Convert the bytes object to a string
    plaintext = box.decrypt(value)

    plaintext = plaintext.decode("utf-8")  # type: ignore
    return plaintext  # type: ignore

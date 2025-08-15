import base64
from json import dumps
import time
from app.core.config import settings
from app.logger import logger
from app.models import IdentityEvalModel
import requests
from sqlalchemy import func
from sqlmodel import Session, select, text
from app.core.db import engine, llm_engine
import hashlib
import nacl.secret
import nacl.utils


def llm_connectivity_task():

    response = requests.get(
        f"{settings.LITE_API_URL}/health",
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
            message = ""

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
                error_message = error_message.split("stack trace:")[0]
                message += f"❌ 模型: [{endpoint.get('model')}], 服务商: [{service}], 连通性检测失败: {error_message}\r\n"

            _send_message_to_feishu(message)

        else:
            logger.info(f"litellm 健康检查通过")
    else:
        logger.error(f"litellm 健康检查请求失败: {response.status_code}")
        _send_message_to_feishu(f"litellm 健康检查请求失败: {response.status_code}")

    return

    # 准备数据
    models = []

    # 创建数据库会话
    with Session(engine) as session:
        models = session.exec(
            select(IdentityEvalModel.ai_model_id).where(
                func.cardinality(IdentityEvalModel.dataset_keys) > 0
            )
        ).all()

    # 失败的模型Map
    failed_models = {}

    logger.info(f"开始检测模型连通性: {models}")

    for model_id in models:
        try:
            response = requests.post(
                f"{settings.LITE_API_URL}/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.LITE_API_KEY}",
                },
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("choices") and response_data["choices"][0].get(
                    "message", {}
                ).get("content"):
                    logger.info(f"✅ 模型 {model_id} 连通性检测成功")
                    continue
            error_message = (
                response.content.decode("utf-8")
                if response.content
                else response.status_code
            )
            # {'date': 'Thu, 24 Jul 2025 06:24:53 GMT', 'server': 'uvicorn', 'x-litellm-call-id': 'c8a1945d-6616-43cd-a10e-d75a30ecf8a5', 'x-litellm-response-cost': '0', 'x-litellm-key-spend': '0.025460325000000002', 'x-litellm-timeout': '7200', 'content-length': '328', 'content-type': 'application/json'}
            logger.error(f"❌ 模型 {model_id} 连通性检测失败:  {error_message}")
            failed_models[model_id] = {
                "message": error_message,
                "call_id": response.headers.get("x-litellm-call-id"),
            }
        except Exception as e:
            logger.error(f"❌ 模型 {model_id} 连通性检测失败:  {e}")
            failed_models[model_id] = {
                "message": e,
            }

    if failed_models:
        # 创建llm数据库会话
        with Session(llm_engine) as session:
            # 执行SQL查询，对应模型的服务商
            for model_id, data in failed_models.items():
                result = _get_litellm_model_by_request_id(session, data["call_id"])

                failed_models[model_id]["service"] = "unknown"

                if result:
                    logger.info(f"获取litellm_params: {result.litellm_params}")
                    # 先检查没有没配置litellm_credential_name
                    litellm_params = result.litellm_params
                    if litellm_params.get("litellm_credential_name"):
                        failed_models[model_id]["service"] = decrypt_value(
                            litellm_params.get("litellm_credential_name"),
                            settings.LITELLM_SALT_KEY,
                        )
                    elif litellm_params.get("api_base"):
                        api_base = decrypt_value(
                            litellm_params.get("api_base"), settings.LITELLM_SALT_KEY
                        )
                        if api_base.startswith("https://aigc.x-see.cn/v1"):
                            failed_models[model_id]["service"] = "xiaojingai"
                        elif api_base.startswith("https://www.furion-tech.com/v1"):
                            failed_models[model_id]["service"] = "jiang"
                        else:
                            failed_models[model_id]["service"] = api_base
                    else:
                        failed_models[model_id]["service"] = "unknown"

        # 格式化failed_models数据
        message = ""
        for model_id, data in failed_models.items():
            message += f"❌ 模型: [{model_id}], 服务商: [{data['service']}], request_id: [{data['call_id']}], 连通性检测失败: {data['message']}\r\n"

        _send_message_to_feishu(message)


def _get_litellm_model_by_request_id(session: Session, request_id: str) -> dict | None:
    for i in range(20):
        result = session.exec(
            text(
                f"""
                SELECT p.litellm_params
                FROM public."LiteLLM_SpendLogs" t inner join public."LiteLLM_ProxyModelTable" p on t.model_id = p.model_id
                WHERE t.request_id = '{request_id}'
            """
            )
        ).first()
        if result:
            return result
        time.sleep(i * 5)
        logger.info(f"重试获取litellm_params: {i}, call_id: {request_id}")
    return None


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

import random
from datetime import datetime, date

from sqlmodel import Session, select
from app.core.db import engine
from app.logger import logger
from app.models import IdentityEval


async def identity_eval_task() -> None:
    """
    Identity评估数据生成任务
    
    定期向IdentityEval表中插入测试数据，用于展示和测试目的
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Identity评估数据生成任务执行时间: {current_time}")
    
    # 准备随机数据
    models = ["gpt-4", "claude-3", "llama-3", "gemini-pro"]
    datasets = ["hellaswag", "mmlu", "truthfulqa", "arena-hard"]
    metrics = ["accuracy", "f1_score", "precision", "recall"]
    dataset_keys = ["key1", "key2", "key3", "key4"]
    subsets = ["subset1", "subset2", "subset3"]
    
    try:
        # 创建数据库会话
        with Session(engine) as session:
            # 随机选择数据
            model = random.choice(models)
            dataset = random.choice(datasets)
            metric = random.choice(metrics)
            score = round(random.uniform(0.7, 0.99), 2)  # 生成0.7到0.99之间的随机分数
            today = date.today()
            dataset_key = random.choice(dataset_keys)
            subset = random.choice(subsets)
            num = random.randint(100, 1000)
            
            # 创建新记录
            new_eval = IdentityEval(
                ai_model_id=model,
                dataset_name=dataset,
                metric=metric,
                score=score,
                date=today,
                dataset_key=dataset_key,
                subset=subset,
                num=num,
                updated_at="CURRENT_TIMESTAMP"
            )
            
            # 检查是否已存在相同记录(ai_model_id + dataset_name + date组合唯一)
            existing = session.exec(
                select(IdentityEval).where(
                    IdentityEval.ai_model_id == model,
                    IdentityEval.dataset_name == dataset,
                    IdentityEval.date == today
                )
            ).first()
            
            if existing:
                # 更新现有记录
                existing.score = score
                existing.metric = metric
                existing.dataset_key = dataset_key
                existing.subset = subset
                existing.num = num
                existing.updated_at = "CURRENT_TIMESTAMP"
                session.add(existing)
                logger.info(f"更新IdentityEval记录: {model}/{dataset}")
            else:
                # 添加新记录
                session.add(new_eval)
                logger.info(f"添加新IdentityEval记录: {model}/{dataset}")
            
            # 提交事务
            session.commit()
            
    except Exception as e:
        logger.error(f"Identity评估数据生成任务异常: {str(e)}") 
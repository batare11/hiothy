"""创建业务表并写入演示消息。

运行前需确保数据库和用户已按 README 中的 SQL 创建，并配置 backend/.env。
"""

import sys
from pathlib import Path

from sqlalchemy import select

# 支持直接执行 `python scripts/init_db.py`。
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base, SessionLocal, engine
from app.models import Message


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        exists = db.scalar(select(Message.id).where(Message.mini_user_id == "demo-user"))
        if not exists:
            db.add_all(
                [
                    Message(
                        mini_user_id="demo-user",
                        title="欢迎使用血压健康助手",
                        content="记录每日血压，持续关注健康趋势。",
                        message_type="system",
                    ),
                    Message(
                        mini_user_id="demo-user",
                        title="测量小贴士",
                        content="测量前静坐 5 分钟，手臂与心脏保持同一高度。",
                        message_type="notice",
                    ),
                ]
            )
            db.commit()
    print("数据库表初始化完成。")


if __name__ == "__main__":
    main()

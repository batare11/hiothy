# Python 后端

技术栈：FastAPI、SQLAlchemy 2、PostgreSQL、RapidOCR。

## 配置

复制 `.env.example` 为 `.env`，将 `CHANGE_ME` 改为真实数据库密码。密码中若含特殊字符，应进行 URL 编码；例如 `@` 写为 `%40`。

```env
DATABASE_URL=postgresql+psycopg://blood_pressure:你的URL编码密码@101.42.90.208:5432/blood_pressure
```

## 安装与运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
python run.py
```

首次 OCR 请求会加载 ONNX 模型，响应时间可能略长。

## API 概览

所有业务请求建议携带：

```text
X-Mini-User-Id: 微信用户 openid 或开发期唯一 ID
```

- `POST /api/v1/ocr/blood-pressure`：识别血压计图片
- `POST /api/v1/blood-pressure`：新增记录
- `GET /api/v1/blood-pressure`：记录列表
- `GET /api/v1/blood-pressure/trend`：趋势分析
- `PUT /api/v1/blood-pressure/{id}`：修改记录
- `DELETE /api/v1/blood-pressure/{id}`：删除记录
- `GET /api/v1/messages?state=unread|read|all`：消息列表
- `PUT /api/v1/messages/{id}/read`：消息已读
- `GET/PUT /api/v1/profile`：个人资料
- `POST /api/v1/feedback`：意见反馈

## 上线前必须完成

1. 使用 Nginx 配置 HTTPS，将 `https://hiothy.cn/api/v1` 代理到 `127.0.0.1:5000/api/v1`。
2. 将开发期 `X-Mini-User-Id` 替换为微信 `wx.login` + 服务端 `code2Session` 登录态，不能信任客户端直接提交的 openid。
3. 用 Alembic 管理生产数据库迁移。
4. 为接口增加访问频率限制、结构化日志和备份策略。
5. 血压判定仅作健康提示，不应替代医生诊断。


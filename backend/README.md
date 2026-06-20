# Python 后端

技术栈：FastAPI、SQLAlchemy 2、PostgreSQL、RapidOCR。

## 配置

复制 `.env.example` 为 `.env`，将 `CHANGE_ME` 改为真实数据库密码。密码中若含特殊字符，应进行 URL 编码；例如 `@` 写为 `%40`。

```env
DATABASE_URL=postgresql+psycopg://blood_pressure:你的URL编码密码@101.42.90.208:5432/blood_pressure
```

服务器本机部署时应使用 PostgreSQL 的本地端口：

```env
DATABASE_URL=postgresql+psycopg://blood_pressure:你的URL编码密码@127.0.0.1:5432/blood_pressure
```

## 微信真实身份登录

开发版、体验版和正式版统一使用 `wx.login` 获取临时 code。后端调用微信
`code2Session` 换取 openid，再签发自己的 Bearer Token。

服务器 `.env` 必须配置：

```env
WECHAT_APP_ID=与小程序项目一致的AppID
WECHAT_APP_SECRET=微信公众平台中的AppSecret
AUTH_TOKEN_SECRET=至少32个随机字符
AUTH_TOKEN_EXPIRE_DAYS=30
```

可生成令牌密钥：

```bash
openssl rand -hex 32
```

AppSecret 只能保存在服务器，不能写入小程序、Git 仓库或前端配置。测试微信号、
体验成员和正式用户只要访问同一个 AppID，都会获得各自真实且稳定的 openid。

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

除健康检查和登录外，所有业务请求必须携带：

```text
Authorization: Bearer 后端签发的访问令牌
```

- `POST /api/v1/auth/wechat-login`：使用 `wx.login` code 登录
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
2. 用 Alembic 管理生产数据库迁移。
3. 为登录和 OCR 接口增加访问频率限制、结构化日志和备份策略。
4. 血压判定仅作健康提示，不应替代医生诊断。

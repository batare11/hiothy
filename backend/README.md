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

首次创建 PostgreSQL 数据库时，先修改
`scripts/schema.sql` 中的 `CHANGE_ME_STRONG_PASSWORD`，再执行：

```bash
sudo -u postgres psql -d postgres -f scripts/schema.sql
```

该脚本会直接创建完整业务表、索引和后来新增的字段，包括：

- `bp_records.hypertension_grade`
- `health_archives` 的年龄、身高、体重、性别、婚姻状态、生活习惯及备注

已有数据库也可以重复执行该脚本，用于补充缺失字段并回填历史血压等级。
Python 初始化命令仍可用于写入演示消息。

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
- `GET /api/v1/messages/unread-count`：未读消息数量
- `PUT /api/v1/messages/{id}/read`：消息已读
- `GET/PUT /api/v1/profile`：个人资料
- `POST /api/v1/feedback`：意见反馈
- `GET /api/v1/feedback`：查询当前用户的历史反馈

血压记录保存或修改后，后端会自动生成血压异常提醒；最近连续 3 次达到
高血压范围时，会额外生成连续异常提醒。自动消息通过 `dedupe_key` 防止重复。

### OCR 引擎

识别接口通过查询参数选择引擎：

```text
POST /api/v1/ocr/blood-pressure?engine=rapid
POST /api/v1/ocr/blood-pressure?engine=glm
POST /api/v1/ocr/blood-pressure?engine=auto
```

- `rapid`：现有本地 RapidOCR 血压专用识别。
- `glm`：使用配置的 GLM 云端视觉接口。
- `auto`：RapidOCR 优先；结果不完整或置信度不足时调用 GLM，并择优返回。

GLM配置全部位于服务器 `.env`，API Key 不得写入小程序或 Git：

```env
GLM_OCR_API_KEY=你的APIKey
GLM_OCR_ENDPOINT=https://open.bigmodel.cn/api/paas/v4/layout_parsing
GLM_OCR_MODEL=实际模型名称
GLM_OCR_TIMEOUT=60
OCR_AUTO_MIN_CONFIDENCE=0.85
```

`GLM_OCR_ENDPOINT` 与 `GLM_OCR_MODEL` 应以购买服务对应的官方控制台文档为准。
GLM-OCR 图片会在内存中转换为标准 JPEG，并通过 Base64 Data URL 提交到
官方 `layout_parsing` 文档解析接口，不再依赖公网临时图片地址。旧环境如果仍配置
`chat/completions`，后端会自动切换到 `layout_parsing`。

## 上线前必须完成

1. 使用 Nginx 配置 HTTPS，将 `https://hiothy.cn/api/v1` 代理到 `127.0.0.1:5000/api/v1`。
2. 用 Alembic 管理生产数据库迁移。
3. 为登录和 OCR 接口增加访问频率限制、结构化日志和备份策略。
4. 血压判定仅作健康提示，不应替代医生诊断。

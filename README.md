# Hiothy 血压健康小程序

本目录包含两个可独立运行的项目：

- `miniprogram/`：原生微信小程序（WXML + WXSS + JavaScript + JSON）
- `backend/`：FastAPI + PostgreSQL 后端

## 快速启动

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/init_db.py
python run.py
```

服务默认监听 `http://0.0.0.0:5000`，接口文档：

- Swagger UI：`http://127.0.0.1:5000/docs`
- 健康检查：`http://127.0.0.1:5000/api/v1/health`

### 2. 启动小程序

1. 使用微信开发者工具导入 `miniprogram/`。
2. 在 `miniprogram/config/index.js` 中设置后端地址。
3. 本地调试可将地址改为 `http://127.0.0.1:5000/api/v1`，并在开发者工具中勾选“不校验合法域名”。
4. 生产环境建议通过 Nginx 将 `https://hiothy.cn/api/v1` 反向代理到 `127.0.0.1:5000/api/v1`，并在微信公众平台配置 `request`、`uploadFile` 合法域名。

## 项目结构

```text
backend/
  app/
    api/             API 路由
    core/            配置与数据库
    models/          数据模型
    schemas/         请求/响应结构
    services/        OCR 与业务服务
  scripts/           数据库初始化脚本
  tests/             基础测试
miniprogram/
  pages/             首页、消息中心、个人中心
  utils/             请求、日期和状态工具
  config/            环境配置
```

详细说明见 `backend/README.md` 和 `miniprogram/README.md`。


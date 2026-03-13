# fapiaohezi

发票盒子（`fapiaohezi`）是一个多子项目仓库，包含后端 API、管理后台、Web 用户端和 UniApp 移动端。

## 1. 项目总览

| 模块 | 路径 | 技术栈 | 默认端口 | 说明 |
|---|---|---|---|---|
| 后端 API | `fp_api` | FastAPI + SQLite | `8000` | 用户、发票、OCR、邮箱推送等接口 |
| 管理后台 | `fp_admin` | Vue2 + Element UI | `8081` | 管理员数据看板、用户管理、发票管理 |
| Web 用户端 | `fp_view` | Vue2 + Element UI | `8080`(默认) | 用户登录、个人信息、发票整理 |
| 移动端 | `fp_app` | UniApp + Vue2 | `8080`(H5) | 移动端上传、历史、个人中心 |

## 2. 目录结构

```text
fapiaohezi/
├─ fp_api/                     # FastAPI 后端
│  ├─ main_refactored.py       # 服务入口
│  ├─ routes.py                # API 路由
│  ├─ services.py              # 业务服务
│  ├─ database.py              # 数据库管理
│  ├─ image_processing.py      # 图片/PDF 预处理
│  ├─ external_batch_api.py    # 外部批处理识别调用
│  └─ email_push.py            # 邮箱推送任务
├─ fp_admin/                   # 后台管理系统
├─ fp_view/                    # Web 用户端
├─ fp_app/                     # UniApp 移动端
├─ docs/
│  ├─ ARCHITECTURE.md          # 架构说明
│  └─ SSH_PUSH.md              # SSH 推送指南
└─ README.md
```

## 3. 快速启动

建议启动顺序：先后端，再前端。

### 3.1 启动后端 `fp_api`

```bash
cd fp_api
pip install -r requirements.txt
python main_refactored.py
```

启动后访问：
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3.2 启动后台 `fp_admin`

```bash
cd fp_admin
npm install
npm run serve
```

访问：http://localhost:8081  
`vue.config.js` 已配置 `/api -> http://localhost:8000` 代理。

### 3.3 启动 Web 端 `fp_view`

```bash
cd fp_view
npm install
npm run serve
```

默认访问：http://localhost:8080

### 3.4 启动移动端 `fp_app` (H5)

```bash
cd fp_app
npm install
npm run dev:h5
```

或使用 HBuilderX 打开 `fp_app` 运行。

## 4. 默认测试账号

- 用户名：`testuser`
- 密码：`test123456`

## 5. 核心接口分组（后端）

- 认证：`/api/register`、`/api/login`
- 用户：`/api/user/{user_id}`、`/api/stats/{user_id}`
- 发票：`/api/upload/{user_id}`、`/api/invoices/{user_id}`、`/api/invoice/{user_id}/{invoice_id}`
- 批量识别：`/api/recognize/{user_id}/unrecognized`、`/api/recognize/status/{job_id}`
- 邮箱推送：`/api/email-push/{user_id}/start`、`/api/email-push/status/{job_id}`
- 管理员：`/api/admin/users`、`/api/admin/invoices`、`/api/admin/stats`

## 6. 文档索引

- 架构说明：[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- SSH 推送：[`docs/SSH_PUSH.md`](./docs/SSH_PUSH.md)

## 7. 推送前建议

仓库已补充根 `.gitignore`，用于忽略依赖目录、数据库和本地运行数据。  
首次推送前请优先阅读 [`docs/SSH_PUSH.md`](./docs/SSH_PUSH.md)。


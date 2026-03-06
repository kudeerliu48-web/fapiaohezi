# 架构说明（Architecture）

本文档描述 `fapiaohezi` 当前代码结构、调用关系和已知注意点。

## 1. 总体架构

```text
fp_admin / fp_view / fp_app
            |
            v
         fp_api (FastAPI)
            |
            +--> main.db (用户主库)
            |
            +--> files/{user_id}/database/{user_id}.db (用户发票库)
            |
            +--> files/{user_id}/uploads|processed (文件存储)
```

## 2. 后端（fp_api）

### 2.1 分层

- 入口层：`main_refactored.py`
- 路由层：`routes.py`
- 业务层：`services.py`
- 数据层：`database.py`
- 工具层：`utils.py`、`config.py`

### 2.2 核心能力

- 用户注册/登录/资料更新
- 发票上传、预处理（图片/PDF -> webp）
- 发票列表、详情、删除、批量删除、导出
- 异步批量识别任务
- 邮箱推送任务（IMAP 拉取发票附件）
- 管理员视角用户与发票统计

### 2.3 主要文件

- `main_refactored.py`：FastAPI app 初始化、CORS、静态文件挂载、启动逻辑
- `routes.py`：所有 REST 接口定义
- `services.py`：`UserService`、`FileService`、`OCRService`
- `image_processing.py`：图片裁剪/缩放/锐化与 webp 输出
- `external_batch_api.py`：外部批处理识别 API 客户端
- `email_push.py`：邮箱抓取任务线程、状态维护

## 3. 前端模块

## 3.1 管理后台（fp_admin）

- 技术栈：Vue2 + Element UI + Axios + ECharts
- 路由：`dashboard`、`users`、`invoices`
- 请求封装：`src/utils/request.js`，`baseURL=/api`
- 开发代理：`vue.config.js` 中 `/api -> http://localhost:8000`

## 3.2 Web 用户端（fp_view）

- 技术栈：Vue2 + Element UI（主链）
- 入口：`src/main.js` + `src/router/index.js`
- 页面：`src/views/Login.vue`、`Profile.vue`、`Invoice.vue`
- API：`src/api/auth.js`、`src/api/invoice.js`

备注：该目录内同时保留了 UniApp 相关文件（`pages.json`、`manifest.json`、`src/pages/*`、`src/utils/api.js`），属于历史混合结构。

## 3.3 移动端（fp_app）

- 技术栈：UniApp + Vue2
- 页面：`src/pages/index|history|mine|login`
- 路由配置：`pages.json`
- API 封装：`src/utils/api.js`

备注：当前仍有部分 `TODO`、`mockData` 和 `test` 占位路径。

## 4. 数据与文件

## 4.1 数据库

- 主库：`fp_api/main.db`
  - 表：`users`、`login_logs`
- 用户库：`fp_api/files/{user_id}/database/{user_id}.db`
  - 表：`invoice_details`

## 4.2 文件目录

- 上传原件：`fp_api/files/{user_id}/uploads`
- 处理结果：`fp_api/files/{user_id}/processed`

## 5. 已知注意点

1. `fp_view` 目前为 Web + UniApp 混合目录，建议后续明确拆分边界。
2. `fp_app` 仍存在演示数据逻辑，联调时建议先替换为真实接口调用。
3. 管理员发票聚合查询在用户量增大时需关注性能与分页准确性。


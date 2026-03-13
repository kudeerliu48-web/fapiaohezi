# V9 发票识别 外部 API 接口文档（实际对外服务实际映射地址及端口：http://182.92.151.50:12001/，以下所有端口1201改成12001）
## 概述

本文档描述 V9 发票识别系统的外部 API 接口，供第三方系统集成使用。

**服务端口**: `1201`（公网 API 网关）
**API 前缀**: `/api/invoices`
**版本标识**: `V9`

---

## 端口规划

| 端口 | 角色 | 访问范围 | 说明 |
|------|------|---------|------|
| **1200** | 前端测试台 | 可对外 | React 可视化界面，拖拽上传、实时查看结果 |
| **1201** | 客户 API 网关 | 对外 | 仅开放 `/api/invoices/*`、`/v1/*`、`/health` |
| **1202** | 管理后台 | 仅内网 | 用户管理、API Key 管理、调用日志、系统配置 |

> **安全说明**：管理接口 `/api/admin/*` 在 1201 端口被网关直接拒绝（返回 403），仅可通过 1202 端口访问。

---

## 鉴权说明

### API Key 管理

外部 API 使用 **API Key** 进行鉴权，管理流程如下：

1. 登录管理后台（端口 `1202`）→ API Key 管理
2. 新建 API Key（完整 Key 仅在创建时显示一次，请立即保存）
3. 将 Key 填入请求的 `api_key` 参数

### 鉴权优先级

| 优先级 | 方式 | 说明 |
|--------|------|------|
| 1 | 环境变量 `V9_API_KEY` | 开发/运维 bypass，设置后优先匹配 |
| 2 | Admin DB 活跃 Key | 通过管理后台创建的 Key（推荐） |
| 3 | 无活跃 Key | 若管理后台尚未创建任何 Key，允许访问（迁移模式） |

> **鉴权失败返回**: HTTP 401 `{"detail": "api_key 无效或已停用"}`

### 流量控制

每个 API Key 可在管理后台独立配置：

| 控制项 | 默认值 | 说明 |
|--------|--------|------|
| **日额度** | 10,000 份 | 每天可处理的发票份数（含成功和失败），超出返回 429 |
| **QPS 限制** | 10 次/秒 | 每秒最多请求次数（滑动窗口），超出返回 429 |

---

## V9 核心字段（9 个）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `invoice_type` | string | 发票类型（增值税电子普通发票、全电发票等） |
| `invoice_number` | string | 发票号码（8 位或 20 位） |
| `issue_date` | string | 开票日期（YYYY-MM-DD 格式） |
| `buyer_name` | string | 购买方名称 |
| `seller_name` | string | 销售方名称 |
| `service_name` | string | 服务/商品名称（只取第一行） |
| `total_amount` | string | 合计金额（不含税），如 `"458.32"` |
| `tax_amount` | string | 税额，如 `"59.58"` |
| `amount_with_tax` | string | 价税合计，如 `"517.90"` |

> **注意**：金额字段返回字符串格式，避免浮点精度问题。

---

## V9 附加状态字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `batch_id` | string | 批次 ID |
| `item_id` | integer | 附件 ID（自增） |
| `seq` | integer | 附件在批次中的序号（从 1 开始） |
| `file_name` | string | 原始文件名 |
| `status` | string | 处理状态：`success` / `failed` / `pending` |
| `remark` | string | 备注信息 |
| `error_message` | string | 错误信息（失败时） |
| `V9_review_status` | string | 复核状态：`pass` / `warning` / `error` |
| `V9_review_note` | string | 复核说明 |
| `source_type` | string | 文件类型：`pdf` / `image` |
| `version` | string | 固定为 `"V9"` |

---

## 接口列表

### 1. 提交批次

**接口**: `POST /api/invoices/submit`

**请求方式**: `multipart/form-data`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `batch_id` | string | 是 | 批次 ID（自定义唯一值，建议格式：`20260309_001`） |
| `api_key` | string | 否 | 从管理后台获取的 API Key（迁移模式下可为空） |
| `files` | file[] | 是 | 附件列表（支持 PDF、JPG、PNG、WEBP、BMP、TIFF） |

**响应示例**:

```json
{
  "success": true,
  "code": 200,
  "message": "批次已接收",
  "data": {
    "batch_id": "20260309_001",
    "task_status": "queued",
    "file_count": 3,
    "version": "V9"
  }
}
```

**说明**:
- 接口立即返回，不等待识别完成
- 后端异步处理每个附件（docgate → OCR → 规则引擎 → LLM 修复）
- 返回后应立即建立 SSE 连接（接口 2）实时接收结果
- 同一 `batch_id` 只能提交一次，重复提交返回 409

---

### 2. SSE 实时推送（主接口）

**接口**: `GET /api/invoices/batches/{batch_id}/stream`

**请求方式**: `GET`（SSE 长连接）

**响应格式**: `text/event-stream`

**事件类型**:

#### 2.1 附件结果事件

**事件名**: `invoice_item`

每当有一个附件处理完成，立即推送该条结果（不等待整批完成）。

**数据格式**:

```json
{
  "item_id": 1,
  "seq": 1,
  "batch_id": "20260309_001",
  "file_name": "invoice_001.pdf",
  "status": "success",
  "invoice_type": "增值税电子普通发票",
  "invoice_number": "50426174",
  "issue_date": "2023-07-22",
  "buyer_name": "湖北十优信息科技发展有限责任公司",
  "seller_name": "道达尔能源销售(湖北)有限公司",
  "service_name": "乙醇汽油",
  "total_amount": "458.32",
  "tax_amount": "59.58",
  "amount_with_tax": "517.90",
  "remark": "",
  "error_message": "",
  "V9_review_status": "pass",
  "V9_review_note": "",
  "source_type": "pdf",
  "version": "V9"
}
```

#### 2.2 批次完成事件

**事件名**: `batch_done`

当所有附件处理完毕后推送，之后 SSE 流自动关闭。

**数据格式**:

```json
{
  "batch_id": "20260309_001",
  "status": "completed",
  "version": "V9"
}
```

**前端示例代码**:

```javascript
const eventSource = new EventSource(`/api/invoices/batches/${batchId}/stream`);

eventSource.addEventListener('invoice_item', (event) => {
  const item = JSON.parse(event.data);
  console.log('收到附件结果:', item);
  addItemToTable(item);
});

eventSource.addEventListener('batch_done', (event) => {
  console.log('批次完成');
  eventSource.close();
});

eventSource.onerror = (error) => {
  console.error('SSE 连接错误:', error);
  eventSource.close();
  // 调用补偿接口恢复数据
  fetchMissingItems(batchId, lastItemId);
};
```

---

### 3. 批次状态

**接口**: `GET /api/invoices/batches/{batch_id}/status`

**请求方式**: `GET`

**响应示例**:

```json
{
  "success": true,
  "code": 200,
  "message": "ok",
  "data": {
    "batch_id": "20260309_001",
    "version": "V9",
    "status": "processing",
    "total_files": 3,
    "completed_files": 1,
    "failed_files": 0,
    "pending_files": 2,
    "progress": 33
  }
}
```

**状态值说明**:

| 状态值 | 说明 |
|--------|------|
| `queued` | 已接收，等待处理 |
| `processing` | 处理中 |
| `completed` | 全部成功 |
| `partial_success` | 部分成功、部分失败 |
| `failed` | 全部失败 |

---

### 4. 增量结果（补偿接口）

**接口**: `GET /api/invoices/batches/{batch_id}/items?since_id=0`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `since_id` | integer | 否 | 上次已读取的最大 `item_id`，默认 0（从头取） |

**响应示例**:

```json
{
  "success": true,
  "code": 200,
  "message": "ok",
  "data": {
    "batch_id": "20260309_001",
    "version": "V9",
    "has_more": true,
    "next_since_id": 2,
    "items": [
      {
        "item_id": 1,
        "seq": 1,
        "batch_id": "20260309_001",
        "file_name": "invoice_001.pdf",
        "status": "success",
        "...": "（字段同接口 2）"
      }
    ]
  }
}
```

**字段说明**:
- `has_more`: `true` 表示还有附件尚未处理完，应继续轮询
- `next_since_id`: 下次请求时使用此值作为 `since_id`

**使用场景**: SSE 断开后补齐缺失结果；页面刷新后恢复历史数据

---

### 5. 整批汇总

**接口**: `GET /api/invoices/batches/{batch_id}/results`

**响应示例**:

```json
{
  "success": true,
  "code": 200,
  "message": "ok",
  "data": {
    "batch_id": "20260309_001",
    "version": "V9",
    "status": "completed",
    "total_files": 3,
    "success_files": 2,
    "failed_files": 1,
    "items": [ ... ]
  }
}
```

**使用场景**: 批次全部完成后，一次性获取所有结果，用于导出 / 校对

---

## 完整联调流程

### 标准流程（推荐）

```
1. 管理后台（1202）创建 API Key
         ↓
2. POST /api/invoices/submit（提交批次 + 文件）
         ↓
3. GET /api/invoices/batches/{batch_id}/stream（SSE 实时逐条接收）
         ↓（SSE 断开时）
4. GET /api/invoices/batches/{batch_id}/items?since_id=X（补偿拉取）
         ↓（批次全部完成后）
5. GET /api/invoices/batches/{batch_id}/results（整批汇总导出）
```

### 简化流程（轮询模式）

如果客户端不支持 SSE，可以使用轮询方式：

```
1. POST /api/invoices/submit（提交）
         ↓
2. 每隔 2-3 秒轮询 GET .../status 查看进度
         ↓（pending_files == 0 时）
3. GET .../results 获取全部结果
```

### 代码示例（JavaScript）

```javascript
// Step 1: 提交批次
const formData = new FormData();
formData.append('batch_id', 'batch_20260310_001');
formData.append('api_key', 'sk-xxxxxxxxxxxxxxxx');
formData.append('files', file1);
formData.append('files', file2);

const res = await fetch('http://your-server:1201/api/invoices/submit', {
  method: 'POST',
  body: formData,
});
const { data } = await res.json();
const batchId = data.batch_id;

// Step 2: 建立 SSE 连接（实时接收）
let lastItemId = 0;
const eventSource = new EventSource(
  `http://your-server:1201/api/invoices/batches/${batchId}/stream`
);

eventSource.addEventListener('invoice_item', (e) => {
  const item = JSON.parse(e.data);
  lastItemId = Math.max(lastItemId, item.item_id);
  renderItem(item);
});

eventSource.addEventListener('batch_done', () => {
  eventSource.close();
  console.log('全部完成');
});

// Step 3: 断线补偿
eventSource.onerror = async () => {
  eventSource.close();
  const r = await fetch(
    `http://your-server:1201/api/invoices/batches/${batchId}/items?since_id=${lastItemId}`
  );
  const { data } = await r.json();
  data.items.forEach(item => renderItem(item));
};
```

### 代码示例（Python）

```python
import requests

API_BASE = "http://your-server:1201"
API_KEY  = "sk-xxxxxxxxxxxxxxxx"

# Step 1: 提交批次
files = [
    ("files", ("invoice_001.pdf", open("invoice_001.pdf", "rb"), "application/pdf")),
    ("files", ("invoice_002.jpg", open("invoice_002.jpg", "rb"), "image/jpeg")),
]
resp = requests.post(f"{API_BASE}/api/invoices/submit", data={
    "batch_id": "batch_20260310_001",
    "api_key": API_KEY,
}, files=files)
print(resp.json())

# Step 2: 轮询等待完成
import time
batch_id = "batch_20260310_001"
while True:
    status = requests.get(f"{API_BASE}/api/invoices/batches/{batch_id}/status").json()
    info = status["data"]
    print(f"进度: {info['progress']}%  完成: {info['completed_files']}/{info['total_files']}")
    if info["pending_files"] == 0:
        break
    time.sleep(2)

# Step 3: 获取全部结果
results = requests.get(f"{API_BASE}/api/invoices/batches/{batch_id}/results").json()
for item in results["data"]["items"]:
    print(f"{item['file_name']}: {item['invoice_number']} {item['amount_with_tax']}")
```

---

## 错误处理

### 统一错误格式

所有接口失败时返回：

```json
{
  "detail": "错误描述（中文）"
}
```

### 常见错误码

| HTTP 状态码 | 说明 | 常见原因 |
|------------|------|---------|
| 400 | 请求参数错误 | 缺少必填字段 |
| 401 | 鉴权失败 | API Key 无效或已停用 |
| 404 | 资源不存在 | batch_id 不存在 |
| 409 | 冲突 | batch_id 重复提交 |
| 422 | 参数校验失败 | 字段类型不对 |
| 429 | 请求过多 | 日额度用完或 QPS 超限 |
| 500 | 服务器内部错误 | 请联系管理员 |
| 503 | 认证服务不可用 | Admin DB 暂时不可用 |

### 429 错误示例

日额度用完：
```json
{"detail": "日额度已用完：今日已处理 10000 份，额度 10000 份，本次提交 5 份超出限制"}
```

QPS 超限：
```json
{"detail": "请求过于频繁：QPS 限制 10 次/秒"}
```

---

## 处理管线说明

提交的每个附件按以下管线处理：

```
docgate（文件分类）
  ↓
OCR（PaddleOCR 文字识别）
  ↓
clean（文本清洗）
  ↓
extract（字段提取）
  ↓
rule_validate（规则引擎校验）
  ├── 规则完整 → 直接出结果（快，~1-2 秒）
  └── 需补充 → LLM 修复 → 二次校验（~3-5 秒）
```

**重复发票检测**：同一批次内相同发票号码的文件，第二张起自动引用第一张结果（`processed_by: "duplicate_reference"`），不重复消耗识别资源。

---

## 配置说明

| 配置项 | 位置 | 说明 |
|--------|------|------|
| API Key 管理 | 管理后台 1202 → API Key 管理 | 创建、编辑、停用、重新生成、删除 |
| 日额度 / QPS | 管理后台 → API Key 编辑 | 每个 Key 独立配置 |
| `V9_API_KEY` 环境变量 | docker-compose.yml | 旧版兼容方式，设置后优先于 DB Key |
| `REDIS_URL` | 环境变量 | Redis 连接地址，默认 `redis://redis:6379` |

---

## 注意事项

1. **SSE 连接**：批次完成后自动关闭；网络抖动时用补偿接口（接口 4）恢复
2. **批次 ID 唯一性**：同一 `batch_id` 只能提交一次，重复提交返回 409
3. **文件格式支持**：PDF、JPG、JPEG、PNG、WEBP、BMP、TIFF，单文件建议 ≤ 10MB
4. **API Key 安全**：Key 创建/重新生成后完整值仅显示一次；如泄露请在管理后台立即停用或删除
5. **调用日志**：所有 submit 请求自动记录到管理后台 → API 调用日志，包含用户、批次号、文件数、耗时、错误信息
6. **日额度计量**：按发票份数计算（非调用次数），一次提交 5 个文件消耗 5 份额度
7. **管理接口隔离**：`/api/admin/*` 在 1201 端口被网关拦截返回 403，仅可通过 1202 端口访问

---

**API 网关端口**: `1201`
**管理后台端口**: `1202`
**前端测试台端口**: `1200`
**版本**: V9 (2026-03-10)

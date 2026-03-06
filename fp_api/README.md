# 发票盒子API服务端

基于FastAPI框架的发票管理系统后端服务

## 功能特性

- 用户注册/登录
- 文件上传管理
- 发票OCR识别（预留接口）
- SQLite数据库存储
- 用户独立文件夹结构

## 项目结构

```
fp_api/
├── main_refactored.py          # 主应用文件（推荐使用）
├── config.py                 # 配置文件
├── utils.py                  # 工具函数
├── models.py                 # 数据模型
├── database.py               # 数据库管理
├── services.py               # 业务服务
├── routes.py                 # API路由
├── requirements.txt          # 依赖包
├── .env                     # 环境变量
├── .gitignore               # Git忽略文件
├── start.bat                # Windows启动脚本
├── start.sh                 # Linux/Mac启动脚本
├── main.db                  # 主数据库文件
└── files/                   # 文件存储目录
    └── {user_id}/         # 用户文件夹（18位数字ID）
        ├── database/       # 用户数据库目录
        │   └── {user_id}.db  # 用户数据库文件
        ├── uploads/        # 上传文件目录
        └── processed/      # 处理后文件目录
```

## 文件说明

### 核心文件

- **main_refactored.py** - 主应用入口，FastAPI应用初始化
- **config.py** - 系统配置，包含数据库路径、文件类型限制等
- **utils.py** - 工具函数，包含UUID生成、密码加密等
- **models.py** - Pydantic数据模型，定义API请求/响应格式

### 数据层

- **database.py** - 数据库管理器，处理用户和发票数据操作
- **services.py** - 业务逻辑层，处理用户认证、文件上传等业务

### API层

- **routes.py** - API路由定义，包含所有RESTful接口

### 配置文件

- **requirements.txt** - Python依赖包列表
- **.env** - 环境变量配置
- **.gitignore** - Git版本控制忽略文件

### 启动脚本

- **start.bat** - Windows系统启动脚本
- **start.sh** - Linux/Mac系统启动脚本

### 数据存储

- **main.db** - SQLite主数据库，存储用户信息
- **files/** - 文件存储根目录
  - **{user_id}/** - 用户独立文件夹（18位数字ID）
    - **database/** - 用户数据库文件夹
      - **{user_id}.db** - 用户个人数据库（发票明细）
    - **uploads/** - 原始上传文件存储
    - **processed/** - 处理后的文件存储

## 数据库结构

### 主数据库 (main.db)

#### users 表
- `id`: 18位UUID，主键
- `username`: 用户名
- `password`: 加密密码
- `email`: 邮箱
- `company`: 公司
- `phone`: 电话
- `login_time`: 登录时间
- `status`: 状态（1:正常 0:禁用）
- `register_time`: 注册时间
- `last_login_time`: 最后登录时间
- `avatar_url`: 头像URL
- `role`: 角色
- `field1/2/3`: 预留字段

#### login_logs 表
- `id`: 日志ID
- `user_id`: 用户ID
- `login_time`: 登录时间
- `ip_address`: IP地址
- `user_agent`: 用户代理
- `login_status`: 登录状态

### 用户数据库 (files/{user_id}/database/user_{user_id}.db)

#### invoice_details 表
- `id`: 18位UUID，主键
- `filename`: 文件名
- `invoice_amount`: 发票金额
- `buyer`: 购买方
- `seller`: 售卖方
- `invoice_number`: 发票号码
- `recognition_status`: 识别状态（0:待识别 1:已识别 2:识别失败）
- `processing_time`: 处理耗时（秒）
- `ocr_text`: OCR文本信息
- `json_info`: JSON处理信息
- `file_type`: 文件类型
- `file_size`: 文件大小（字节）
- `upload_time`: 上传时间
- `field1/2/3`: 预留字段

## API接口

### 用户管理
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/user/{user_id}` - 获取用户信息
- `PUT /api/user/{user_id}` - 更新用户信息

### 文件管理
- `POST /api/upload/{user_id}` - 文件上传
- `GET /api/invoices/{user_id}` - 获取发票列表
- `GET /api/invoice/{user_id}/{invoice_id}` - 获取发票详情
- `POST /api/ocr/{user_id}/{invoice_id}` - 手动OCR识别
- `GET /api/stats/{user_id}` - 获取用户统计信息

### 系统接口
- `GET /api/health` - 健康检查
- `GET /files/{user_id}/{file_path}` - 静态文件访问

## 安装运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行服务
```bash
python main_refactored.py
```

### 3. Windows快捷启动
```bash
start.bat
```

### 4. Linux/Mac快捷启动
```bash
chmod +x start.sh
./start.sh
```

## API文档

启动后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 测试账号

系统初始化时会自动创建测试账号：
- **用户名**: `testuser`
- **密码**: `test123456`
- **邮箱**: `test@example.com`
- **公司**: `测试科技有限公司`

## OCR识别接口

文件上传后，系统会：
1. 保存文件到 `files/{user_id}/uploads/` 目录
2. 在用户数据库中创建记录（状态为待识别）
3. 预留OCR识别接口调用位置

你需要在 `services.py` 的 `OCRService.process_invoice()` 方法中对接实际的OCR服务。

## 文件存储规则

- 每个用户有独立的文件夹：`files/{user_id}/`
- 上传文件存储在：`files/{user_id}/uploads/`
- 处理后文件存储在：`files/{user_id}/processed/`
- 用户数据库存储在：`files/{user_id}/database/`

## UUID格式

- **用户ID**: 18位纯数字（如：123456789012345678）
- **文件ID**: 18位纯数字（如：987654321098765432）
- **发票ID**: 18位纯数字（如：567890123456789012）

## 安全特性

- 密码SHA256加密存储
- 用户独立数据库隔离
- 文件访问权限控制
- CORS跨域支持

## 开发说明

### 添加新API
1. 在 `models.py` 中定义数据模型
2. 在 `services.py` 中实现业务逻辑
3. 在 `routes.py` 中添加路由
4. 更新API文档

### 数据库迁移
如需修改数据库结构：
1. 更新 `database.py` 中的表创建语句
2. 为现有数据库添加迁移脚本
3. 测试新旧数据兼容性

## 部署建议

### 生产环境
- 使用环境变量管理敏感配置
- 配置反向代理（Nginx）
- 启用HTTPS
- 设置日志轮转
- 配置数据库备份

### Docker部署
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main_refactored.py"]

# 发票盒子后台管理系统

基于 Vue 2 + Element UI 的发票管理后台系统，与 fp_api 后端服务配合使用。

## 技术栈

- **前端框架**: Vue 2.6.14
- **UI 组件库**: Element UI 2.15.14
- **路由**: Vue Router 3.5.1
- **HTTP 客户端**: Axios 1.6.0
- **图表库**: ECharts 5.4.3
- **构建工具**: Vue CLI 5.0.0

## 功能模块

### 1. 首页（Dashboard）
- 📊 数据统计卡片：用户总数、发票总数、已识别发票数、发票总金额
- 📈 发票类型分布饼图
- 📉 近 7 天发票趋势折线图

### 2. 用户管理
- 👥 用户列表展示（分页）
- 🔍 搜索功能（按用户名/邮箱）
- 📋 用户详情查看
- 🗑️ 用户删除（同时删除用户文件夹和数据库）

### 3. 发票管理
- 📄 发票列表展示（分页）
- 🔍 搜索功能（按发票号/购买方/销售方/文件名）
- 📤 发票上传（支持 PDF、JPG、PNG 格式）
- 👁️ 发票详情查看
- 🔄 OCR 识别触发
- 🗑️ 发票删除
- 📥 Excel 导出

## 安装步骤

### 1. 安装依赖
```bash
cd fp_admin
npm install
```

### 2. 启动后端 API
```bash
cd ../fp_api
python main_refactored.py
```
后端服务将在 http://localhost:8000 启动

### 3. 启动前端开发服务器
```bash
cd fp_admin
npm run serve
```
前端应用将在 http://localhost:8081 启动

## 项目结构

```
fp_admin/
├── public/
│   └── index.html
├── src/
│   ├── api/              # API 接口定义
│   │   ├── user.js
│   │   └── invoice.js
│   ├── components/       # 公共组件
│   │   └── Layout.vue
│   ├── router/          # 路由配置
│   │   └── index.js
│   ├── styles/          # 全局样式
│   │   └── global.scss
│   ├── utils/           # 工具函数
│   │   └── request.js
│   ├── views/           # 页面视图
│   │   ├── Dashboard.vue
│   │   ├── Users.vue
│   │   └── Invoices.vue
│   ├── App.vue
│   └── main.js
├── package.json
├── vue.config.js
└── babel.config.js
```

## 主要特性

### 数据同步
- ✅ 用户上传发票后自动同步到 `main.db` 数据库
- ✅ 每个用户独立的数据库文件（位于 `files/{user_id}/db/main.db`）
- ✅ 管理员可查看所有用户的发票数据

### 文件处理
- 📁 支持多种文件格式：PDF、JPG、PNG
- 🖼️ 自动预处理生成 WebP 格式预览图
- 📊 OCR 识别结果存储
- 💾 文件和元数据双重保存

### 管理功能
- 👨‍💼 管理员视角：统览所有用户和数据
- 📊 实时统计：可视化数据展示
- 🔐 用户管理：增删改查
- 📝 发票管理：全生命周期管理

## API 端点

### 管理员接口
- `GET /api/admin/users` - 获取所有用户列表
- `DELETE /api/admin/user/{user_id}` - 删除用户
- `GET /api/admin/invoices` - 获取所有发票列表
- `GET /api/admin/invoice-stats` - 获取发票统计
- `GET /api/admin/stats` - 获取综合统计
- `GET /api/invoice/detail/{invoice_id}` - 获取发票详情（管理员）
- `DELETE /api/invoice/{invoice_id}` - 删除发票（管理员）

## 默认测试账号

后端会自动创建测试用户：
- 用户名：`testuser`
- 密码：`test123456`

## 注意事项

1. **端口配置**：
   - 后端 API 运行在 `8000` 端口
   - 前端运行在 `8081` 端口
   - 已在 `vue.config.js` 中配置代理

2. **CORS**：
   - 后端已配置允许跨域请求
   - 开发环境通过代理解决跨域问题

3. **数据库**：
   - 主数据库：`fp_api/main.db`（存储用户信息）
   - 用户数据库：`fp_api/files/{user_id}/db/main.db`（存储发票信息）

4. **文件存储**：
   - 原始文件：`fp_api/files/{user_id}/uploads/`
   - 处理后文件：`fp_api/files/{user_id}/processed/`

## 构建生产版本

```bash
npm run build
```

生成的文件将在 `dist/` 目录中。

## 开发规范

- 使用 ESLint 进行代码检查
- SCSS 用于样式编写
- 组件化开发模式
- Axios 统一 HTTP 请求管理

## 常见问题

### Q: 为什么图表不显示？
A: 确保 ECharts 已正确安装，并检查 DOM 容器是否有明确的高度。

### Q: 上传文件失败？
A: 检查后端服务是否正常运行，以及用户是否存在。

### Q: 搜索功能无效？
A: 确认关键词匹配逻辑和数据库字段是否正确。

## 更新日志

### v1.0.0 (2026-03-05)
- ✨ 初始版本发布
- 🎨 完成首页 Dashboard
- 👥 完成用户管理
- 📄 完成发票管理
- 📊 集成 ECharts 图表
- 🔗 对接 fp_api 后端服务

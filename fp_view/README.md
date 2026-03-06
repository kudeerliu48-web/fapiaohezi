# 发票识别管理系统（前端）

基于 Vue 2 + Element UI 的发票识别管理前端，包含个人信息与发票整理两大模块。

## 功能说明

- **个人信息**：展示姓名、性别、邮箱、公司、手机号码（当前为示例数据）
- **发票整理**
  - 手动上传：支持图片（JPG/PNG/GIF 等）与 PDF
  - 邮箱推送：时间范围可选「近七天」「近一个月」「近三个月」，默认近七天
  - 发票清单：列表展示所有记录，支持搜索、预览、删除（前端演示）

## 技术栈

- Vue 2.7
- Vue Router
- Element UI
- Sass

## 运行方式

```bash
# 安装依赖
npm install

# 本地开发
npm run serve

# 构建生产
npm run build
```

开发时访问：http://localhost:8080（端口以终端提示为准）

## 项目结构

```
fapiaohezi/
├── public/
├── src/
│   ├── router/       # 路由
│   ├── styles/       # 全局样式
│   ├── views/        # 页面：Profile 个人信息、Invoice 发票整理
│   ├── App.vue
│   └── main.js
├── package.json
└── vue.config.js
```

当前未对接服务端，数据均为前端模拟。

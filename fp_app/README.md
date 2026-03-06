# 发票盒子 App - UniApp 移动端应用

基于 **UniApp + Vue 2** 开发的智能发票识别管理移动应用（独立项目）

## 📱 项目说明

这是一个**独立的 UniApp 项目**，与原有的 `fp_view` (Vue2 Web 版) 和 `fp_admin` (后台管理版) 并列。

### 项目定位

- **fp_view** - Vue2 + Element UI 的 Web 端用户界面
- **fp_admin** - Vue2 + Element UI 的后台管理系统  
- **fp_app** - UniApp + Vue2 的移动端应用（本项目）✨

## 🎯 功能模块

### 1. 首页（发票操作）
- 📷 拍照上传发票
- 📁 从相册选择文件
- 📊 数据统计展示
- ⚡ 快捷操作入口

### 2. 历史记录
- 📋 发票列表展示
- 🔍 搜索功能
- 🏷️ 状态标识
- 🗑️ 删除/重新识别

### 3. 个人中心
- 👤 用户信息管理
- 📊 数据统计
- 📥 导出发票
- ⚡ 批量识别
- ℹ️ 关于我们

## 🛠️ 技术栈

- **框架**: UniApp (兼容 Vue 2)
- **构建工具**: Vue CLI 5
- **样式**: SCSS
- **HTTP**: uni.request 封装
- **支持平台**: H5、微信小程序、Android、iOS

## 📦 目录结构

```
fp_app/
├── src/
│   ├── pages/           # 页面目录
│   │   ├── index/       # 首页
│   │   ├── history/     # 历史记录
│   │   ├── mine/        # 个人中心
│   │   └── login/       # 登录页
│   ├── utils/           # 工具函数
│   │   └── api.js       # API 接口
│   ├── static/          # 静态资源
│   ├── App.vue          # 应用配置
│   └── main.js          # 入口文件
├── manifest.json        # 应用配置
├── pages.json           # 页面路由
├── package.json         # 项目依赖
└── README.md            # 项目文档
```

## 🚀 快速开始

### 方法一：使用 HBuilderX（推荐）

1. **下载 HBuilderX**
   - https://www.dcloud.io/hbuilderx.html

2. **打开项目**
   ```
   在 HBuilderX 中打开 fp_app 文件夹
   ```

3. **运行到浏览器**
   ```
   运行 > 运行到浏览器 > Chrome
   ```

4. **访问地址**
   ```
   http://localhost:8080
   ```

### 方法二：命令行

```bash
# 1. 进入项目目录
cd fp_app

# 2. 安装依赖
npm install

# 3. 运行到 H5
npm run dev:h5

# 4. 访问 http://localhost:8080
```

## 🔧 配置说明

### API 接口

编辑 `src/utils/api.js`：

```javascript
const BASE_URL = 'http://localhost:8000/api'
```

确保后端服务已启动：
```bash
cd ../fp_api
python main_refactored.py
```

### TabBar 图标

需要在 `src/static/tabbar/` 放置以下图标（81x81px）：
- home.png / home-active.png
- history.png / history-active.png
- mine.png / mine-active.png

**临时方案**：如果没有图标，可以在 `pages.json` 中移除 `iconPath` 和 `selectedIconPath` 配置。

## 📋 测试账号

- 用户名：`testuser`
- 密码：`test123456`

## 🌐 多端发布

### H5
```bash
npm run build:h5
```

### 微信小程序
```bash
npm run build:mp-weixin
```

### Android/iOS App
通过 HBuilderX 云打包生成 APK/IPA

## 🎨 界面设计

- **主色调**: 渐变紫 (#667eea → #764ba2)
- **风格**: 简洁现代
- **交互**: 流畅动画、友好提示
- **适配**: 响应式布局

## 📝 注意事项

1. **项目独立性**
   - 这是独立的 UniApp 项目
   - 与 fp_view 互不影响
   - 可以单独运行和部署

2. **开发工具**
   - 推荐使用 HBuilderX
   - 也可以用 VSCode + CLI

3. **API 对接**
   - 统一使用 `utils/api.js` 封装
   - 自动携带 token
   - 统一错误处理

## 🆚 与 fp_view 的区别

| 特性 | fp_view | fp_app |
|------|---------|--------|
| 技术栈 | Vue2 + Element UI | UniApp + Vue2 |
| 平台 | Web 浏览器 | 多端（H5/小程序/App） |
| UI 框架 | Element UI | 原生组件 |
| 单位 | px | rpx |
| 导航 | Vue Router | TabBar |
| 用途 | Web 端用户界面 | 移动端应用 |

## 📄 更新日志

### v1.0.0 (2026-03-06)
- ✨ 创建独立的 UniApp 项目
- 📱 完成首页、历史记录、个人中心
- 🔐 实现登录功能
- 📊 集成数据统计
- 🎨 简洁现代的 UI 设计

## 📞 技术支持

- UniApp 官方文档：https://uniapp.dcloud.net.cn/
- 后端 API 文档：http://localhost:8000/docs

---

**发票盒子 App** - 让发票管理更便捷！✨

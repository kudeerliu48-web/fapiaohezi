# 发票盒子 - UniApp 移动端应用

基于 UniApp + Vue 2 开发的智能发票识别管理移动应用。

## 📱 项目特点

- **跨平台支持** - 一套代码编译到 iOS、Android、微信小程序等多个平台
- **简洁界面** - 现代化设计风格，操作流畅
- **智能识别** - 对接后端 OCR 接口，自动识别发票信息
- **数据同步** - 实时同步到数据库，数据安全存储

## 🎯 功能模块

### 1. 首页（发票操作）
- 📷 **拍照上传** - 直接拍摄发票进行识别
- 📁 **文件选择** - 从相册选择图片或 PDF 文件
- 📊 **数据统计** - 显示总发票数、已识别数量、总金额
- ⚡ **快捷操作** - 快速跳转到历史记录、批量上传

### 2. 历史记录
- 📋 **发票列表** - 展示所有发票识别记录
- 🔍 **搜索功能** - 按发票号、购买方等关键词搜索
- 🏷️ **状态标识** - 待识别/已识别/识别失败
- 🗑️ **删除操作** - 单张删除发票记录
- 🔄 **重新识别** - 支持手动触发重新识别

### 3. 个人中心
- 👤 **用户信息** - 显示用户名、邮箱等基本信息
- 📊 **数据统计** - 查看详细的统计数据
- 📥 **发票导出** - 支持导出 Excel 格式
- ⚡ **批量识别** - 一键识别所有待识别发票
- ⚙️ **设置** - 应用相关设置
- ℹ️ **关于我们** - 应用版本和介绍

## 🛠️ 技术栈

- **框架**: UniApp (Vue 2)
- **UI**: 原生组件 + 自定义样式
- **HTTP**: uni.request 封装
- **状态管理**: 本地存储
- **构建工具**: HBuilderX / CLI

## 📦 项目结构

```
fp_view/
├── src/
│   ├── pages/           # 页面目录
│   │   ├── index/       # 首页
│   │   ├── history/     # 历史记录
│   │   ├── mine/        # 个人中心
│   │   └── login/       # 登录页
│   ├── utils/           # 工具函数
│   │   └── api.js       # API 接口封装
│   ├── static/          # 静态资源
│   │   └── tabbar/      # 底部导航图标
│   ├── App.vue          # 应用配置
│   ├── main.js          # 入口文件
│   └── manifest.json    # 应用配置
├── pages.json           # 页面路由配置
├── package.json         # 项目依赖
└── README.md            # 项目文档
```

## 🚀 快速开始

### 方法一：使用 HBuilderX（推荐）

1. **下载并安装 HBuilderX**
   - 官网：https://www.dcloud.io/hbuilderx.html

2. **打开项目**
   ```bash
   # 在 HBuilderX 中打开 fp_view 文件夹
   ```

3. **运行到浏览器**
   - 点击菜单栏：运行 > 运行到浏览器 > Chrome

4. **运行到微信开发者工具**
   - 点击菜单栏：运行 > 运行到小程序模拟器 > 微信开发者工具

5. **打包成 App**
   - 点击菜单栏：发行 > 原生 App-云打包

### 方法二：使用 CLI

1. **安装依赖**
   ```bash
   cd fp_view
   npm install
   ```

2. **运行到 H5**
   ```bash
   npm run dev:h5
   ```

3. **运行到微信小程序**
   ```bash
   npm run dev:mp-weixin
   ```

4. **打包**
   ```bash
   # 打包 H5
   npm run build:h5
   
   # 打包微信小程序
   npm run build:mp-weixin
   ```

## 🔧 配置说明

### API 接口配置

编辑 `src/utils/api.js` 文件中的 `BASE_URL`：

```javascript
const BASE_URL = 'http://localhost:8000/api'
```

生产环境请修改为实际的后端地址。

### TabBar 图标

需要在 `static/tabbar/` 目录下准备以下图标：
- home.png / home-active.png
- history.png / history-active.png  
- mine.png / mine-active.png

图标尺寸建议：81x81px

## 📱 平台差异说明

### H5
- 直接在浏览器运行
- 支持拍照和文件选择
- 需要后端服务启动

### 微信小程序
- 需要在微信公众平台注册小程序
- 配置服务器域名
- 部分功能需要用户授权

### App (iOS/Android)
- 需要配置相应权限
- 相机和相册权限
- 网络访问权限

## 🔐 测试账号

- 用户名：`testuser`
- 密码：`test123456`

## 📝 开发注意事项

1. **图片上传**
   - 使用 `uni.chooseImage` 选择图片
   - 使用 `uni.uploadFile` 上传图片
   - 注意处理临时文件路径

2. **网络请求**
   - 统一使用封装的 `api.js`
   - 自动携带 token
   - 统一错误处理

3. **数据存储**
   - 使用 `uni.setStorageSync` 存储 token
   - 使用 `uni.getStorageSync` 读取数据

4. **样式单位**
   - 使用 rpx 响应式像素
   - 750rpx = 屏幕宽度
   - 自动适配不同设备

## 🎨 UI 设计规范

- **主色调**: 渐变紫 (#667eea → #764ba2)
- **字体大小**: 
  - 标题：32-48rpx
  - 正文：26-30rpx
  - 辅助文字：24rpx
- **圆角**: 16-50rpx
- **间距**: 20-40rpx

## 📊 API 接口文档

详细接口请参考后端 API 文档：http://localhost:8000/docs

主要接口：
- POST `/api/login` - 用户登录
- GET `/api/invoices` - 获取发票列表
- POST `/api/upload/{user_id}` - 上传发票
- DELETE `/api/invoice/{user_id}/{invoice_id}` - 删除发票
- POST `/api/ocr/{user_id}/{invoice_id}` - OCR 识别
- GET `/api/stats/{user_id}` - 获取统计信息

## 🐛 常见问题

### Q: 图片无法上传？
A: 检查后端服务是否启动，以及 CORS 配置是否正确。

### Q: 小程序提示域名未备案？
A: 需要在微信公众平台配置合法的服务器域名。

### Q: App 无法访问网络？
A: 检查 manifest.json 中的权限配置和网络权限。

## 📄 更新日志

### v1.0.0 (2026-03-05)
- ✨ 初始版本发布
- 🎨 完成首页、历史记录、个人中心三个主要页面
- 📷 实现拍照上传和文件选择功能
- 📊 集成数据统计展示
- 🔐 实现用户登录功能
- 📱 支持 H5、微信小程序、App 多端运行

## 📞 联系方式

如有问题或建议，欢迎联系。

---

**发票盒子** - 让发票管理更高效！✨

# SSH 推送指南（GitHub）

目标远端仓库：`git@github.com:kudeerliu48-web/fapiaohezi.git`

## 1. 本机准备

## 1.1 检查 SSH Key

```bash
ls ~/.ssh
```

如果没有 `id_ed25519`，创建一把：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

## 1.2 添加到 ssh-agent

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

Windows PowerShell 可用：

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519
```

## 1.3 绑定到 GitHub

复制公钥内容（`id_ed25519.pub`）到 GitHub:

- GitHub -> Settings -> SSH and GPG keys -> New SSH key

测试连通：

```bash
ssh -T git@github.com
```

## 2. 仓库初始化与远端配置

你当前仓库存在 `dubious ownership` 安全提示。可在命令中临时带参数执行：

```bash
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi status
```

设置远端并推送：

```bash
cd F:/web/AI_DEMO/fapiaohezi
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi remote add origin git@github.com:kudeerliu48-web/fapiaohezi.git
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi branch -M main
```

如果之前已经有 `origin`，先改地址：

```bash
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi remote set-url origin git@github.com:kudeerliu48-web/fapiaohezi.git
```

## 3. 首次提交前检查

本仓库已添加根 `.gitignore`，会忽略：

- `**/node_modules`
- Python 缓存和虚拟环境
- 数据库文件（如 `*.db`）
- `fp_api/files/` 运行数据目录

如果你此前执行过 `git add .`，且大文件已进入暂存区，可先取消缓存跟踪：

```bash
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi rm -r --cached fp_admin/node_modules fp_view/node_modules fp_api/files fp_api/main.db
```

（如果提示路径不存在，直接忽略即可）

## 4. 提交与推送

```bash
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi add .
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi commit -m "docs: add project README, architecture and ssh push guide"
git -c safe.directory=F:/web/AI_DEMO/fapiaohezi push -u origin main
```

## 5. 常见问题

## 5.1 `Permission denied (publickey)`

- 检查公钥是否已加到 GitHub
- `ssh-add -l` 查看是否已加载密钥
- 确认远端地址是 `git@github.com:...` 而不是 `https://...`

## 5.2 `dubious ownership`

可二选一：

1. 每次命令带 `-c safe.directory=F:/web/AI_DEMO/fapiaohezi`
2. 一次性全局配置：

```bash
git config --global --add safe.directory F:/web/AI_DEMO/fapiaohezi
```


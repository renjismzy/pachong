# Vercel 部署指南

本项目已配置为支持 Vercel 部署。以下是部署步骤：

## 部署前准备

1. **环境变量配置**
   在 Vercel 项目设置的 Environment Variables 页面中添加以下环境变量：
   
   | 变量名 | 值 | 环境 |
   |--------|----|---------|
   | `FEISHU_APP_ID` | 你的飞书应用ID | Production, Preview, Development |
   | `FEISHU_APP_SECRET` | 你的飞书应用密钥 | Production, Preview, Development |
   | `DEEPSEEK_API_KEY` | 你的DeepSeek API密钥 | Production, Preview, Development |
   | `SECRET_KEY` | 你的Flask密钥 | Production, Preview, Development |
   
   **重要**：不要在 `vercel.json` 中使用 `@secret_name` 引用，直接在 Vercel 控制台设置环境变量即可。

2. **文件结构**
   ```
   ├── api/
   │   ├── index.py          # Vercel入口文件
   │   └── web_app_vercel.py # Vercel适配的Flask应用
   ├── vercel.json           # Vercel配置文件
   ├── requirements-vercel.txt # Vercel依赖文件
   └── .vercelignore         # 忽略文件配置
   ```

## 部署步骤

### 方法一：通过 Vercel CLI

1. 安装 Vercel CLI：
   ```bash
   npm install -g vercel
   ```

2. 登录 Vercel：
   ```bash
   vercel login
   ```

3. 在项目根目录执行部署：
   ```bash
   vercel --prod
   ```

### 方法二：通过 GitHub 集成

1. 将代码推送到 GitHub 仓库
2. 在 Vercel 控制台导入 GitHub 项目
3. 配置环境变量
4. 部署

## 功能限制

由于 Vercel 是无服务器环境，以下功能在部署版本中不可用：

- ❌ 定时任务调度（BackgroundScheduler）
- ❌ WebSocket 实时通信
- ❌ 日志文件访问
- ❌ 系统资源监控
- ✅ 手动爬虫任务执行
- ✅ 比赛数据查看
- ✅ 基本的 Web 界面

## 故障排除

1. **DEPLOYMENT_NOT_FOUND 错误**
   - 确保 `vercel.json` 配置正确
   - 检查 `api/index.py` 文件存在
   - 验证项目结构符合 Vercel 要求

2. **Function Runtime Version Error**
   - 错误信息：`Function Runtimes must have a valid version, for example 'now-php@1.0.0'`
   - 解决方案：移除 `runtime` 字段，让 Vercel 自动检测 Python 运行时
   - 已修复：从 `functions` 配置中移除了 `runtime` 字段

3. **Environment Variable Secret Reference Error**
   - 错误信息：`Environment Variable "FEISHU_APP_ID" references Secret "feishu_app_id", which does not exist`
   - 解决方案：不要在 `vercel.json` 中使用 `@secret_name` 语法
   - 直接在 Vercel 控制台的 Environment Variables 页面设置变量
   - 已修复：移除了 `vercel.json` 中的 `env` 配置

4. **Conflicting functions and builds configuration**
   - 已修复：移除了冲突的 `builds` 和 `routes` 配置
   - 现在使用现代的 `functions` 和 `rewrites` 配置
   - 让 Vercel 自动检测 Python 运行时

5. **导入模块失败**
   - 检查 `api/requirements.txt` 包含所需依赖
   - 确保环境变量配置正确

6. **函数超时**
   - 已设置 30 秒超时时间
   - Vercel 免费版有执行时间限制
   - 考虑升级到 Pro 版本或优化爬虫逻辑

## 本地测试

在部署前，可以本地测试 Vercel 版本：

```bash
cd api
python web_app_vercel.py
```

访问 `http://localhost:5000` 验证功能正常。
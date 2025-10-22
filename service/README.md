# DeepSeek-OCR API Systemd Service

这个目录包含将 DeepSeek-OCR API 配置为 Linux 系统服务的所有必要文件。

## 📁 文件说明

- **`deepseek-ocr-api.service`** - systemd 服务配置文件
- **`deepseek-ocr.env`** - 环境变量配置文件
- **`install.sh`** - 服务安装脚本
- **`uninstall.sh`** - 服务卸载脚本
- **`status.sh`** - 服务状态检查脚本
- **`README.md`** - 本文档

## 🚀 快速开始

### 前置要求

1. **Python 虚拟环境已创建并安装依赖**
   ```bash
   cd /root/DeepSeek-OCR
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **模型文件已下载**
   ```bash
   # 确保 deepseek_ocr/ 目录存在且包含模型文件
   ls deepseek_ocr/
   ```

3. **具有 root 权限**
   ```bash
   # 所有服务操作需要 sudo
   ```

### 安装服务

```bash
cd /root/DeepSeek-OCR
sudo bash service/install.sh
```

安装脚本会：
- ✅ 检查前置条件
- ✅ 复制服务文件到 systemd
- ✅ 创建环境配置链接
- ✅ 设置开机自启
- ✅ 显示使用说明

### 启动服务

```bash
sudo systemctl start deepseek-ocr-api
```

### 检查状态

```bash
# 方式1: 使用便捷脚本（推荐）
bash service/status.sh

# 方式2: 使用 systemctl
sudo systemctl status deepseek-ocr-api
```

### 查看日志

```bash
# 实时查看日志
sudo journalctl -u deepseek-ocr-api -f

# 查看最近100行
sudo journalctl -u deepseek-ocr-api -n 100

# 查看今天的日志
sudo journalctl -u deepseek-ocr-api --since today
```

## ⚙️ 配置

### 修改配置

编辑环境配置文件：

```bash
nano service/deepseek-ocr.env
```

### 常用配置项

```bash
# API 端口
API_PORT=8000

# 并发数（根据GPU显存调整）
MAX_CONCURRENCY=100

# 最大PDF页数
MAX_PDF_PAGES=50

# 最大上传文件大小（MB）
MAX_FILE_SIZE_MB=20

# CUDA路径（如使用CUDA 11.8）
# TRITON_PTXAS_PATH=/usr/local/cuda-11.8/bin/ptxas
```

### 应用配置更改

修改配置后重启服务：

```bash
sudo systemctl restart deepseek-ocr-api
```

## 🔧 服务管理命令

### 基本操作

```bash
# 启动服务
sudo systemctl start deepseek-ocr-api

# 停止服务
sudo systemctl stop deepseek-ocr-api

# 重启服务
sudo systemctl restart deepseek-ocr-api

# 重载配置
sudo systemctl reload deepseek-ocr-api

# 查看状态
sudo systemctl status deepseek-ocr-api
```

### 开机自启

```bash
# 启用开机自启（安装时已自动启用）
sudo systemctl enable deepseek-ocr-api

# 禁用开机自启
sudo systemctl disable deepseek-ocr-api

# 检查是否已启用
systemctl is-enabled deepseek-ocr-api
```

### 日志管理

```bash
# 实时日志
sudo journalctl -u deepseek-ocr-api -f

# 查看错误日志
sudo journalctl -u deepseek-ocr-api -p err

# 查看特定时间段
sudo journalctl -u deepseek-ocr-api --since "2025-10-22 10:00:00" --until "2025-10-22 12:00:00"

# 清理旧日志（保留最近7天）
sudo journalctl --vacuum-time=7d
```

## 🔍 故障排查

### 服务无法启动

1. **检查虚拟环境**
   ```bash
   ls -la /root/DeepSeek-OCR/.venv/bin/uvicorn
   ```

2. **检查模型文件**
   ```bash
   ls /root/DeepSeek-OCR/deepseek_ocr/
   ```

3. **查看详细错误**
   ```bash
   sudo journalctl -u deepseek-ocr-api -n 50 --no-pager
   ```

4. **检查端口占用**
   ```bash
   sudo netstat -tulnp | grep 8000
   ```

### GPU 内存不足

编辑配置文件降低并发数：

```bash
nano service/deepseek-ocr.env
# 修改: MAX_CONCURRENCY=50
sudo systemctl restart deepseek-ocr-api
```

### 权限问题

确保工作目录权限正确：

```bash
sudo chown -R root:root /root/DeepSeek-OCR
sudo chmod -R 755 /root/DeepSeek-OCR
```

### API Key 问题

检查 API Key 文件：

```bash
ls -l /root/DeepSeek-OCR/APIKEY.keys
cat /root/DeepSeek-OCR/APIKEY.keys
```

## 📊 性能监控

### 实时监控

```bash
# CPU和内存使用
sudo systemctl status deepseek-ocr-api

# GPU使用情况
nvidia-smi -l 1

# 进程详情
ps aux | grep uvicorn
```

### API 健康检查

```bash
# 检查服务健康
curl http://localhost:8000/health

# 检查API响应
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/v1/info
```

## 🔄 更新服务

### 更新代码后重启

```bash
cd /root/DeepSeek-OCR
git pull  # 如果使用git
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart deepseek-ocr-api
```

### 更新服务配置

```bash
# 修改 service/ 目录下的文件后
sudo bash service/install.sh
sudo systemctl restart deepseek-ocr-api
```

## 🗑️ 卸载服务

```bash
sudo bash service/uninstall.sh
```

卸载脚本会：
- ✅ 停止服务
- ✅ 禁用开机自启
- ✅ 删除服务文件
- ✅ 清理配置链接

**注意**: 卸载不会删除项目文件，只移除 systemd 服务配置。

## 🔐 安全建议

1. **保护 API Key**
   ```bash
   chmod 600 /root/DeepSeek-OCR/APIKEY.keys
   ```

2. **使用防火墙**
   ```bash
   # 只允许特定IP访问
   sudo ufw allow from 192.168.1.0/24 to any port 8000
   ```

3. **反向代理**
   ```bash
   # 建议使用 Nginx 配置 HTTPS
   # 不要直接暴露 uvicorn 到公网
   ```

4. **限制资源**
   ```bash
   # 在 service 文件中添加资源限制
   MemoryLimit=8G
   CPUQuota=400%
   ```

## 📝 服务文件详解

### deepseek-ocr-api.service

```ini
[Unit]
Description=DeepSeek-OCR API Service
After=network.target          # 网络就绪后启动

[Service]
Type=simple                   # 简单服务类型
User=root                     # 运行用户
WorkingDirectory=/root/DeepSeek-OCR
EnvironmentFile=/root/DeepSeek-OCR/service/deepseek-ocr.env
ExecStart=...                 # 启动命令

Restart=always                # 总是重启
RestartSec=10                # 重启延迟10秒
StartLimitBurst=5            # 连续失败5次后停止
TimeoutStartSec=300          # 启动超时300秒

[Install]
WantedBy=multi-user.target   # 多用户模式下启动
```

## 💡 使用技巧

### 1. 快速重启

创建别名方便操作：

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
alias ocr-start='sudo systemctl start deepseek-ocr-api'
alias ocr-stop='sudo systemctl stop deepseek-ocr-api'
alias ocr-restart='sudo systemctl restart deepseek-ocr-api'
alias ocr-status='bash /root/DeepSeek-OCR/service/status.sh'
alias ocr-logs='sudo journalctl -u deepseek-ocr-api -f'
```

### 2. 开发模式

临时停止服务进行开发：

```bash
sudo systemctl stop deepseek-ocr-api
cd /root/DeepSeek-OCR
bash api/start.sh  # 手动启动用于调试
```

### 3. 多环境配置

创建不同的环境配置文件：

```bash
cp service/deepseek-ocr.env service/deepseek-ocr.prod.env
cp service/deepseek-ocr.env service/deepseek-ocr.dev.env

# 修改 service 文件中的 EnvironmentFile 切换环境
```

## 📚 相关文档

- [API 使用文档](../api/README.md)
- [DeepSeek-OCR 主文档](../README.md)
- [systemd 官方文档](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

## ❓ 常见问题

**Q: 服务启动慢怎么办？**
A: 模型加载需要时间，特别是首次启动。可以增加 `TimeoutStartSec` 或使用 `status.sh` 监控启动进度。

**Q: 如何设置多个 API 端口？**
A: 复制 service 文件创建多个服务实例，修改端口和服务名称。

**Q: 能在非 root 用户下运行吗？**
A: 可以，修改 service 文件中的 `User` 和 `Group`，确保该用户有权限访问项目目录和 GPU。

**Q: 如何实现服务的自动重启？**
A: 已配置 `Restart=always`，服务异常退出会自动重启。

## 📞 支持

遇到问题？

1. 查看日志: `sudo journalctl -u deepseek-ocr-api -n 100`
2. 检查状态: `bash service/status.sh`
3. 参考 API 文档: http://localhost:8000/docs

## 📄 许可证

与 DeepSeek-OCR 项目相同。

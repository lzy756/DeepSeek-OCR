## Context

DeepSeek-OCR 当前提供两种推理方式：
1. **vLLM 方式**（高性能生产）：通过 `LLM` 类加载模型，支持高并发（MAX_CONCURRENCY=100），吞吐量约 2500 tokens/s
2. **Transformers 方式**（研究原型）：通过 `AutoModel` 加载，提供 `infer()` 方法

API 服务需要桥接这两种推理引擎，优先使用 vLLM 以获得更好的并发性能。

### 现有组件
- **DeepseekOCRProcessor**: 图像预处理（tokenize_with_images）
- **NoRepeatNGramLogitsProcessor**: 防止重复的 logits 处理器
- **pdf_to_images_high_quality()**: PDF 转图像（DPI=144）
- **re_match()、extract_coordinates_and_label()**: 提取 grounding 坐标
- **draw_bounding_boxes()**: 绘制检测框

### 约束条件
- GPU 内存有限，需控制并发数量
- vLLM 使用 `VLLM_USE_V1=0`，禁用 V1 引擎
- CUDA 11.8 + Triton PTXAS 路径配置
- 模型最大长度 8192 tokens
- 图像尺寸限制需放宽 `Pillow.MAX_IMAGE_PIXELS`

## Goals / Non-Goals

### Goals
1. 提供生产级 RESTful API 服务，易于集成
2. 支持多种输入格式（base64、URL、multipart file）
3. 兼容所有现有 OCR 模式和分辨率配置
4. 异步处理长时间任务，提供任务状态查询
5. 良好的错误处理和用户反馈
6. 自动生成 API 文档（OpenAPI/Swagger）

### Non-Goals
- 不实现用户认证/授权（可作为后续扩展）
- 不实现持久化存储（任务结果仅内存缓存或临时文件）
- 不实现分布式部署（单节点服务）
- 不修改现有推理逻辑（仅封装）

## Decisions

### 1. 推理引擎选择
**决策**: 仅使用 vLLM（唯一后端）

**理由**:
- 项目已完成 vLLM 配置，可直接手动运行
- vLLM 提供生产级并发性能（PagedAttention）
- 无需支持 Transformers 模式（简化架构）
- 降低维护复杂度

**实现**:
```python
# api/services/vllm_service.py
# 直接初始化 vLLM，无需选择逻辑
from vllm import LLM, SamplingParams
llm = LLM(model=MODEL_PATH, ...)
```

### 2. 输入格式支持
**决策**: 支持三种输入方式
1. **Base64 编码**（JSON body）- 适合 Web 前端
2. **URL 下载**（JSON body）- 适合远程图像
3. **Multipart form-data**（文件上传）- 适合 curl/Postman

**理由**:
- 灵活适配不同客户端场景
- Base64 无需额外存储
- URL 支持云存储集成
- Multipart 符合 HTTP 规范

**实现**:
```python
# 三种方式合并到一个端点，通过 Union 类型区分
@router.post("/api/v1/ocr/image")
async def ocr_image(
    file: UploadFile = File(None),
    image_base64: str = Form(None),
    image_url: str = Form(None),
    # ...
)
```

### 3. 异步任务处理
**决策**: 内存队列 + 后台 worker（asyncio）

**理由**:
- PDF 大文件处理耗时长（可能数分钟）
- 避免 HTTP 超时（客户端等待过久）
- 简单场景下无需 Redis/Celery 复杂依赖

**架构**:
```
客户端 → POST /pdf/async → 返回 task_id
                ↓
         Task Queue (asyncio.Queue)
                ↓
         Background Worker → 执行推理
                ↓
         Task Store (dict) → 存储结果
                ↓
客户端 → GET /task/{task_id} → 查询状态/结果
```

**扩展路径**: 
- 生产环境可替换为 Celery + Redis
- 保持 API 接口不变

### 4. 响应格式设计
**决策**: ZIP 文件打包响应（主要）+ JSON 状态响应（辅助）

**同步 OCR 端点响应** (`/api/v1/ocr/image`, `/api/v1/ocr/pdf`):
- **Content-Type**: `application/zip`
- **响应体**: ZIP 压缩文件（二进制）
- **ZIP 文件结构**:
  ```
  result_<timestamp>.zip
  ├── result.mmd              # Markdown 格式的 OCR 结果（清理后）
  ├── result_ori.mmd          # 原始 OCR 输出（包含坐标标记）
  ├── result_with_boxes.jpg   # 标注框的可视化图像
  ├── images/                 # 提取的嵌入图像（如有）
  │   ├── 0.jpg
  │   ├── 1.jpg
  │   └── ...
  └── metadata.json           # 元数据信息
  ```

**metadata.json 内容**:
```json
{
  "model": "DeepSeek-OCR",
  "mode": "document_markdown",
  "resolution": "Gundam",
  "processing_time": 2.34,
  "timestamp": "2025-10-22T10:30:45Z",
  "input_info": {
    "type": "image",  // 或 "pdf"
    "pages": 1,       // PDF 页数
    "size": "1024x768"
  }
}
```

**异步任务状态响应** (`GET /api/v1/ocr/task/{task_id}`):
```json
{
  "task_id": "abc123",
  "status": "completed",  // pending, processing, completed, failed
  "progress": 1.0,
  "created_at": "2025-10-22T10:30:00Z",
  "completed_at": "2025-10-22T10:32:15Z",
  "download_url": "/api/v1/ocr/task/abc123/download"
}
```

**下载异步任务结果** (`GET /api/v1/ocr/task/{task_id}/download`):
- **Content-Type**: `application/zip`
- **响应体**: ZIP 文件（同上结构）

**错误响应** (JSON):
```json
{
  "detail": "Invalid image format"
}
```

**理由**:
1. **ZIP 打包优势**:
   - 客户端一次请求获取所有文件
   - 保持文件结构和关联关系
   - 自动压缩，减少传输大小
   - 兼容现有脚本输出逻辑
2. **直接返回 vs URL 下载**:
   - 同步端点直接返回 ZIP（小文件，快速响应）
   - 异步任务提供下载 URL（大文件，避免超时）
3. **metadata.json**:
   - 提供结构化信息（方便程序解析）
   - 避免客户端需要解析 Markdown
   - 记录处理参数（可追溯）

### 5. 并发控制
**决策**: 信号量限流 + vLLM 内置队列

**实现**:
```python
# api/services/vllm_service.py
class VLLMInferenceService:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self.llm = LLM(max_num_seqs=MAX_CONCURRENCY, ...)
    
    async def infer(self, ...):
        async with self.semaphore:
            # 调用 vLLM
```

**理由**:
- 保护 GPU 内存不溢出
- 请求排队而非拒绝（更好的用户体验）
- vLLM 内部已优化批处理

### 6. API Key 认证机制
**决策**: 支持多个 API KEY + 自动生成高强度密钥 + Header 认证

**密钥生成**:
```python
import secrets
# 生成 64 字符 URL 安全的随机字符串（256 位熵）
api_key = secrets.token_urlsafe(48)  # 48 字节 = 64 字符（base64）
```

**存储格式**（支持多个密钥）:
```
# APIKEY.keys（纯文本，每行一个密钥）
AbCdEfGh123456_IjKlMnOp789012-QrStUvWxYz345678_AbCdEfGh901234
XyZ987_MnOpQr654321-StUvWxYzAbCd987654_EfGhIjKl321098_DEFG
# 可手动添加更多密钥，空行和注释（#开头）会被忽略
```

**认证流程**:
1. 客户端在 Header 中携带：`X-API-Key: <key>`
2. 中间件拦截所有请求（除豁免端点）
3. 从 APIKEY.keys 读取所有有效密钥（每行一个）
4. 验证请求密钥是否在有效密钥列表中
5. 通过则继续，否则返回 401

**多密钥管理**:
- **自动生成**: 首次启动时自动生成第一个密钥
- **手动添加**: 直接编辑 APIKEY.keys 文件，每行添加一个新密钥
- **手动删除**: 从文件中删除对应行即可立即失效
- **密钥轮换**: 添加新密钥后再删除旧密钥，实现无缝切换
- **多客户端**: 为不同客户端/应用分配不同密钥，便于追踪和管理

**豁免端点**（无需认证）:
- `GET /health`
- `GET /health/ready`
- `GET /docs`
- `GET /redoc`
- `GET /openapi.json`

**安全考虑**:
- 使用 `secrets` 模块（加密安全的随机数生成器）
- 密钥长度 64 字符（约 10^115 种可能）
- 文件权限限制（chmod 600）
- 每次启动检查文件是否存在，不存在则生成首个密钥
- 支持注释行（#开头）和空行，便于管理

### 7. 配置管理
**决策**: 环境变量 + 默认值

**配置项**:
```python
# api/config.py
MODEL_PATH = os.getenv('MODEL_PATH', 'deepseek_ocr/')
MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', '100'))
BASE_SIZE = int(os.getenv('BASE_SIZE', '1024'))
IMAGE_SIZE = int(os.getenv('IMAGE_SIZE', '640'))
CROP_MODE = os.getenv('CROP_MODE', 'True').lower() == 'true'
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))
APIKEY_FILE = os.getenv('APIKEY_FILE', 'APIKEY.keys')
```

**理由**:
- 容器化部署友好
- 无需修改代码即可调整参数
- 保持与现有 config.py 一致

## Alternatives Considered

### 替代方案 1: 使用 Flask 而非 FastAPI
**优点**: 更成熟、生态更广
**缺点**: 
- 异步支持较弱（需要 Celery）
- 无自动 API 文档生成
- 类型验证需手动实现
**结论**: FastAPI 更适合现代异步场景

### 替代方案 2: gRPC 而非 RESTful
**优点**: 性能更高、类型安全
**缺点**: 
- 客户端集成复杂（需要 proto 文件）
- 不易调试（无法直接 curl）
- 浏览器支持差
**结论**: REST 更通用，适合初期

### 替代方案 3: Celery + Redis 任务队列
**优点**: 成熟的分布式任务队列
**缺点**: 
- 增加部署复杂度（需要 Redis）
- 对于单节点场景过度设计
**结论**: 先用内存队列，预留扩展接口

### 替代方案 4: JWT 认证而非 API Key
**优点**: 支持过期时间、用户信息嵌入
**缺点**: 
- 需要 Token 刷新机制
- 对于无状态服务过于复杂
- 需要用户注册/登录流程
**结论**: API Key 更简单，适合服务间调用

### 替代方案 5: 数据库存储 API Key
**优点**: 支持元数据（创建时间、用途、过期时间）、使用统计、细粒度权限
**缺点**: 
- 增加数据库依赖（PostgreSQL/MySQL/SQLite）
- 增加部署和维护复杂度
- 对于中小型场景过度设计
**结论**: 文件存储多密钥方案足够（已实现），后续可按需扩展为数据库

## Risks / Trade-offs

### 风险 1: 内存泄漏
**描述**: 长时间运行可能导致任务结果缓存占用过多内存
**缓解**: 
- 设置 TTL（任务完成后 1 小时自动清理）
- 最大缓存数量限制（LRU 淘汰）
- 可选写入文件系统

### 风险 2: 并发竞争
**描述**: 多个请求同时访问 vLLM 可能导致 GPU OOM
**缓解**:
- 信号量严格限流
- vLLM 的 `max_num_seqs` 配置
- 监控 GPU 内存使用

### 风险 3: 请求超时
**描述**: 大型 PDF 处理时间过长，HTTP 可能超时
**缓解**:
- 强制使用异步端点处理大文件（> 10 页）
- 同步端点设置合理超时（300s）
- 客户端轮询任务状态

### 风险 4: API Key 泄露
**描述**: APIKEY.keys 文件可能被意外暴露
**缓解**:
- 文件权限设置为 600（仅所有者可读写）
- 添加到 .gitignore（不提交到版本控制）
- 文档明确警告不要在公共环境暴露
- 支持通过环境变量 APIKEY_FILE 自定义路径

### 权衡: 功能 vs 简洁
- **权衡**: 不实现完整的任务持久化（仅内存缓存）
- **理由**: 保持架构简单，避免引入数据库
- **影响**: 服务重启会丢失任务历史，可接受（生产环境可扩展）

### 权衡: 文件存储 vs 数据库
- **权衡**: 使用文件存储多个 API Key（而非数据库）
- **理由**: 简化部署依赖，满足中小型场景
- **影响**: 无法记录每个密钥的元数据（创建时间、用途、使用统计等）
- **扩展**: 后续可扩展为数据库存储（支持元数据、细粒度权限、使用统计）

## Migration Plan

### 阶段 1: 基础服务（Milestone 1）
1. 实现核心 API 端点（image, pdf 同步）
2. vLLM 服务封装
3. 基础健康检查
4. **目标**: 功能可用，可本地运行

### 阶段 2: 异步支持（Milestone 2）
1. 任务队列实现
2. 异步 PDF 端点
3. 任务查询端点
4. **目标**: 支持长时间任务

### 阶段 3: 生产优化（Milestone 3）
1. Docker 镜像和编排
2. 错误处理完善
3. 日志和监控
4. **目标**: 可生产部署

### 回滚策略
- API 服务与现有脚本独立，出问题可直接使用命令行方式
- 不修改模型文件，无破坏性变更

## Open Questions

1. **问**: 是否需要支持流式响应（SSE）？
   **答**: 暂不需要，客户端可轮询任务状态。后续可添加 WebSocket 支持。

2. **问**: 如何处理超大 PDF（> 100 页）？
   **答**: 设置最大页数限制（默认 50 页），超过则拒绝或分批处理。

3. **问**: 是否需要支持自定义模型路径（多模型切换）？
   **答**: 暂不支持，单模型服务。后续可添加 `/models` 端点支持多模型。

4. **问**: 图像上传大小限制？
   **答**: 默认 20MB，通过 FastAPI 的 `max_file_size` 配置。

5. **问**: 是否需要支持 HTTPS？
   **答**: API 本身支持 HTTP，HTTPS 通过反向代理（Nginx/Traefik）配置。

6. **问**: API Key 如何更新/重置？
   **答**: 支持多种方式：
   - **添加新密钥**: 直接编辑 APIKEY.keys 文件，添加新行
   - **删除密钥**: 从文件中删除对应行（立即生效）
   - **重置所有密钥**: 删除 APIKEY.keys 文件，重启服务会自动生成新密钥
   - **密钥轮换**: 先添加新密钥，通知客户端切换后再删除旧密钥

7. **问**: 是否需要支持多个 API Key（多客户端）？
   **答**: **已支持**。APIKEY.keys 采用多行格式存储，每行一个密钥。可为不同客户端/应用分配独立密钥。

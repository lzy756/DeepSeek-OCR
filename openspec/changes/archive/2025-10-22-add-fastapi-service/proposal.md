# Add FastAPI Service

## Why
当前 DeepSeek-OCR 项目仅提供命令行脚本方式运行（run_dpsk_ocr_pdf.py、run_dpsk_ocr_image.py、run_dpsk_ocr_eval_batch.py），无法作为服务提供给其他应用调用。添加 FastAPI 服务可以：
1. 提供 RESTful API 接口，方便集成到其他系统
2. 支持并发请求处理，提高资源利用率
3. 标准化输入输出格式，降低使用门槛
4. 支持异步处理长时间任务（大型 PDF 文档）

## What Changes
- **新增** FastAPI 应用服务器和路由处理器
- **新增** 基于 vLLM 的推理服务封装（支持高并发）
- **新增** 统一的请求/响应数据模型
- **新增** 任务队列和异步处理机制（用于 PDF 批处理）
- **新增** 健康检查和模型状态监控端点
- **新增** API 文档（自动生成的 OpenAPI/Swagger 文档）
- **新增** 配置管理（环境变量 + 配置文件）
- **新增** API Key 认证中间件（支持多个 API KEY，自动生成高强度密钥）

## Impact
### 受影响的能力
- **新增能力**: `api-service` - RESTful API 服务层
- **复用现有**: vLLM 推理引擎 (DeepSeek-OCR-vllm/)
- **复用现有**: Transformers 推理引擎 (deepseek_ocr/)

### 受影响的代码
- **新增文件**:
  - `api/` - API 服务根目录
    - `main.py` - FastAPI 应用入口
    - `routers/` - API 路由模块
      - `ocr.py` - OCR 相关端点
      - `health.py` - 健康检查端点
    - `models/` - Pydantic 数据模型
      - `request.py` - 请求模型
      - `response.py` - 响应模型
    - `services/` - 业务逻辑层
      - `vllm_service.py` - vLLM 推理服务封装
      - `task_queue.py` - 异步任务队列
    - `middleware/` - 中间件
      - `auth.py` - API Key 认证中间件
    - `config.py` - API 配置管理
    - `utils/` - 工具函数
      - `image_utils.py` - 图像处理辅助函数
      - `pdf_utils.py` - PDF 处理辅助函数
      - `apikey_generator.py` - API Key 生成和管理
  - `.env.example` - 环境变量配置模板
  - `APIKEY.keys` - 自动生成的 API Key 存储文件（启动时创建，支持多行多密钥）
  - `docker/` - Docker 部署配置
    - `Dockerfile.api` - API 服务镜像
    - `docker-compose.yml` - 编排配置
- **更新文件**:
  - `requirements.txt` - 添加 FastAPI、uvicorn、python-multipart 等依赖

### 不影响的部分
- 现有命令行脚本保持不变，可独立使用
- 模型文件和权重无需修改
- vLLM 和 Transformers 推理逻辑保持独立

## API 功能设计

### 核心端点
1. **POST /api/v1/ocr/image** - 单图像 OCR（返回 ZIP）
2. **POST /api/v1/ocr/pdf** - PDF 文档 OCR（同步，返回 ZIP）
3. **POST /api/v1/ocr/pdf/async** - PDF 文档 OCR（异步，返回任务 ID）
4. **GET /api/v1/ocr/task/{task_id}** - 查询异步任务状态
5. **GET /api/v1/ocr/task/{task_id}/download** - 下载异步任务结果（返回 ZIP）
6. **GET /health** - 健康检查
7. **GET /api/v1/info** - 模型信息和配置

### 支持的 OCR 模式
- 基于现有 PROMPT 模板：
  - `document_markdown`: 文档转 Markdown（带布局）
  - `free_ocr`: 纯文本提取（无布局）
  - `figure_parse`: 图表解析
  - `grounding_ocr`: 带坐标的 OCR（grounding）
  - `custom`: 自定义 prompt

### 分辨率模式
- 支持所有现有模式：Tiny、Small、Base、Large、Gundam
- 通过请求参数指定：`base_size`、`image_size`、`crop_mode`

### 响应格式
- **同步端点**: 直接返回 ZIP 文件（`application/zip`）
- **异步端点**: 返回任务状态 JSON，完成后通过下载端点获取 ZIP
- **ZIP 内容**: `result.mmd`, `result_ori.mmd`, `result_with_boxes.jpg`, `images/`, `metadata.json`

## 技术选型理由
- **FastAPI**: 
  - 高性能异步框架
  - 自动 API 文档生成
  - 类型验证和序列化
  - 与 Pydantic 深度集成
- **vLLM 后端（唯一选择）**:
  - 项目已配置完成，可直接使用
  - 已有高并发支持（MAX_CONCURRENCY）
  - 生产级性能（~2500 tokens/s）
  - 内存优化（PagedAttention）
- **异步任务队列**:
  - 基于 asyncio + 内存队列（简单场景）
  - 可选 Celery + Redis（生产环境扩展）
- **API Key 认证**:
  - 使用 secrets 模块生成加密安全的随机密钥
  - 密钥长度 64 字符（256 位熵）
  - 支持多个 API KEY（APIKEY.keys 文件多行存储）
  - 启动时自动生成首个密钥并保存到 APIKEY.keys
  - 支持手动添加/删除密钥（编辑文件，每行一个密钥）
  - Header 认证方式：`X-API-Key: <key>`

## 非目标（本次不包括）
- 多用户系统和细粒度权限管理（后续添加）
- 速率限制和配额管理（后续添加）
- 模型热更新和版本管理（后续添加）
- 分布式部署和负载均衡（后续添加）
- 日志聚合和监控告警（后续添加）

## ADDED Requirements

### Requirement: HTTP API Server
系统 SHALL 提供基于 FastAPI 的 HTTP API 服务器，用于接收和处理 OCR 请求。

#### Scenario: 服务启动成功
- **WHEN** 管理员执行 `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- **THEN** 服务器应成功启动并监听指定端口
- **AND** 日志输出 "Application startup complete"
- **AND** vLLM 模型成功加载到 GPU 内存

#### Scenario: 服务健康检查
- **WHEN** 客户端发送 `GET /health` 请求
- **THEN** 返回 200 状态码
- **AND** 响应包含 `{"status": "healthy", "model_loaded": true}`

#### Scenario: 服务就绪检查
- **WHEN** 客户端发送 `GET /health/ready` 请求
- **THEN** 如果模型已加载，返回 200 状态码
- **AND** 如果模型未加载，返回 503 状态码

### Requirement: Single Image OCR
系统 SHALL 支持单张图像的 OCR 处理，接受多种输入格式，并返回 ZIP 文件。

#### Scenario: Base64 图像输入
- **WHEN** 客户端发送 POST 请求到 `/api/v1/ocr/image`
- **AND** 请求体包含 `{"image_base64": "...", "mode": "document_markdown"}`
- **THEN** 返回 200 状态码
- **AND** Content-Type 为 `application/zip`
- **AND** 响应体为 ZIP 文件（二进制数据）
- **AND** ZIP 文件名为 `result_<timestamp>.zip`

#### Scenario: 图像 URL 输入
- **WHEN** 客户端发送 POST 请求到 `/api/v1/ocr/image`
- **AND** 请求体包含 `{"image_url": "https://example.com/doc.jpg", "mode": "free_ocr"}`
- **THEN** 系统下载图像并执行 OCR
- **AND** 返回 ZIP 文件

#### Scenario: 文件上传输入
- **WHEN** 客户端使用 multipart/form-data 上传图像文件
- **AND** Content-Type 为 `image/jpeg` 或 `image/png`
- **THEN** 系统解析文件并执行 OCR
- **AND** 返回 ZIP 文件

#### Scenario: ZIP 文件内容验证
- **WHEN** 客户端解压 OCR 返回的 ZIP 文件
- **THEN** ZIP 包含以下文件：
  - `result.mmd` - Markdown 格式 OCR 结果（清理后）
  - `result_ori.mmd` - 原始 OCR 输出（含坐标标记）
  - `result_with_boxes.jpg` - 标注框可视化图像
  - `metadata.json` - 元数据信息
- **AND** 如果有 grounding 提取的图像，包含 `images/` 目录及图像文件

#### Scenario: metadata.json 内容
- **WHEN** 客户端解析 ZIP 中的 `metadata.json`
- **THEN** 包含以下字段：
  ```json
  {
    "model": "DeepSeek-OCR",
    "mode": "document_markdown",
    "resolution": "Gundam",
    "processing_time": 2.34,
    "timestamp": "2025-10-22T10:30:45Z",
    "input_info": {"type": "image", "size": "1024x768"}
  }
  ```

#### Scenario: 无效图像格式
- **WHEN** 客户端上传非图像文件（如 .txt）
- **THEN** 返回 400 状态码
- **AND** 错误信息为 `{"error": {"code": "INVALID_IMAGE_FORMAT", "message": "..."}}`

#### Scenario: 图像超过大小限制
- **WHEN** 客户端上传超过 20MB 的图像
- **THEN** 返回 413 状态码
- **AND** 错误信息提示大小限制

### Requirement: OCR Mode Selection
系统 SHALL 支持多种 OCR 模式，通过请求参数指定。

#### Scenario: 文档转 Markdown 模式
- **WHEN** 请求参数 `mode="document_markdown"`
- **THEN** 系统使用 prompt `"<image>\n<|grounding|>Convert the document to markdown."`
- **AND** 返回包含 Markdown 格式文本的响应
- **AND** 包含布局坐标信息（如存在）

#### Scenario: 纯文本 OCR 模式
- **WHEN** 请求参数 `mode="free_ocr"`
- **THEN** 系统使用 prompt `"<image>\nFree OCR."`
- **AND** 返回不含布局信息的纯文本

#### Scenario: 图表解析模式
- **WHEN** 请求参数 `mode="figure_parse"`
- **THEN** 系统使用 prompt `"<image>\nParse the figure."`
- **AND** 返回图表结构化描述

#### Scenario: 自定义 Prompt
- **WHEN** 请求参数 `mode="custom"` 且 `custom_prompt="<image>\nDescribe this image."`
- **THEN** 系统使用用户提供的 prompt
- **AND** 返回对应结果

### Requirement: Resolution Configuration
系统 SHALL 支持灵活的分辨率配置，兼容所有现有模式。

#### Scenario: Tiny 模式
- **WHEN** 请求参数 `{"base_size": 512, "image_size": 512, "crop_mode": false}`
- **THEN** 图像被调整为 512×512
- **AND** 使用 64 个视觉 tokens

#### Scenario: Gundam 动态分辨率
- **WHEN** 请求参数 `{"base_size": 1024, "image_size": 640, "crop_mode": true}`
- **THEN** 全局视图为 1024×1024
- **AND** 局部裁剪为 n×640×640
- **AND** 视觉 tokens 根据裁剪数量动态调整

#### Scenario: 默认配置
- **WHEN** 请求未指定分辨率参数
- **THEN** 使用默认配置（Base: 1024×1024）

### Requirement: PDF Document OCR
系统 SHALL 支持 PDF 文档的 OCR 处理，包括同步和异步模式，并返回 ZIP 文件。

#### Scenario: 小 PDF 同步处理
- **WHEN** 客户端上传不超过 10 页的 PDF 到 `/api/v1/ocr/pdf`
- **THEN** 系统同步处理所有页面
- **AND** 返回 ZIP 文件（application/zip）
- **AND** ZIP 包含合并的 `result.mmd`（所有页面，用 `<--- Page Split --->` 分隔）
- **AND** ZIP 包含 `images/` 目录（所有页面提取的图像，命名为 `{page}_{index}.jpg`）
- **AND** 处理时间在 60 秒内

#### Scenario: 大 PDF 异步处理
- **WHEN** 客户端上传超过 10 页的 PDF 到 `/api/v1/ocr/pdf/async`
- **THEN** 系统返回任务 ID：`{"task_id": "abc123", "status": "pending"}`
- **AND** HTTP 状态码为 202（Accepted）
- **AND** 后台开始处理任务

#### Scenario: 异步任务结果下载
- **WHEN** 客户端发送 `GET /api/v1/ocr/task/{task_id}/download`
- **AND** 任务已完成
- **THEN** 返回 ZIP 文件（application/zip）
- **AND** Content-Disposition header 包含文件名：`attachment; filename="result_{task_id}.zip"`

#### Scenario: PDF 转图像失败
- **WHEN** PDF 文件损坏或加密
- **THEN** 返回 400 状态码
- **AND** 错误信息说明 PDF 解析失败原因

### Requirement: Asynchronous Task Management
系统 SHALL 提供异步任务的创建、查询和管理功能。

#### Scenario: 创建异步任务
- **WHEN** 客户端提交异步 OCR 请求
- **THEN** 系统生成唯一任务 ID（UUID）
- **AND** 任务状态初始化为 "pending"
- **AND** 任务加入后台队列

#### Scenario: 查询任务状态（处理中）
- **WHEN** 客户端查询 `GET /api/v1/ocr/task/{task_id}`
- **AND** 任务正在处理
- **THEN** 返回 `{"task_id": "...", "status": "processing", "progress": 0.4}`

#### Scenario: 查询任务状态（已完成）
- **WHEN** 客户端查询已完成的任务
- **THEN** 返回 `{"task_id": "...", "status": "completed", "download_url": "/api/v1/ocr/task/.../download"}`
- **AND** 响应包含下载链接

#### Scenario: 查询任务状态（失败）
- **WHEN** 任务执行失败
- **THEN** 返回 `{"task_id": "...", "status": "failed", "error": {...}}`
- **AND** 错误信息包含失败原因

#### Scenario: 查询不存在的任务
- **WHEN** 客户端查询无效的任务 ID
- **THEN** 返回 404 状态码
- **AND** 错误信息为 "Task not found"

#### Scenario: 任务结果自动清理
- **WHEN** 任务完成超过 1 小时
- **THEN** 系统自动清理任务结果（释放内存）
- **AND** 后续查询返回 410 状态码（Gone）

### Requirement: Grounding Coordinate Extraction
系统 SHALL 提取 grounding 模式下的坐标信息，并保存到 ZIP 文件中。

#### Scenario: 提取文本坐标和可视化
- **WHEN** OCR 结果包含 `<|ref|>title<|/ref|><|det|>[[100, 200, 300, 400]]<|/det|>`
- **THEN** 系统在 `result_with_boxes.jpg` 绘制边界框
- **AND** 边界框标注类型（title、text、table 等）
- **AND** `result_ori.mmd` 保留原始坐标标记

#### Scenario: 提取嵌入图像
- **WHEN** OCR 结果包含 `<|ref|>image<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>`
- **THEN** 系统裁剪该区域图像
- **AND** 保存到 ZIP 的 `images/` 目录（命名为 `0.jpg`, `1.jpg` 等）
- **AND** `result.mmd` 中替换坐标标记为图像引用：`![](images/0.jpg)`

#### Scenario: 无 Grounding 信息
- **WHEN** 使用 `free_ocr` 模式（不包含坐标）
- **THEN** ZIP 不包含 `result_with_boxes.jpg`
- **AND** ZIP 不包含 `images/` 目录（除非 PDF 多页）

### Requirement: Model Information API
系统 SHALL 提供查询模型和配置信息的端点。

#### Scenario: 查询模型信息
- **WHEN** 客户端发送 `GET /api/v1/info`
- **THEN** 返回模型配置：
  ```json
  {
    "model_name": "DeepSeek-OCR",
    "model_path": "deepseek_ocr/",
    "inference_backend": "vllm",
    "max_concurrency": 100,
    "supported_modes": ["document_markdown", "free_ocr", "figure_parse", "grounding_ocr", "custom"],
    "supported_resolutions": ["Tiny", "Small", "Base", "Large", "Gundam"],
    "response_format": "application/zip",
    "version": "1.0.0"
  }
  ```

### Requirement: Error Handling
系统 SHALL 提供统一的错误处理和响应格式（JSON）。

#### Scenario: 验证错误
- **WHEN** 请求参数不符合 Pydantic 模型定义
- **THEN** 返回 422 状态码（Unprocessable Entity）
- **AND** Content-Type 为 `application/json`
- **AND** 错误信息包含具体字段验证失败原因

#### Scenario: 服务器内部错误
- **WHEN** vLLM 推理过程中出现异常
- **THEN** 返回 500 状态码
- **AND** Content-Type 为 `application/json`
- **AND** 错误响应包含通用错误信息（不暴露内部细节）
- **AND** 详细错误记录到日志

#### Scenario: 并发限流
- **WHEN** 当前请求数达到 MAX_CONCURRENCY
- **THEN** 新请求排队等待（不立即拒绝）
- **AND** 客户端收到延迟响应（但最终返回 ZIP）

#### Scenario: 临时文件清理
- **WHEN** OCR 处理完成并返回 ZIP 后
- **THEN** 系统自动清理临时输出目录
- **AND** 仅保留异步任务的结果（有 TTL）

### Requirement: API Documentation
系统 SHALL 自动生成交互式 API 文档。

#### Scenario: 访问 Swagger UI
- **WHEN** 用户访问 `/docs`
- **THEN** 显示 Swagger UI 界面
- **AND** 包含所有端点的描述和示例
- **AND** 支持在线测试 API

#### Scenario: 访问 ReDoc
- **WHEN** 用户访问 `/redoc`
- **THEN** 显示 ReDoc 格式的文档

#### Scenario: 导出 OpenAPI Schema
- **WHEN** 用户访问 `/openapi.json`
- **THEN** 返回完整的 OpenAPI 3.0 规范（JSON 格式）

### Requirement: Concurrent Request Handling
系统 SHALL 安全地处理并发请求，避免资源竞争。

#### Scenario: 并发单图像请求
- **WHEN** 10 个客户端同时发送图像 OCR 请求
- **THEN** vLLM 内部优化批处理
- **AND** 所有请求均成功返回结果
- **AND** 无 GPU 内存溢出

#### Scenario: 混合并发请求
- **WHEN** 同时处理 5 个图像请求和 2 个 PDF 请求
- **THEN** 系统根据信号量控制并发数
- **AND** 请求按队列顺序处理
- **AND** 吞吐量接近 2500 tokens/s

### Requirement: API Key Authentication
系统 SHALL 实现基于 API Key 的认证机制，保护所有业务端点。

#### Scenario: 首次启动自动生成 API Key
- **WHEN** 系统首次启动且 `APIKEY.keys` 文件不存在
- **THEN** 自动生成 64 字符高强度随机 API Key
- **AND** 将密钥保存到 `APIKEY.keys` 文件
- **AND** 控制台输出生成的密钥（供管理员获取）
- **AND** 日志记录："API Key generated and saved to APIKEY.keys"

#### Scenario: 使用现有 API Key 启动
- **WHEN** 系统启动且 `APIKEY.keys` 文件已存在
- **THEN** 从文件读取 API Key
- **AND** 不重新生成密钥
- **AND** 日志记录："Loaded API Key from APIKEY.keys"

#### Scenario: 携带正确 API Key 访问
- **WHEN** 客户端发送请求到业务端点（如 `/api/v1/ocr/image`）
- **AND** 请求 Header 包含 `X-API-Key: <valid_key>`
- **THEN** 认证通过，正常处理请求
- **AND** 返回业务响应

#### Scenario: 缺失 API Key
- **WHEN** 客户端发送请求到业务端点
- **AND** 请求 Header 不包含 `X-API-Key`
- **THEN** 返回 401 状态码
- **AND** 响应体为：`{"detail": "Missing API Key"}`

#### Scenario: 无效 API Key
- **WHEN** 客户端提供错误的 API Key
- **THEN** 返回 401 状态码
- **AND** 响应体为：`{"detail": "Invalid API Key"}`

#### Scenario: 健康检查端点豁免认证
- **WHEN** 客户端访问 `/health` 或 `/health/ready`
- **AND** 不携带 API Key
- **THEN** 正常返回健康状态（200 状态码）
- **AND** 不进行认证检查

#### Scenario: API 文档端点豁免认证
- **WHEN** 客户端访问 `/docs`、`/redoc` 或 `/openapi.json`
- **AND** 不携带 API Key
- **THEN** 正常返回文档内容
- **AND** 不进行认证检查

#### Scenario: API Key 文件权限保护
- **WHEN** 系统创建 `APIKEY.keys` 文件
- **THEN** 文件权限设置为 600（仅所有者可读写）
- **AND** 文件所有者为运行服务的用户

#### Scenario: API Key 密钥强度验证
- **WHEN** 生成 API Key
- **THEN** 密钥长度为 64 字符
- **AND** 使用 URL 安全的 Base64 编码字符集（A-Z, a-z, 0-9, -, _）
- **AND** 熵为 256 位（cryptographically secure）

### Requirement: Configuration Management
系统 SHALL 通过环境变量管理配置，支持容器化部署。

#### Scenario: 使用默认配置启动
- **WHEN** 未设置任何环境变量
- **THEN** 系统使用 `api/config.py` 中的默认值
- **AND** 模型路径为 `deepseek_ocr/`
- **AND** 端口为 8000
- **AND** API Key 文件路径为 `APIKEY.keys`

#### Scenario: 通过环境变量覆盖配置
- **WHEN** 设置 `MODEL_PATH=/custom/path` 和 `API_PORT=9000`
- **THEN** 系统加载自定义路径的模型
- **AND** 监听 9000 端口

#### Scenario: 自定义 API Key 文件路径
- **WHEN** 设置环境变量 `APIKEY_FILE=/secure/path/keys.txt`
- **THEN** 系统从该路径读取/生成 API Key

#### Scenario: 环境变量验证
- **WHEN** 环境变量 `MAX_CONCURRENCY=invalid`
- **THEN** 启动失败并提示配置错误

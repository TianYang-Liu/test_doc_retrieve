# SRS 文档 RAG 数据管道

基于公司内部 DeepSeek 模型的文档知识库，用于为已有 agent 提供检索接口，生成测试用例。

---

## 技术选型

### 为什么不用传统 RAG 切块？

传统 RAG 按固定 token 数切割文档，会把表格切断、把上下文割裂。本项目改用**结构化分层分块**：

- 按文档自然边界切（每张表格是一个完整 chunk，每个章节是一个完整 chunk）
- 检索用小块（精准匹配），送给 LLM 用大块（完整上下文）
- 超大章节按 heading 层级递归拆，不会切断表格

### PDF 解析：Docling

| 候选 | 结论 |
|---|---|
| pdfplumber / PyMuPDF | 表格识别弱，中文支持一般 |
| Camelot / Tabula | 只能提取表格，无法处理混合内容 |
| **Docling（选用）** | IBM 开源，表格识别最强，输出结构化 Markdown，原生支持中文，直接集成 LlamaIndex |

### 飞书文档解析：飞书开放平台 API

飞书支持将文档导出为 Markdown，结构天然保留（heading 层级、表格、代码块），无需额外解析。

### Embedding 模型：Qwen3-Embedding-0.6B

| 候选 | MTEB 多语言均分 | context window | 中文底座 |
|---|---|---|---|
| BGE-M3（570M） | ~56-58 | 8,192 tokens | 否 |
| **Qwen3-Embedding-0.6B（选用）** | **64.33** | **32,768 tokens** | **是（Qwen3）** |

选用原因：
- MTEB 多语言榜显著优于 BGE-M3
- 32k context window，一张大表格或完整章节可以直接放入，不截断
- 基于 Qwen3 训练，中英混合文档语义理解更准确
- 参数量 0.6B，CPU 可运行，内存占用约 2GB

### Reranker：Qwen3-Reranker-0.6B

与 Embedding 同系列，中英混合场景下重排精度最优，CPU 可运行。
检索 top-20，重排后取 top-5 送给 LLM，大幅提升精度。

### 向量数据库：Qdrant

| 候选 | 结论 |
|---|---|
| Chroma | 适合原型，生产不稳定 |
| Milvus | 适合亿级向量，部署复杂（依赖 etcd/Kafka），本项目规模不值得 |
| pgvector | 有 PostgreSQL 基础设施时可选，性能略低 |
| **Qdrant（选用）** | 单 Docker 容器，无额外依赖，支持 hybrid search，磁盘索引节省内存，百万级向量足够 |

本项目预估 chunk 数 50万～200万，Qdrant 完全覆盖，且运维成本最低。

### 框架：LlamaIndex

- 专为 RAG/文档检索设计，API 最简洁
- 原生支持 Docling NodeParser
- 原生支持 AutoMergingRetriever（parent-child 自动合并）
- 原生支持 DeepSeek（OpenAI 兼容接口）

### 依赖管理：uv

比 pip/poetry 更快，`pyproject.toml` 标准化管理，torch 通过 `sys_platform` marker 只在 Linux 服务器上安装。

---

## 项目结构

```
doc_rag/
├── pyproject.toml          # uv 依赖管理
├── config.py               # 所有配置项
├── main.py                 # 入口：ingest / query
├── data/
│   └── pdfs/               # 把 SRS PDF 放这里
├── storage/                # docstore 持久化（自动生成）
├── qdrant_data/            # Qdrant 数据（Docker 挂载）
├── ingest/
│   ├── pdf_loader.py       # Docling 解析 PDF
│   └── feishu_loader.py    # 飞书 API 拉取文档
└── pipeline/
    ├── chunker.py          # 分层分块
    ├── indexer.py          # embedding + 写入 Qdrant
    └── retriever.py        # 检索 + rerank
```

---

## 整体流程

```
PDF (Docling 解析，表格完整保留)  ──┐
                                    ├──> 分层分块 ──> Qwen3-Embedding-0.6B ──> Qdrant
飞书 API 导出 Markdown ─────────────┘

查询 ──> Qwen3-Embedding-0.6B ──> Qdrant 检索 top-20
     ──> AutoMerging（leaf 命中多时返回完整 parent）
     ──> Qwen3-Reranker-0.6B 重排 top-5
     ──> 返回节点列表给 agent
```

---

## 部署步骤

### 1. 环境要求

- Python 3.10+
- Docker
- Linux x86_64（生产环境）
- 无需 GPU

### 2. 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 启动 Qdrant

```bash
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

验证：
```bash
curl http://localhost:6333/healthz
```

管理界面：`http://localhost:6333/dashboard`

### 4. 安装依赖

```bash
uv sync
```

### 5. 配置

编辑 `config.py`：

```python
# 飞书应用凭证（飞书开放平台 -> 应用 -> 凭证与基础信息）
FEISHU_APP_ID     = "your-app-id"
FEISHU_APP_SECRET = "your-app-secret"

# 如果 Qdrant 不在本机，修改这里
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
```

在 `main.py` 中填入飞书文档 token：

```python
FEISHU_DOC_TOKENS = [
    "your-feishu-doc-token-1",  # URL 中 /docx/<token> 部分
]
```

### 6. 放入 PDF

将 SRS PDF 文件放入 `./data/pdfs/` 目录。

### 7. 建立索引（首次运行）

```bash
uv run python main.py ingest
```

首次运行会自动下载 Qwen3-Embedding-0.6B 和 Qwen3-Reranker-0.6B 模型（约 2-3GB），之后不再重复下载。

### 8. 查询测试

```bash
uv run python main.py query 用户登录模块的错误码定义
uv run python main.py query 支付流程的异常处理逻辑
```

---

## 对接 Agent

`main.py` 中的 `cmd_query()` 返回节点列表，直接传给 agent：

```python
from main import cmd_query

results = cmd_query("用户登录模块的错误码")
for node in results:
    print(node.get_content())       # 文本内容
    print(node.metadata["source"])  # 来源文件
    print(node.metadata["type"])    # "pdf" 或 "feishu"
    print(node.score)               # 相关性分数
```

---

## 注意事项

- 数据全部在本地，不经过任何外部服务（飞书 API 除外，用于拉取文档）
- Qdrant 数据存储在 `./qdrant_data/`，docstore 存储在 `./storage/`，定期备份这两个目录
- 文档更新后重新运行 `uv run python main.py ingest` 即可增量更新
- 模型文件默认缓存在 `~/.cache/huggingface/`，如需离线部署，提前下载到内网服务器

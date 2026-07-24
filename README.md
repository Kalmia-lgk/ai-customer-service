# 🤖 AI 智能客服系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688?logo=fastapi)
![LlamaIndex](https://img.shields.io/badge/RAG-LlamaIndex-8A2BE2)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-fb8c00)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1c3c3c)
![License](https://img.shields.io/badge/License-MIT-green)

**基于 RAG + Agent 架构的现代化 AI 智能客服平台**

</div>

---

## 📖 项目简介

AI 智能客服系统是一个**全栈 Web 应用**，结合了 **RAG（检索增强生成）** 和 **AI Agent** 技术，能够基于用户上传的知识库文档提供智能问答。系统支持流式对话、多轮会话管理、文档知识库管理、真转人工工单，并提供客服端 + 管理端双 UI。

### 适用场景

- 企业内部知识库客服
- 产品使用手册智能问答
- FAQ 自动化回复
- 技术支持知识库

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 💬 **智能对话** | 基于 RAG 的知识库问答，流式 SSE 实时输出 |
| 📚 **知识库管理** | PDF/DOCX/TXT/Markdown/CSV 上传与向量索引 |
| 🔍 **语义检索** | ChromaDB 向量相似度搜索，带来源引用与评分 |
| 🤖 **Agent 工作流** | LangGraph：意图识别 → 检索 → 生成 |
| 🎧 **真转人工** | WebSocket 实时通信 + 工单队列 |
| 🔐 **认证系统** | JWT + 角色权限（超管/管理员/客服） |
| ⚙️ **管理后台** | 工单、知识库、会话、统计、API 配置在线修改 |
| 🎨 **双端 UI** | 客服端 + 管理端，暗色模式 + 响应式 |
| 🔌 **多 LLM 支持** | OpenAI / Anthropic / Groq / 硅基流动 SiliconFlow |

---

## 🚀 快速开始

### 方式一：双击启动（推荐）

直接双击项目根目录下的 **`AI智能客服系统.exe`**：

1. 自动检查 Python 环境、安装缺失依赖、释放 8000 端口
2. 启动后端服务，弹出控制面板窗口（含实时日志）
3. 自动打开 **客户端** 和 **管理端** 两个应用窗口

> 说明：exe 是启动器，电脑上需要安装 Python 3.12+（首次运行会自动安装依赖）。

### 方式二：命令行启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制并编辑配置（填入 API Key）
copy .env.example .env

# 3. 启动服务
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 方式三：Docker

```bash
docker-compose up -d
```

### 访问地址

| 界面 | 地址 |
|------|------|
| 客户端 | http://localhost:8000 |
| 管理端 | http://localhost:8000/admin （默认账号 `admin@aicc.com` / `admin123`） |
| API 文档 | http://localhost:8000/api/docs |
| 健康检查 | http://localhost:8000/api/health |

---

## 🔧 配置说明

### LLM 提供商（.env 中配置，也可在管理后台在线修改）

```ini
# 硅基流动（国内推荐，对话 + Embedding 共用一个 Key）
LLM_PROVIDER=siliconflow
SILICONFLOW_API_KEY=sk-xxx
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V4-Flash
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-m3

# 或 OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-xxx
# OPENAI_MODEL=gpt-4o-mini

# 或 Groq（免费额度）
# LLM_PROVIDER=groq
# GROQ_API_KEY=gsk_xxx
```

没有配置任何有效 Key 时自动进入 **Demo 模式**（模拟回复，UI 功能全部可用）。

### RAG 知识库参数

```ini
CHUNK_SIZE=512       # 文档分块大小（tokens）
CHUNK_OVERLAP=50     # 块之间的重叠量
RETRIEVAL_TOP_K=4    # 检索时返回的相关文档数
```

Embedding 自动跟随提供商选择：硅基流动用 `BAAI/bge-m3`，OpenAI 用 `text-embedding-3-small`，也可用 `EMBEDDING_*` 变量显式覆盖。

---

## 📁 项目结构

```
AI客服系统/
├── AI智能客服系统.exe          # 🖱️ 双击启动（图形化启动器）
├── launcher.py                 # 启动器源码（PyInstaller 打包用）
│
├── backend/                    # 📦 后端服务
│   └── app/
│       ├── main.py             # FastAPI 应用入口
│       ├── core/               # 配置中心 / LLM 客户端 / 认证
│       ├── schemas/            # Pydantic 数据模型
│       ├── routers/            # API 路由（聊天/文档/客户/管理/WebSocket）
│       ├── services/           # 业务层（会话/文档/工单/用户/设置）
│       ├── rag/                # RAG 引擎（摄取/检索/Embedding）
│       └── agents/             # LangGraph Agent 工作流
│
├── static/                     # 🎨 客户端 UI
├── static-admin/               # ⚙️ 管理端 UI
│
├── uploads/                    # 📤 上传的知识库文件
├── chroma_db/                  # 🗄️ ChromaDB 向量数据
├── data/                       # 💾 运行时数据（用户/工单/设置）
│
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
├── Dockerfile / docker-compose.yml
└── README.md
```

---

## 📡 核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/customer/chat` | 客户流式聊天（SSE） |
| `POST` | `/api/customer/escalate` | 请求转人工 |
| `POST` | `/api/documents/upload` | 上传知识库文档 |
| `POST` | `/api/documents/reindex` | 重建全部向量索引 |
| `POST` | `/api/admin/login` | 管理端登录 |
| `GET/POST` | `/api/admin/settings*` | 查看/修改系统配置 |
| `GET` | `/api/health` | 健康检查（含 RAG 状态） |

完整接口见 Swagger：http://localhost:8000/api/docs

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| RAG 引擎 | LlamaIndex（解析/分块）+ ChromaDB（向量库） |
| Embedding | OpenAI 兼容接口（硅基流动 bge-m3 / OpenAI） |
| Agent | LangGraph |
| LLM | OpenAI / Anthropic / Groq / 硅基流动 |
| 认证 | JWT (python-jose) + bcrypt |
| 前端 | 原生 HTML/CSS/JS + marked.js + highlight.js |
| 打包 | PyInstaller（图形化启动器 exe） |

---

## 📄 License

MIT License - 自由使用、修改和分发

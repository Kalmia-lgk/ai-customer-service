# 🤖 AI 智能客服系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![LlamaIndex](https://img.shields.io/badge/RAG-LlamaIndex-8A2BE2)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-fb8c00)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1c3c3c)
![License](https://img.shields.io/badge/License-MIT-green)

**基于 RAG + Agent 架构的现代化 AI 智能客服平台**

<<<<<<< HEAD
=======
[功能特性](#-功能特性) · [快速开始](#-快速开始) · [项目架构](#-项目架构) · [API 文档](#-api-文档) · [扩展建议](#-后续扩展建议)

>>>>>>> 5ecf2ea (🎉 AI 智能客服系统 v2.0 — RAG + Agent 全栈客服平台)
</div>

---

## 📖 项目简介

<<<<<<< HEAD
AI 智能客服系统是一个**全栈 Web 应用**，结合了 **RAG（检索增强生成）** 和 **AI Agent** 技术，能够基于用户上传的知识库文档提供智能问答。

## ✨ 核心功能
=======
AI 智能客服系统是一个**全栈 Web 应用**，结合了 **RAG（检索增强生成）** 和 **AI Agent** 技术，能够基于用户上传的知识库文档提供智能问答。系统支持流式对话、多轮会话管理、文档知识库管理，并提供专业美观的现代化 UI 界面。

### 适用场景
- 企业内部知识库客服
- 产品使用手册智能问答
- FAQ 自动化回复
- 技术支持知识库

---

## ✨ 功能特性

### 🎯 核心功能
>>>>>>> 5ecf2ea (🎉 AI 智能客服系统 v2.0 — RAG + Agent 全栈客服平台)

| 功能 | 说明 |
|------|------|
| 💬 **智能对话** | 基于 RAG 的知识库问答，流式 SSE 实时输出 |
<<<<<<< HEAD
| 📚 **知识库管理** | PDF/DOCX/TXT/Markdown/CSV 上传与索引 |
| 🔍 **语义检索** | ChromaDB 向量相似度搜索 |
| 🤖 **Agent 工作流** | LangGraph：意图识别 → 检索 → 生成 |
| 🎧 **真转人工** | WebSocket 实时通信 + 工单队列 |
| 🔐 **认证系统** | JWT + RBAC + 多方式登录 |
| ⚙️ **管理后台** | 工单管理 + 知识库管理 + 统计面板 |
| 🎨 **双端 UI** | 客服端 + 管理端，暗色模式 + 响应式 |

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 启动（Demo 模式无需 API Key）
python run.py --demo

# 或双击 start.bat
```

访问 http://localhost:8000

## 🐳 Docker

```bash
docker-compose up -d
```

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| RAG 引擎 | LlamaIndex + ChromaDB |
| Agent | LangGraph |
| 数据验证 | Pydantic v2 |
| LLM | OpenAI / Anthropic / Groq |

## 📄 License

MIT License
=======
| 📚 **知识库管理** | 支持 PDF/DOCX/TXT/Markdown/CSV 文件上传与索引 |
| 🔍 **语义检索** | 基于 ChromaDB 的向量相似度搜索，关联度评分 |
| 🤖 **Agent 工作流** | LangGraph 驱动：意图识别 → 知识检索 → 回复生成 |
| 📝 **多轮会话** | 会话持久化、历史管理、上下文记忆 |
| 🎧 **转人工** | 一键模拟转接人工客服流程 |

### 🎨 前端体验

| 特性 | 说明 |
|------|------|
| 🌓 **深色/浅色模式** | 一键切换，自适应系统主题 |
| 📱 **响应式设计** | 适配桌面端、平板和手机 |
| ✨ **Markdown 渲染** | 支持标题、列表、加粗、代码块等富文本 |
| 🎨 **代码高亮** | highlight.js 自动语法着色 |
| 🔗 **来源引用** | 展示检索到的知识来源及相关度评分 |
| 🏗️ **玻璃拟态 UI** | 现代化毛玻璃效果，简洁大气 |

### 🛠️ 工程化

| 特性 | 说明 |
|------|------|
| 🐳 **Docker 部署** | 一键容器化启动 |
| ⚙️ **多 LLM 支持** | OpenAI / Anthropic / Groq 灵活切换 |
| 📐 **Pydantic v2** | 全类型标注，数据校验 |
| 📝 **模块化架构** | routers/services/rag/agents 分层清晰 |
| 🔒 **安全校验** | 文件类型与大小双重校验 |

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- （可选）Docker & Docker Compose

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd ai-customer-service
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，填入你的 API Key
# 至少要配置一个 LLM 提供商
```

```ini
# 选择 LLM 提供商（三选一即可）
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# 或使用 Groq（免费额度）
# LLM_PROVIDER=groq
# GROQ_API_KEY=gsk_your_key_here
```

### 3. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 启动服务

```bash
# 方式一：直接启动
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 方式二：使用主入口脚本
cd backend
python app/main.py
```

### 5. 打开浏览器

访问 **http://localhost:8000** 即可使用

- 前端界面: http://localhost:8000
- API 文档 (Swagger): http://localhost:8000/api/docs
- API 文档 (ReDoc): http://localhost:8000/api/redoc
- 健康检查: http://localhost:8000/api/health

### 🐳 Docker 部署

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

---

## 📁 项目架构

```
ai-customer-service/
│
├── backend/                        # 📦 后端服务
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口
│   │   ├── core/                   # ⚙️ 核心配置
│   │   │   ├── config.py           # Pydantic Settings 全局配置
│   │   │   └── llm_client.py       # 多 LLM 客户端工厂（OpenAI/Anthropic/Groq）
│   │   ├── schemas/                # 📋 Pydantic 数据模型
│   │   │   └── models.py           # 请求/响应 Schema 定义
│   │   ├── routers/                # 🛣️ API 路由层
│   │   │   ├── chat.py             # 聊天相关接口 (SSE 流式)
│   │   │   └── documents.py        # 文档管理接口
│   │   ├── services/               # 🏗️ 业务服务层
│   │   │   ├── chat_service.py     # 聊天业务逻辑 + 会话管理
│   │   │   └── document_service.py # 文档校验/存储/索引编排
│   │   ├── rag/                    # 🧠 RAG 知识库引擎
│   │   │   ├── ingestion.py        # 文档摄取管道（加载→分块→Embedding→入库）
│   │   │   └── retrieval.py        # 语义检索器（查询→向量搜索→结果组装）
│   │   └── agents/                 # 🤖 AI Agent
│   │       └── customer_agent.py   # LangGraph 工作流（意图分类→检索→生成）
│   └── requirements.txt            # Python 依赖清单
│
├── static/                         # 🎨 前端静态文件
│   ├── index.html                  # 单页面应用入口
│   ├── css/
│   │   └── style.css               # 全局样式（含浅色/深色主题变量）
│   └── js/
│       ├── app.js                  # 应用初始化 + 主题管理 + 全局工具
│       ├── chat.js                 # 聊天核心（SSE 流式、会话管理、Markdown）
│       └── documents.js            # 知识库管理（上传、列表、删除、重建）
│
├── uploads/                        # 📤 上传文件存储目录
├── chroma_db/                      # 🗄️ ChromaDB 向量数据持久化
│
├── Dockerfile                      # 🐳 Docker 镜像
├── docker-compose.yml              # 🐳 Docker Compose 编排
├── .env.example                    # 🔐 环境变量模板
├── .gitignore
├── requirements.txt                # 📦 项目依赖
└── README.md                       # 📖 项目文档
```

### 架构设计

```
用户浏览器 (SSE)
    │
    ▼
┌─────────────────────────────────────────┐
│               FastAPI 服务               │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │ Routers │→│ Services │→│   RAG   │ │
│  │ (API层) │  │ (业务层) │  │ (引擎) │ │
│  └─────────┘  └──────────┘  └────────┘ │
│                      │          │        │
│                      ▼          ▼        │
│               ┌──────────┐ ┌──────────┐ │
│               │  Agent   │ │ ChromaDB │ │
│               │(LangGraph)│ │(向量库) │ │
│               └──────────┘ └──────────┘ │
└─────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   ┌──────────┐                 ┌──────────┐
   │  LLM API │                 │ Embedding│
   │(OpenAI/  │                 │  Model   │
   │Anthropic/│                 └──────────┘
   │  Groq)   │
   └──────────┘
```

### 聊天请求处理流程

```
用户消息 → Agent 意图分类
              ├── greeting/general_chat → 直接 LLM 回复
              ├── escalation → 转人工流程
              └── knowledge_query → RAG 检索
                                        │
                                        ▼
                                   ChromaDB 向量搜索
                                        │
                                        ▼
                                   组装上下文 + System Prompt
                                        │
                                        ▼
                                   LLM 流式生成 (SSE)
                                        │
                                        ▼
                                   返回给前端 (逐 token)
```

---

## 📡 API 文档

### 聊天接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | 流式聊天（SSE），支持 session_id |
| `GET` | `/api/sessions` | 获取所有会话列表 |
| `GET` | `/api/sessions/{id}` | 获取会话详情（含历史消息） |
| `DELETE` | `/api/sessions/{id}` | 删除会话 |

**流式事件类型：**

```javascript
// SSE 事件格式
event: session       → {"session_id": "uuid"}
event: thinking      → {"content": "🔍 正在检索..."}
event: sources       → {"sources": [{...}]}
data: {"content": "回答内容 token..."}  // 默认 message 事件
event: done          → {}
event: error         → {"content": "错误信息"}
```

### 知识库接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/documents/upload` | 上传文档（multipart/form-data） |
| `GET` | `/api/documents` | 文档列表 |
| `GET` | `/api/documents/{id}` | 文档详情 |
| `DELETE` | `/api/documents/{id}` | 删除文档（含向量+文件） |
| `POST` | `/api/documents/reindex` | 重建全部索引 |
| `GET` | `/api/documents/stats/summary` | 知识库统计 |

### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/docs` | Swagger UI |
| `GET` | `/api/redoc` | ReDoc |

---

## 🔧 配置说明

### LLM 提供商切换

在 `.env` 中修改 `LLM_PROVIDER` 即可切换：

```bash
# 使用 OpenAI（推荐 gpt-4o-mini，性价比高）
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini

# 使用 Anthropic Claude
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# 使用 Groq（免费额度，推荐 llama-3.3-70b）
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxx
GROQ_MODEL=llama-3.3-70b-versatile
```

### Embedding 模型

目前默认使用 OpenAI 的 `text-embedding-3-small`，后续可扩展支持其他嵌入模型。

### 分块参数

```bash
CHUNK_SIZE=512       # 文档分块大小（tokens）
CHUNK_OVERLAP=50     # 块之间的重叠量
RETRIEVAL_TOP_K=4    # 检索时返回的相关文档数
```

---

## 🚧 后续扩展建议

### 短期扩展（1-2 周）

- [ ] **数据库持久化**: 使用 PostgreSQL + SQLAlchemy 替代 JSON 文件存储会话
- [ ] **用户认证**: JWT + OAuth2 实现多用户登录
- [ ] **Embedding 扩展**: 支持本地模型（如 BGE、M3E）降低 API 成本
- [ ] **更多文件格式**: 支持 HTML、EPUB、图片 OCR
- [ ] **对话导出**: 导出聊天记录为 PDF/Markdown

### 中期扩展（1-3 月）

- [ ] **多知识库**: 支持创建多个独立知识库并切换
- [ ] **Agent 工具调用**: Function Calling 集成外部 API（订单查询、工单系统等）
- [ ] **意图分析仪表盘**: 统计常见问题、知识库覆盖度
- [ ] **反馈闭环**: 用户对回答的满意度评价，自动优化
- [ ] **语音交互**: 集成 TTS/STT 实现语音客服
- [ ] **多语言支持**: i18n 国际化

### 长期扩展（3+ 月）

- [ ] **真正的转人工**: 集成企业微信/钉钉/飞书等 IM 平台
- [ ] **多模态 RAG**: 支持图片/表格/图表理解
- [ ] **知识图谱**: Neo4j 构建企业知识图谱
- [ ] **A/B 评测**: 自动评估不同 Prompt/模型效果
- [ ] **微调模型**: 基于客服对话数据 Fine-tune
- [ ] **生产级部署**: Kubernetes + 负载均衡 + 监控告警

---

## 🛠️ 技术栈详情

| 层级 | 技术 | 版本 |
|------|------|------|
| **后端框架** | FastAPI | 0.115+ |
| **RAG 框架** | LlamaIndex | 0.12+ |
| **向量数据库** | ChromaDB | 0.6+ |
| **Agent 框架** | LangGraph | 0.3+ |
| **数据验证** | Pydantic | v2 |
| **配置管理** | pydantic-settings | 2.7+ |
| **前端样式** | CSS3 (自定义变量 + 玻璃拟态) | - |
| **Markdown** | marked.js | 14.1+ |
| **代码高亮** | highlight.js | 11.10+ |
| **字体** | Inter (Google Fonts) | - |
| **LLM API** | OpenAI / Anthropic / Groq SDK | 最新 |

---

## 📝 开发指南

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制并编辑配置
cp .env.example .env

# 3. 启动开发服务器（热重载）
cd backend && python -m uvicorn app.main:app --reload --port 8000

# 4. 前端可直接编辑 static/ 目录下的文件，刷新浏览器即可看到效果
```

### 添加新的 LLM 提供商

1. 在 `backend/app/core/config.py` 中添加配置项
2. 在 `backend/app/core/llm_client.py` 中添加 `_stream_xxx()` 方法
3. 在 `match self.provider` 分支中添加路由

### 代码规范

- 后端：遵循 PEP 8，使用 `from __future__ import annotations`
- 所有函数添加类型标注
- 使用 Pydantic v2 进行数据校验
- 中文注释 + docstring
- 前端：ES6+ 模块化，事件驱动架构

---

## 📄 License

MIT License - 自由使用、修改和分发

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！**

Made with ❤️ by AI Engineering

</div>
>>>>>>> 5ecf2ea (🎉 AI 智能客服系统 v2.0 — RAG + Agent 全栈客服平台)

# 🤖 AI 智能客服系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![LlamaIndex](https://img.shields.io/badge/RAG-LlamaIndex-8A2BE2)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-fb8c00)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-1c3c3c)
![License](https://img.shields.io/badge/License-MIT-green)

**基于 RAG + Agent 架构的现代化 AI 智能客服平台**

</div>

---

## 📖 项目简介

AI 智能客服系统是一个**全栈 Web 应用**，结合了 **RAG（检索增强生成）** 和 **AI Agent** 技术，能够基于用户上传的知识库文档提供智能问答。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 💬 **智能对话** | 基于 RAG 的知识库问答，流式 SSE 实时输出 |
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

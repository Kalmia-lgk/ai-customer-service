# AI 智能客服系统 v3

基于 **RAG + LangGraph Agent** 的全栈智能客服平台：客户端聊天页 + 管理后台 + 桌面启动器，共用一个 FastAPI 后端。

> v3 为全栈重做版本：聊天链路由真正的 LangGraph 状态图驱动，业务数据落 SQLite，LLM 配置在线热更新。设计文档见 `docs/重做方案v2.md`。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| Agent 驱动对话 | LangGraph 四节点状态图（意图识别 → 检索 / 转人工 / 闲聊 → 生成），意图由 LLM 结构化输出判断 |
| Agent 步骤可视化 | 前端实时显示 Agent 走到哪一步（识别意图 › 检索知识库 › 生成回答） |
| RAG 知识库 | PDF / DOCX / TXT / Markdown / CSV 上传，自动分块 + bge-m3 向量化，回答附引用与相关度 |
| 智能转人工 | 说"给我个活人"这类无关键词的表达也能被语义识别，自动创建工单 |
| 实时工单 | WebSocket 双向对话：客服接管 → 回复 → 解决，状态实时同步访客端 |
| 数据可靠 | 会话 / 消息 / 工单 / 用户全部落 SQLite（`data/app.db`），重启不丢；访客按 visitor_id 隔离 |
| 配置热更新 | 管理端在线修改 LLM API 配置，下一条对话立即生效，无需重启 |
| 双端 UI | 零构建原生前端 + 共享设计令牌，深浅色主题，断网可用（无 CDN 依赖） |

## 快速开始

### 方式一：双击启动器

双击 `AI智能客服系统.exe`（需已安装 Python 3.12+，首次运行自动装依赖），启动后自动打开客户端与管理端窗口。

### 方式二：命令行

```bash
pip install -r requirements.txt
copy .env.example .env      # 填入 LLM_API_KEY（硅基流动等 OpenAI 兼容厂商）
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| 界面 | 地址 |
|------|------|
| 客户端 | http://localhost:8000 |
| 管理端 | http://localhost:8000/admin/（首个注册账号自动成为超级管理员） |
| API 文档 | http://localhost:8000/api/docs |

## 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| Web | FastAPI + Uvicorn | SSE 流式 + WebSocket |
| 数据 | SQLite + SQLModel | 单文件零安装，SQL 思维与 MySQL 通用 |
| 向量库 | ChromaDB | 余弦相似度检索，本地持久化 |
| Agent | LangGraph | 状态图编排，`/api/chat` 的处理链路本体 |
| LLM | openai SDK 单通路 | OpenAI 兼容接口（硅基流动 / DeepSeek / OpenAI 换 base_url 即用） |
| 文档处理 | pypdf + python-docx + langchain-text-splitters | 轻量组合 |
| 认证 | PyJWT + bcrypt | 两级角色：super_admin / agent |
| 前端 | 原生 HTML/CSS/JS（ES Module） | 零构建，marked + DOMPurify 本地化 |

## 项目结构

```
AI客服/
├─ backend/app/
│  ├─ main.py            # 应用装配（lifespan 初始化全局单例）
│  ├─ config.py          # .env 配置与路径
│  ├─ db.py  models.py   # SQLite 引擎 + SQLModel 表模型
│  ├─ schemas.py         # 请求/响应校验模型
│  ├─ security.py        # bcrypt + PyJWT
│  ├─ llm.py             # LLMGateway：全局唯一 LLM 出口（热更新）
│  ├─ rag/               # loader 解析 / pipeline 分块入库 / store Chroma 封装
│  ├─ agent/             # LangGraph 状态图 + 提示词
│  ├─ routers/           # chat / auth / documents / tickets / admin / ws
│  └─ services/          # 会话 / 工单 / 运行时配置 / WS 连接管理
├─ static/               # 客户端 UI
├─ static-admin/         # 管理端 UI（hash 路由单页）
├─ static-shared/        # 共享设计令牌 + 本地化第三方库（挂载 /assets）
├─ scripts/
│  ├─ reset_data.py      # 清空业务数据（保留账号）
│  ├─ reset_password.py  # 重置管理端账号密码
│  ├─ smoke_test.py      # 后端端到端冒烟测试
│  ├─ full_check.py      # 交付前全功能浏览器验收
│  └─ ui_check.py / admin_ui_check.py   # Playwright UI 自动化走查
├─ data/app.db           # 运行时数据库（gitignore）
├─ chroma_db/  uploads/  # 向量库 / 知识库原文件
└─ launcher.py           # 桌面启动器（PyInstaller 打包源码）
```

## 核心 API 与 SSE 契约

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 聊天（SSE 流式，Agent 驱动） |
| GET | `/api/sessions` | 会话列表（visitor_id 隔离） |
| POST | `/api/customer/escalate` | 手动转人工 |
| POST | `/api/auth/login` | 管理端登录 |
| POST | `/api/documents/upload` | 上传知识库文档 |
| PUT | `/api/admin/settings` | 修改 LLM 配置（保存即热生效） |
| WS | `/ws/admin` `/ws/customer/{ticket_id}` | 工单实时推送 |

`/api/chat` 的 SSE 事件：`session`（会话 ID）→ `agent_step`（Agent 进度）→ `sources`（引用）/ `ticket`（自动建单）→ 无名事件（流式 token）→ `done`。

## 测试

```bash
# 先启动服务，然后：
python scripts/smoke_test.py        # 后端全链路（RAG / Agent 三分支 / 工单 / 隔离）
python scripts/ui_check.py          # 客户端 UI 走查（需本机 Edge）
python scripts/admin_ui_check.py    # 管理端 + 双端实时联动走查
```

## License

MIT

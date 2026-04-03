# A Story Teller / 智能故事生成系统 (Alpha 2.5)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

**A Story Teller** 是一个以角色为中心、多视角协同创作、具备全链路持久化能力的智能故事生成系统。它不仅能生成故事，更能模拟一个由多名“演员”组成的剧组，在不同的故事题材中进行深度演绎。

---

## 🌟 核心特性

### 1. 🎭 演员扮演架构 (Roleplay Engine)
*   **角色与背景解耦**：角色不再是剧本的附属品，而是拥有独立“演员设定”（身高、性格、语调）的实体。
*   **动态身份适配**：演员入驻《都市侦探》或《冰风之行》时，会根据自身本性自动演化出对应的职业技能与剧情目标。
*   **关系网编织**：系统自动推演演员间的社交矩阵（信任、竞争、暗流），使多视角叙事具备真实的人际张力。

### 2. ⚡ 高性能异步流水线 (Async Pipeline)
*   **全异步架构**：基于 LangGraph Async 构建，消除 I/O 阻塞。
*   **并行生成加速**：多名角色的视角叙事采用并发调用，在大模型推理吞吐允许的情况下，效率较原型提升 400%。

### 3. 💾 工业级持久化保险丝 (Persistence)
*   **节点级快照**：内置 `AsyncSqliteSaver`。生成过程中的每一步（大纲、适配、视角、整合）都会自动保存。
*   **无畏中断**：如遇停电或模型崩溃，通过相同的 `Thread ID` 重新启动，系统将秒级找回进度并继续创作。

### 4. 🧠 记忆蒸馏与 RAG (Smart Memory)
*   **增量索引技术**：基于 SHA-256 哈希校验，仅索引变更内容，彻底解决冷启动时的预处理耗时。
*   **精准语境召回**：通过 `story_id` 元数据过滤，确保角色在不同剧本间拥有清晰的记忆边界。

---

## 🛠️ 技术栈

| 模块 | 选型 |
| :--- | :--- |
| **调度内核** | LangGraph (Async StateGraph) |
| **模型推理** | Ollama (本地私有化部署) |
| **向量检索** | ChromaDB (原生加速核心) |
| **数据模型** | Pydantic V2 (强类型校验) |
| **前端交互** | Flet (响应式三栏布局) |
| **底层通信** | HTTPX (全链路异步) |

---

## 🚀 快速开始

### 1. 环境安装
```bash
git clone https://github.com/luoli0706/A_Stroy_Teller.git
cd A_Stroy_Teller
pip install -r requirements.txt
```

### 2. 启动推理引擎
确保本地 [Ollama](https://ollama.com/) 已启动，并拉取所需模型：
```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

### 3. 运行应用
```bash
# 启动 UI 界面
python UI/flet_app.py

# 或运行自动化测试脚本产出故事
python -m unittest tests/test_v025_integration.py
```

---

## 📂 项目结构
```text
├── app/                # 核心逻辑 (图编排、LLM客户端、RAG引擎)
├── UI/                 # 组件化表现层
├── stories/            # 故事框架模板库
├── role/               # 演员通用设定集
├── memory/             # 角色跨剧本长期记忆
├── opt/                # 最终故事与归档产物
└── docs/               # 详细的技术与功能演进历史
```

## 📝 开发者说明
本系统处于 Alpha 阶段，初期测试显示在 **逻辑一致性** 与 **多视角碰撞** 上具有显著优势。欢迎参与 UGC 演员设定或故事框架的贡献。

## 许可证
Apache License 2.0

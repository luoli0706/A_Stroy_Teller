# A Story Teller / 智能故事生成系统 (Alpha 2)

A Story Teller 是一个以角色为中心、多视角协同、支持持久化续写的智能故事生成系统。基于 LangGraph + Ollama + ChromaDB 构建。

## 🌟 核心特性

- **多视角并行叙事**：采用全异步并发架构，多名角色同时撰写各自视角，效率提升 400%。
- **演员扮演机制 (Actor-Slot Mapping)**：角色以“通用演员”身份入驻故事框架，根据大纲自动适配职业、目标与社交关系。
- **持久化断点续写**：内置 Checkpointer 机制。若生成中断（断电、超时），通过 Thread ID 即可秒级恢复进度。
- **高效增量 RAG**：基于 SHA-256 哈希的增量索引技术，支持毫秒级海量记忆检索。
- **结构化质检系统**：强制模型输出 JSON 格式质检报告，自动识别逻辑冲突并提供修正建议。
- **全链路类型安全**：基于 Pydantic V2 构建系统状态机，确保数据流转万无一失。

## 🛠️ 技术栈

- **编排框架**: [LangGraph](https://github.com/langchain-ai/langgraph) (Async StateGraph)
- **大模型引擎**: [Ollama](https://ollama.com/) (本地部署)
- **向量数据库**: [ChromaDB](https://www.trychroma.com/) (原生 C++ 核心加速)
- **数据校验**: [Pydantic V2](https://docs.pydantic.dev/)
- **UI 框架**: [Flet](https://flet.dev/) (Flutter for Python)
- **通信协议**: 全链路异步 [HTTPX](https://www.python-httpx.org/)

## 🚀 快速开始

1. **环境准备**:
   - 确保安装了 Python 3.10+。
   - 安装依赖: `pip install -r requirements.txt`。
   - 启动本地 Ollama 服务并拉取模型 (如 `qwen3.5:9b`, `nomic-embed-text`)。

2. **启动应用**:
   ```bash
   python UI/flet_app.py
   ```

3. **断点续写说明**:
   - 在 UI 中输入自定义的 `Thread ID`。
   - 任务执行时，系统会为每个节点保存快照。
   - 如遇中断，使用相同 `Thread ID` 重新点击生成，系统将自动跳过已完成节点。

## 📂 项目结构

- `app/`: 核心逻辑、图编排、LLM 客户端。
- `UI/`: 组件化前端界面。
- `memory/`: 角色的长期记忆切片。
- `stories/`: 故事框架与角色槽位定义。
- `Reviewer/`: 深度架构评估与蓝图。
- `tests/`: 自动化集成测试。

## 📝 版本记录

详见 `docs/code_history.md` (代码演进) 与 `docs/func_history.md` (功能迭代)。

## 许可证

Apache License 2.0

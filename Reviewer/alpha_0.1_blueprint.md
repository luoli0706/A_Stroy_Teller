# A Story Teller Alpha 0.1 版本蓝图

## 1. 版本目标
Alpha 0.1 版本的核心目标是实现“工程化底座的重构”，解决原型阶段遗留的性能瓶颈与架构耦合问题，为后续的功能扩展提供稳定的基础设施。

**核心指标：**
- **性能**：多角色生成耗时降低 40% 以上（通过并行实现）。
- **架构**：消除核心业务逻辑与 UI 的直接依赖。
- **效率**：RAG 检索耗时降低至毫秒级（通过原生查询实现）。
- **可维护性**：配置项统一管理，路径规范化。

## 2. 核心任务清单

### 2.1 配置与存储中心化 (Centralized Config & Storage)
- [ ] 创建 `app/config.py`，统一管理环境变量、模型参数及文件路径。
- [ ] 优化存储结构：
    - `memory/{role_id}/` 仅存放持久化记忆。
    - `opt/stories/{story_id}/` 按故事归档生成结果（Markdown/JSON）。
    - `.data/` 存放 SQLite 和向量库。

### 2.2 RAG 引擎重构 (Efficient RAG)
- [ ] 移除 `chroma_memory.py` 中的手动余弦相似度计算。
- [ ] 改为使用 `collection.query()` 原生接口，利用 ChromaDB 内部索引。
- [ ] 优化 Embedding 过程，支持批量向量化。

### 2.3 异步与并发增强 (Concurrency & Async)
- [ ] 将 `app/llm_client.py` 改造为支持异步调用（使用 `httpx` 或 LangChain Async 接口）。
- [ ] 在 `generate_role_views` 节点引入 `asyncio.gather`，实现多角色视角并行生成。
- [ ] 确保 LangGraph 的运行环境支持异步执行。

### 2.4 UI 逻辑解耦 (UI Decoupling)
- [ ] 将 `UI/flet_app.py` 中的组件（Page, Section）拆分为独立的 Python 类。
- [ ] I18N 文本提取至外部配置文件或独立的定义模块。
- [ ] UI 仅作为状态的呈现者，业务逻辑由 `app/runtime.py` 调度。

### 2.5 库方法替换 (Library Optimization)
- [ ] 统一使用 `httpx` 替换 `urllib` 手写调用。
- [ ] 规范化 LangChain 组件的使用方式，减少低级手写代码。

## 3. 存储结构优化方案
```text
E:\Projects\A_Story_Teller\
├── .data/                  # 持久化数据（db, vector）
├── app/
│   ├── config.py           # 中心化配置 [NEW]
│   └── ...
├── memory/
│   └── {role_id}/          # 角色记忆切片
├── stories/
│   └── {story_id}/
│       └── framework.md    # 故事框架定义
└── opt/                    # 输出归档
    └── stories/
        └── {story_id}/     # 按故事 ID 分类存储生成的切片和最终成文
```

## 4. 后续评估计划
开发完成后，将生成：
1. **Alpha 0.1 性能与稳定性评估**：重点对比优化前后的耗时与资源占用。
2. **Alpha 0.1 架构鲁棒性评估**：评估解耦后的代码维护成本与扩展潜力。

# Phase 10: Real Toy Repair

## 组件边界

Phase 10 的目标是确认真实 Gemini 可以驱动 OpenCAI 已有的通用 Agent Loop 完成 toy project 修复闭环。

Agent Loop 负责：

- 保存 task 内部的 messages。
- 调用 LLM Adapter。
- 执行模型选择的工具调用。
- 把工具结果转成下一轮 observation。
- 从 `run_command` 结果生成 `verification` event。
- 维护 step budget。

Agent Loop 不负责：

- 写死 `run_command -> read_file -> apply_patch` 的修复顺序。
- 判断具体 bug 应该怎么修。
- 直接依赖 Gemini SDK 对象。
- 做权限拦截。

真实 Gemini 负责根据 observation 决定下一步工具调用；Tool Model 负责实际执行工具；Renderer 只展示 events。

## Reference Pass

本轮参考问题：

```text
真实 function calling 模型如何和本地工具执行形成多轮修复闭环？
```

参考结论：

- Gemini function calling 的工具执行由应用侧负责。
- 应用执行工具后，需要把 function response 传回模型。
- 模型可以基于上一轮工具结果继续选择下一个工具或输出最终答案。

OpenCAI 采用：

- 继续使用现有 `GeminiAdapter` 的 provider-neutral message 翻译。
- 继续让 LLM 决定工具顺序。
- 通过 CLI `--max-steps` 给真实 repair loop 足够 step budget。

OpenCAI 暂不采用：

- 专用 repair demo 入口。
- 把 bugfix 策略写死进 `agent_loop.py`。
- 引入新框架或 workflow runtime。

## 最小接口变化

Runtime 新增 CLI 参数：

```text
--max-steps N
```

默认值仍是 `3`。一次性 task 和交互式 task 都会把该值传给 `run_agent_loop(...)`。

这个参数属于 Runtime 配置，不改变 Agent Loop 协议、Tool Model 协议或 GeminiAdapter 协议。

## 验证闭环

Phase 10 使用临时失败态验证：

```python
def add(a, b):
    return a - b
```

真实 Gemini 执行路径：

```text
run_command
-> verification failed
-> read_file
-> apply_patch
-> run_command
-> verification passed
-> final_answer
```

修复后文件回到正确状态：

```python
def add(a, b):
    return a + b
```

## 已验证

- `python -m py_compile OpenCAI\__main__.py`
  - exit code `0`
  - 验证 Runtime 参数改动语法可编译。

- `python -m OpenCAI --dry-run --max-steps 8`
  - exit code `0`
  - dry-run 输出包含 `max_steps: 8`。

- 临时失败态下运行 `python -m unittest discover examples/toy_project`
  - exit code `1`
  - 失败原因为 `AssertionError: -1 != 3`。

- 真实 Gemini repair loop：

```text
python -m OpenCAI --adapter gemini --max-steps 8 --task "Fix the failing unittest in examples/toy_project. First run: python -m unittest discover examples/toy_project. Then inspect the relevant file with read_file or search_files, apply the smallest patch, rerun the same unittest command, and only give a final answer after the unittest passes."
```

  - exit code `0`
  - 事件流包含 `verification failed -> read_file -> apply_patch -> verification passed -> final_answer`。

- `python -m unittest discover examples/toy_project`
  - exit code `0`
  - 验证 toy project 修复后测试通过。

## 下一步

Phase 11：加入最小权限层，把模型提出的写文件和命令执行请求，与 Runtime 是否允许执行分开。

# LLM Providers

## 当前状态

OpenCAI 的普通 Agent Loop 仍只接收一个已选定的 `LLMAdapter`。多 provider / 多 model 的选择、注册和配置属于 Runtime 层，不下沉到 `agent_loop.py`。

默认启动只注册 `fake/fake`。真实 provider 不再内置任何硬编码 model；用户必须通过 `/model-add` 或 `.opencai/models.json` 配置后才能出现在 `/model` 选择器里。

## 数据流

```text
/model-add
  -> choose provider
  -> configure API key
  -> discover models when provider supports it
  -> choose or enter model
  -> save .env key
  -> save .opencai/models.json profile
  -> register profile in RuntimeSession.model_registry

/model
  -> list session.model_registry.profiles()
  -> set RuntimeSession.active_model_id
  -> resolve adapter through ModelManager
  -> pass adapter to iter_agent_loop(...)
```

## ModelProfile

`ModelProfile.id` 使用用户可见的 `provider/model` reference，例如：

```json
{
  "id": "openai/gpt-dynamic",
  "provider": "openai",
  "model": "gpt-dynamic",
  "label": "OpenAI gpt-dynamic",
  "api_key_env": "OPENAI_API_KEY",
  "base_url": "https://api.openai.com/v1"
}
```

配置文件可以省略 `id`；加载时会从 `provider` 和 `model` 推导出 `provider/model`。

## Provider 和 Adapter

Provider 不等于 Adapter。Provider 表示用户配置的服务商或 endpoint；Adapter 表示 OpenCAI 到某类 API 协议的翻译器。多个 provider 可以复用同一个 adapter。

当前映射：

```text
fake                  -> FakeLLMAdapter
google                -> GeminiAdapter
gemini                -> GeminiAdapter   # 兼容旧配置
openai                -> OpenAICompatibleAdapter
deepseek              -> OpenAICompatibleAdapter
glm                   -> OpenAICompatibleAdapter
openai-compatible     -> OpenAICompatibleAdapter
anthropic             -> AnthropicAdapter
ollama                -> OllamaAdapter
```

## Model Discovery

`/model-add` 会优先动态拉取 provider 当前可用 models：

```text
google            -> Gemini models endpoint
openai            -> GET /models
anthropic         -> GET /v1/models
deepseek          -> GET /models
glm               -> GET /models on BigModel-compatible endpoint
openai-compatible -> GET /models on custom base_url
ollama            -> GET /api/tags
```

如果 discovery 失败，Runtime 会提示错误，并允许用户输入 custom model。代码不维护“最新 model 常量”；真实 model 名称应来自 provider API 或用户输入。

## Runtime Commands

- `/model-add`：配置 provider、API key 和 model，写入 `.env` 与 `.opencai/models.json`。
- `/model`：只显示当前已注册 profiles，不显示未配置的真实 provider 默认项。
- `/model provider/model`：切换到已注册 profile。
- `/model-test`：对当前 active profile 运行 no-tool smoke check。

## 文件边界

- `.env`：保存 API key，例如 `OPENAI_API_KEY`、`GEMINI_API_KEY`、`GLM_API_KEY`。
- `.opencai/models.json`：保存 provider / model / base_url / api_key_env，不保存真实 key。
- `OpenCAI/model_discovery.py`：动态拉取 provider model list。
- `OpenCAI/model_setup.py`：provider 默认 endpoint、key env 和 profile 构造。
- `OpenCAI/adapter_factory.py`：把 `ModelProfile` 转成具体 `LLMAdapter`。
- `OpenCAI/model_manager.py`：Runtime profile registry 和 lazy adapter cache。

## 后续

- 改进 `/model-add` 的长列表搜索和 label 展示。
- 支持 provider alias，例如 `openrouter/...`、`litellm/...`、`work-openai/...`。
- 真实 provider smoke 验证。
- 暂缓 model options / effort，等主线 setup 稳定后再加 Runtime-level options。

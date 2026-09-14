# Browser Agent

一个基于 BrowserGym 的文本型浏览器智能体。项目首先使用 DOM / Accessibility
Tree 构建紧凑页面表示，在 MiniWoB 上跑通动作闭环，随后接入 LLM ReAct 与显式规划，
最终迁移到 WebArena。

## 当前范围

M1（BrowserGym 基础环境）已经完成：

- 类型化浏览器动作与严格参数校验
- BrowserGym 环境的统一 `reset` / `step` 接口
- Accessibility Tree 到紧凑文本观察的转换
- 硬编码 MiniWoB `click-test` 冒烟示例
- 单元测试与代码质量配置

M2 已进入开发并提供可运行的基础 ReAct 闭环：

- OpenAI Responses API 文本输入/输出适配器
- 显式禁用 Web Search、Computer Use、MCP 和函数工具
- `Task + Observation + Action History` 状态构建
- 单动作严格 JSON 解析与页面元素 ID 校验
- 无效决策重试、最大步数和环境错误保护
- 奖励、步数和 token 使用量记录

显式 Planner 仍属于 M3。

## 环境准备

项目支持 Python 3.11 或 3.12。PowerShell 示例：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,llm]"
python -m playwright install chromium
```

MiniWoB 还需要本地网页资源。按照 BrowserGym 的 MiniWoB 设置说明检出固定版本的
`miniwob-plusplus`，并将 `.env.example` 中的 `MINIWOB_URL` 设置为网页目录的绝对
`file://` URL。运行前将该变量加载到当前 shell。

## 验证

无需启动浏览器的快速检查：

```powershell
python -m pytest
python -m ruff check .
```

完成 Chromium 和 MiniWoB 设置后运行 M1 冒烟任务：

```powershell
python -m benchmark.run_miniwob --task click-test --headless
```

脚本读取任务目标，在页面树中定位目标按钮，并通过项目的统一动作接口完成点击。

## 运行 M2 ReAct Agent

先在当前 PowerShell 中设置 API 凭据和模型：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_MODEL = "your-model-name"
```

运行 MiniWoB 任务：

```powershell
python -m benchmark.run_react --task click-test --headless
```

观察真实浏览器并放慢每一步：

```powershell
python -m benchmark.run_react `
  --task click-test `
  --no-headless `
  --step-delay 2 `
  --pause-on-finish
```

模型没有被授予任何外部工具。它只能读取项目生成的文本页面状态并返回 JSON 动作；
所有网页操作都由本项目的 BrowserGym 环境执行。

## 目录结构

```text
agent/       Agent、Planner、Prompt 与动作解析（M2/M3）
browser/     Environment、Observation、Actions（M1）
llm/         在线模型客户端接口（M2）
benchmark/   MiniWoB 与后续 WebArena 入口
configs/     运行配置
tests/       无浏览器依赖的单元测试
```

详细路线见 [browser_agent_development_plan.md](browser_agent_development_plan.md)。

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

M2（LLM 驱动的 ReAct 闭环）已经完成：

- 通用 LLM 文本输入/输出接口，以及 OpenAI、DeepSeek 适配器
- 显式禁用 Web Search、Computer Use、MCP 和函数工具
- `Task + Observation + Action History` 状态构建
- 单动作严格 JSON 解析与页面元素 ID 校验
- checkbox 等控件状态的紧凑表示
- 决策/API 重试、停滞检测、最大步数和环境错误保护
- 可复现的多任务、多 seed 批量评测与完整失败轨迹
- 奖励、步数、token 和可选 API 成本记录

DeepSeek 基线在 6 个代表性 MiniWoB 任务、每个 5 个 seed 上达到 `30/30`；详细配置与
逐任务指标见 [M2_BASELINE.md](benchmark/M2_BASELINE.md)。

M3（轻量显式 Planner）已经完成：

- 严格 JSON 的 `Plan`、`PlanStep` 与 `PlanState`
- 初始高层计划生成与 `completed/current/pending` 进度维护
- Planner只指导目标层，现有 ReAct Agent继续负责单个浏览器动作
- 可配置计划复核间隔，非致命更新失败保留旧计划继续执行
- 计划状态、warning 与 Planner token 纳入 benchmark 轨迹

规划模式在选定的多步任务上达到 `6/6`，最长成功轨迹为 5 步。结果及与 Direct ReAct
的对照见 [M3_BASELINE.md](benchmark/M3_BASELINE.md)。下一阶段为 M4 WebArena。

## 环境准备

项目支持 Python 3.11 或 3.12。PowerShell 示例：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,llm]"
python -m playwright install chromium
```

复制本地配置模板：

```powershell
Copy-Item .env.example .env
```

之后直接编辑仓库根目录的 `.env`，填入 `MINIWOB_URL`、所选模型及对应 API Key。
两个运行命令都会自动加载该文件，不需要每次打开终端重新设置。已经在终端或系统中设置的
环境变量优先级更高，不会被 `.env` 覆盖。`.env` 和 `.env.*` 已被 Git 忽略，只有不含
密钥的 `.env.example` 会进入版本控制。

MiniWoB 还需要本地网页资源。按照 BrowserGym 的 MiniWoB 设置说明检出固定版本的
`miniwob-plusplus`，并将 `.env` 中的 `MINIWOB_URL` 设置为网页目录的绝对
`file://` URL。

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

当前支持 `openai` 与 `deepseek`。OpenAI 配置示例：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_MODEL = "your-model-name"
```

DeepSeek 使用官方 OpenAI 兼容端点，配置示例：

```powershell
$env:DEEPSEEK_API_KEY = "your-api-key"
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"
python -m benchmark.run_react --provider deepseek --task click-test --headless
```

也可以用通用变量选择提供商与模型：

```powershell
$env:LLM_PROVIDER = "deepseek"
$env:LLM_MODEL = "deepseek-v4-flash"
python -m benchmark.run_react --task click-test --headless
```

命令行 `--provider` / `--model` 优先于环境变量。DeepSeek 地址默认是
`https://api.deepseek.com`，也可通过 `DEEPSEEK_BASE_URL` 覆盖。

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

## 批量验证 M2

默认套件覆盖单击、文本输入、下拉选择、复选框、顺序点击和登录表单：

```powershell
python -m benchmark.run_miniwob_suite --seeds 0
```

先用少量任务验证配置：

```powershell
python -m benchmark.run_miniwob_suite `
  --tasks click-test enter-text login-user `
  --seeds 0 1 `
  --max-steps 20
```

批量 runner 默认串行运行，避免并发 API 调用影响复现和限流。每次运行会在
`artifacts/miniwob/<UTC时间>/` 生成：

- `episodes.jsonl`：每个 episode 的完整动作轨迹和错误
- `episodes.csv`：便于表格分析的逐任务指标
- `summary.json`：成功率、平均步数、平均 token 和终止原因
- `run_config.json`：任务、seed、模型和运行参数

任务失败默认会继续测试剩余 case；使用 `--fail-fast` 可在首次失败时停止，使用
`--fail-on-task-failure` 可令存在失败时返回非零退出码。批量测试会产生多次 API 调用，
建议先从单个 seed 和少量任务开始。

使用 `--planning` 可启用 M3 高层计划与进度更新，同时保持原有低层动作接口不变：

```powershell
python -m benchmark.run_miniwob_suite `
  --tasks login-user click-checkboxes `
  --seeds 0 `
  --planning `
  --headless
```

默认情况下，供应商请求或空响应会额外重试 1 次，并以 1 秒为初始退避时间；连续 3 次
执行相同动作且页面没有变化时，episode 会以 `stalled_repeated_action` 停止，避免无效
消耗 token。可分别使用 `--llm-retries`、`--llm-retry-delay` 和
`--max-stalled-repeats` 调整，后者设为 `0` 可关闭停滞保护。

如需估算 API 成本，请从供应商当前价格页取得每百万 token 单价并同时传入：

```powershell
python -m benchmark.run_miniwob_suite `
  --tasks click-test enter-text `
  --seeds 0 `
  --input-cost-per-million <输入单价> `
  --output-cost-per-million <输出单价>
```

价格不会硬编码在仓库中；估算值会写入每个 episode 和 `summary.json`。缓存 token、
批量折扣等供应商特有计价可能造成实际账单与估算值不同。

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

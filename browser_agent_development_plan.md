# Browser Agent 开发方案

## 1. 项目目标

构建一个能够在真实浏览器环境中，根据自然语言任务自主规划、调用浏览器动作，并依据页面反馈连续执行多步骤任务的 Browser Agent。

第一阶段聚焦 **DOM / Accessibility Tree 驱动的文本型 Browser Agent**，不把视觉理解、长期记忆、多 Agent、复杂反思等扩展能力纳入主要开发目标。

核心技术路线：

- 开发环境：BrowserGym + MiniWoB
- 最终 Benchmark：BrowserGym + WebArena
- 浏览器：Chromium / Playwright
- LLM：在线 API
- Agent：自行实现
- 页面表示：结构化 DOM / Accessibility Tree
- 基础范式：Observation → Reason / Plan → Action → Observation

---

## 2. 核心能力

### 2.1 Browser Environment

负责浏览器交互与状态获取，包括：

- 启动和重置浏览器环境
- 获取当前 URL
- 获取 DOM / Accessibility Tree
- 提取可交互元素
- 执行浏览器动作

第一版支持以下动作：

```text
click(element_id)
type(element_id, text)
scroll(direction)
select(element_id, option)
navigate(url)
go_back()
finish(message)
```

BrowserGym 负责底层浏览器环境封装，项目自身只实现统一的 Environment / Action Interface。

---

### 2.2 Page Representation

将网页转换为适合 LLM 消费的紧凑文本状态。

示例：

```text
Task:
Find a MacBook under $1000.

Current URL:
https://example.com

Interactive Elements:
[12] textbox "Search"
[13] button "Search"
[21] link "MacBook Air"
[22] link "MacBook Pro"
```

第一版不直接向 LLM 提供完整 HTML，而是优先保留：

- 当前 URL
- 页面标题
- 可交互元素
- 元素类型
- 元素文本 / aria label
- 必要的局部页面文本

目标是减少无关 token，同时保留完成任务所需的信息。

---

### 2.3 ReAct Agent

Agent 输入：

```text
Task
+ Current Observation
+ Action History
```

Agent 输出：

```text
Thought / Reason
Action
```

典型循环：

```text
Observation
    ↓
Reason
    ↓
Action
    ↓
Browser Environment
    ↓
New Observation
    ↓
...
```

第一版不实现复杂的多 Agent 架构。

---

### 2.4 Explicit Planning

在基础 ReAct Agent 跑通后，引入简单的显式任务规划，以支持更长的任务链路。

示例：

```text
Goal:
Buy the highest-rated headphones under $100.

Plan:
1. Search headphones
2. Set price filter
3. Inspect results
4. Compare ratings
5. Open best result
6. Add to cart
```

执行过程中维护：

```text
Completed:
1. Search headphones
2. Set price filter

Current:
3. Inspect results
```

Planner 负责维护高层目标，Action Agent 负责根据当前页面决定下一步浏览器动作。

---

## 3. 系统架构

```text
                User Task
                    │
                    ▼
                 Planner
                    │
                    ▼
            Action Decision
                    │
                    ▼
             Browser Executor
                    │
                    ▼
             Browser Environment
                    │
                    ▼
              Observation
                    │
                    └──────────→ Agent Loop
```

第一版保持单 Agent 结构。

---

## 4. 开发里程碑

### Milestone 1：BrowserGym 基础环境

目标：跑通 BrowserGym，并通过代码完成固定网页任务。

实现：

- BrowserGym 环境初始化
- Observation 获取
- 可交互元素解析
- click / type / scroll / select / navigate
- 环境 step / reset

完成标准：

```text
Python 程序可以在 MiniWoB 中通过硬编码动作完成一个固定任务。
```

---

### Milestone 2：基础 ReAct Browser Agent

状态：已完成（2026-09-14）。选定的 6 个 MiniWoB 任务 × 5 个 seed 基线为
`30/30`，详见 [`benchmark/M2_BASELINE.md`](benchmark/M2_BASELINE.md)。

目标：接入 LLM，实现自主浏览器操作闭环。

实现：

- LLM Client
- Prompt
- Observation → Action
- Action Parser
- Agent Loop
- Action History
- finish 动作

完成标准：

```text
给定未硬编码的 MiniWoB 自然语言任务，
Agent 可以自主连续执行浏览器动作直至完成任务。
```

---

### Milestone 3：多步骤任务与显式 Planning

目标：提高较长任务中的目标保持能力。

实现：

- Task Planner
- Plan State
- Completed / Current Step 管理
- Planner 与 Action Agent 的联合执行

完成标准：

```text
Agent 可以根据自然语言目标生成多步骤 Plan，
并基于页面状态持续执行和更新任务进度。
```

---

### Milestone 4：迁移 WebArena

目标：在更接近真实网页的环境中完成多页面、多步骤任务。

重点覆盖：

- Shopping
- GitLab
- Forum / Wiki 等典型网站
- 页面跳转
- 搜索与筛选
- 多页面信息关联
- 长轨迹任务

完成标准：

```text
在选定的一批 WebArena 任务上，
Agent 能够稳定完成部分真实风格的多步骤网页任务，
并形成正式 Benchmark 结果。
```

---

## 5. Benchmark 与核心指标

第一阶段使用：

```text
MiniWoB
```

最终使用：

```text
WebArena
```

主要记录：

- Task Success Rate
- Average Steps
- Average Token Usage
- Average API Cost

主要比较版本：

```text
V0: Direct ReAct
V1: ReAct + Simplified Page Representation
V2: Explicit Planning
```

核心验证问题：

> 随任务链路变长，结构化网页表示和显式规划是否能够提升任务完成率，并减少无效操作。

---

## 6. 推荐代码结构

```text
browser-agent/
│
├── agent/
│   ├── agent.py
│   ├── planner.py
│   ├── prompt.py
│   └── parser.py
│
├── browser/
│   ├── environment.py
│   ├── observation.py
│   └── actions.py
│
├── llm/
│   └── client.py
│
├── benchmark/
│   ├── run_miniwob.py
│   └── run_webarena.py
│
├── configs/
│
├── main.py
├── AGENTS.md
└── README.md
```

---

## 7. 第一阶段非目标

以下能力暂不纳入主要开发目标：

- Screenshot / VLM 页面理解
- Multi-Agent
- 长期 Memory
- 复杂 Reflection
- 自动 Skill Library
- RL
- OS-level Computer Use
- Browser + Coding 跨环境 Agent
- 并行 Agent

这些能力仅作为后续扩展方向，是否加入取决于第一版 Agent 的真实 failure case。

---

## 8. 预期最终成果

项目完成后应具备：

1. 一个可运行的 Browser Agent
2. 一套统一浏览器动作接口
3. DOM / Accessibility Tree 页面表示
4. ReAct-style 多步执行能力
5. 显式任务规划能力
6. MiniWoB 开发结果
7. WebArena Benchmark 结果

项目可概括为：

> 基于 BrowserGym 构建自主 Web Agent，通过结构化网页感知、LLM 任务规划与浏览器工具调用完成多步骤网页任务，并在 MiniWoB 与 WebArena 上验证长链路任务执行能力。

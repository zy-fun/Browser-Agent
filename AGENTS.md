# AGENTS.md

## Project Overview

This repository implements a **Browser Agent** that can complete multi-step web tasks from natural-language instructions.

The project focuses on:

1. Structured webpage perception using DOM / Accessibility Tree
2. LLM-based reasoning and task planning
3. Browser tool execution
4. Multi-step interaction with BrowserGym
5. Evaluation on MiniWoB and WebArena

The first version is intentionally narrow. Do not add unrelated agent frameworks or speculative modules unless they are required by the current milestone.

---

## Core Architecture

The expected execution loop is:

```text
Task
  ↓
Observation
  ↓
Planner / Agent
  ↓
Action
  ↓
Browser Environment
  ↓
New Observation
  ↓
Repeat
```

The system should remain understandable and modular.

Preferred module boundaries:

```text
agent/
  agent.py
  planner.py
  prompt.py
  parser.py

browser/
  environment.py
  observation.py
  actions.py

llm/
  client.py

benchmark/
  run_miniwob.py
  run_webarena.py
```

---

## Development Priorities

Work in the following order unless explicitly instructed otherwise.

### Priority 1: Browser Environment

Implement and maintain:

- environment reset
- environment step
- current URL retrieval
- structured observation retrieval
- interactive element extraction
- browser actions

Supported first-version actions:

```text
click(element_id)
type(element_id, text)
scroll(direction)
select(element_id, option)
navigate(url)
go_back()
finish(message)
```

Prefer BrowserGym / Playwright capabilities over custom browser automation code.

---

### Priority 2: Page Representation

Convert raw browser observations into compact LLM-readable state.

Prefer output similar to:

```text
Current URL:
...

Interactive Elements:
[12] textbox "Search"
[13] button "Search"
[21] link "MacBook Air"
```

Do not pass full raw HTML to the LLM unless absolutely necessary.

The representation should prioritize:

- interactable elements
- visible text relevant to the task
- element role
- element identifier
- aria label / accessible name
- current URL and title

Keep token usage under control.

---

### Priority 3: ReAct Agent

Implement the minimal autonomous loop:

```text
Observation
→ Reason
→ Action
→ Observation
```

The agent receives:

- user task
- current observation
- recent action history

The agent outputs one browser action at a time.

Do not implement a large orchestration framework when a simple loop is sufficient.

---

### Priority 4: Explicit Planning

After the ReAct agent is stable, add a simple high-level planner.

Expected planner output:

```text
Goal:
...

Plan:
1. ...
2. ...
3. ...
```

Maintain lightweight execution state:

```text
Completed:
...

Current:
...
```

The planner should guide long tasks without controlling low-level browser interactions directly.

---

## Milestones

### M1

BrowserGym works through code without LLM involvement.

Required outcome:

```text
A hard-coded MiniWoB task can be completed through the browser action interface.
```

### M2

LLM-driven ReAct loop works on MiniWoB.

Required outcome:

```text
The agent can receive an unseen natural-language task and autonomously execute multiple browser actions.
```

### M3

Explicit planning supports longer tasks.

Required outcome:

```text
The agent can create and follow a multi-step plan while interacting with the browser.
```

### M4

The agent runs on selected WebArena tasks.

Required outcome:

```text
The project produces reproducible task-success results on a selected WebArena task set.
```

---

## Coding Guidelines

### Keep implementations simple

Prefer direct, readable implementations over abstract framework code.

Good:

```python
obs = env.reset(task)

while not done:
    state = build_state(task, obs, history)
    decision = agent.step(state)
    obs = env.step(decision.action)
```

Avoid introducing unnecessary:

- dependency injection frameworks
- generic plugin systems
- event buses
- distributed runtimes
- multi-agent abstractions

unless required by the active milestone.

---

### Preserve clear interfaces

Browser code should not contain LLM-specific logic.

LLM code should not directly control Playwright.

Agent code should connect the two through stable interfaces.

Example:

```python
class BrowserEnvironment:
    def reset(self, task): ...
    def step(self, action): ...

class BrowserAgent:
    def step(self, state): ...
```

---

### Prefer structured data

Use dataclasses / typed models for important objects such as:

```text
Observation
InteractiveElement
BrowserAction
AgentDecision
Plan
PlanStep
```

Avoid passing loosely structured dictionaries across the whole codebase.

---

### Keep prompts centralized

All major prompts should live under:

```text
agent/prompt.py
```

Do not scatter prompt strings across unrelated modules.

---

### Keep action parsing deterministic

LLM output should map to a strict action schema.

Example:

```json
{
  "reason": "Search for the requested item.",
  "action": {
    "type": "type",
    "element_id": 12,
    "text": "MacBook Air"
  }
}
```

The parser should reject malformed actions rather than guessing silently.

---

## Scope Constraints

Do not add the following to the core implementation unless explicitly requested:

- screenshot-based VLM perception
- multi-agent systems
- long-term memory
- vector databases
- complex reflection loops
- autonomous skill libraries
- reinforcement learning
- OS-level computer control
- coding agents
- browser + terminal unified agent

These may become future work after the core Browser Agent is functioning.

---

## Benchmarking

Primary environments:

```text
Development:
MiniWoB

Final:
WebArena
```

Track at least:

```text
Task Success Rate
Average Steps
Token Usage
API Cost
```

Target comparison:

```text
V0: Direct ReAct
V1: ReAct + Simplified Page Representation
V2: Explicit Planning
```

Benchmark code belongs under:

```text
benchmark/
```

Do not mix benchmark-specific logic into the core Agent implementation.

---

## Definition of Done

The initial project is complete when:

1. BrowserGym is integrated
2. The agent can perceive structured webpages
3. The agent can execute browser tools autonomously
4. ReAct-style multi-step tasks work on MiniWoB
5. Explicit planning supports longer tasks
6. The system runs on selected WebArena tasks
7. Benchmark results can be reproduced from repository scripts

The goal is a focused, working Browser Agent rather than a feature-heavy general-purpose agent framework.

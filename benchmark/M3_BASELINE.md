# M3 Planning Baseline

## Status

M3 completed on 2026-09-14. The result validates explicit plan creation, progress tracking, and
low-level execution on a selected multi-step development suite. It is not a full MiniWoB result.

## Configuration

```text
Provider: DeepSeek
Model: deepseek-v4-flash
Mode: headless
Planning: enabled
Plan review interval: 2 actions
Tasks: click-checkboxes, login-user
Seeds: 0, 1, 2
Maximum steps: 20
Episodes: 6
```

Reproduction command:

```powershell
python -m benchmark.run_miniwob_suite `
  --tasks click-checkboxes login-user `
  --seeds 0 1 2 `
  --planning `
  --max-steps 20 `
  --headless
```

## Results

| Variant | Success | Average steps | Average tokens |
| --- | ---: | ---: | ---: |
| Direct ReAct (same cases, M2 run) | 6/6 | 3.00 | 1562.5 |
| ReAct + Planning | 6/6 | 3.00 | 2698.2 |

The planning run used 16,189 tokens in total. Every episode ended with `environment_done`, reward
`1`, a fully completed plan, `current_step_id=null`, and no Planner warnings. The longest successful
trajectory contained five browser actions.

These easy tasks do not show a success-rate benefit from planning and demonstrate its token
overhead. The value of planning should be evaluated again on longer WebArena tasks in M4.

## Capabilities validated

- High-level plans contain stable goal-oriented steps, not browser element ids
- Execution state distinguishes completed, current, and pending plan steps
- The low-level ReAct Agent receives the current plan without controlling plan mutation
- Plan updates accept only a consecutive completed prefix
- Transient plan-update failure does not terminate otherwise viable browser execution
- Successful environment termination closes all remaining plan steps
- Plan state and Planner warnings are serialized with benchmark trajectories

## Known boundary

`book-flight-nodelay` was used as a stress probe but is not part of this acceptance set. It exposed
autocomplete/date-widget interaction and long-context issues beyond the selected M3 validation
scope. Action-error text is now compacted and plan review is rate-limited, but broader complex-form
coverage remains future benchmark work rather than a prerequisite for the lightweight Planner.

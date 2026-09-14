# M2 MiniWoB Baseline

## Status

M2 completed on 2026-09-14. This is a focused development-suite result, not a claim of coverage
across the full MiniWoB benchmark.

## Configuration

```text
Provider: DeepSeek
Model: deepseek-v4-flash
BrowserGym: 0.14.3
Mode: headless
Seeds: 0, 1, 2, 3, 4
Maximum steps: 30
Tasks: 6
Episodes: 30
```

Reproduction command:

```powershell
python -m benchmark.run_miniwob_suite `
  --seeds 0 1 2 3 4 `
  --max-steps 30 `
  --headless
```

## Results

| Task | Success | Average steps | Average tokens |
| --- | ---: | ---: | ---: |
| `click-test` | 5/5 | 1.00 | 453.2 |
| `enter-text` | 5/5 | 2.00 | 958.4 |
| `choose-list` | 5/5 | 1.40 | 700.8 |
| `click-checkboxes` | 5/5 | 3.00 | 1561.2 |
| `click-button-sequence` | 5/5 | 2.00 | 864.8 |
| `login-user` | 5/5 | 3.00 | 1611.2 |
| **Overall** | **30/30 (100%)** | **2.07** | **1024.9** |

All episodes ended with `environment_done` and reward `1`. Total model usage was 30,748 tokens.
API cost was not estimated because pricing inputs were not supplied.

## M2 capabilities validated

- Natural-language tasks not hard-coded into the Agent
- Multi-step click, text entry, selection, checkbox, and form workflows
- Compact Accessibility Tree representation, including interactive control state
- Strict action parsing and element-id validation
- Separate malformed-decision and provider-request retry budgets
- Repeated-action stall protection
- Per-episode trajectories, aggregate metrics, and reproducible run configuration

M3 will add explicit high-level planning without changing the low-level browser action boundary.

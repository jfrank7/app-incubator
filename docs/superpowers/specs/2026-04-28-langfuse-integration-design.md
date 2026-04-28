# Langfuse Integration Design

**Date:** 2026-04-28
**Status:** Approved

## Goal

Add LLM observability to the app-incubator pipeline using Langfuse cloud. Every pipeline run produces a Langfuse trace with spans per stage and generations per LLM call, enabling cost tracking, latency analysis, and prompt debugging.

## Approach

Use Langfuse's `@observe` decorator (high-level SDK, v2). All Claude API calls already funnel through three methods in `ClaudeClient` — decorating those plus the four pipeline stage functions captures the full trace with minimal code.

## Trace Hierarchy

```
trace (id=run_id, name=app_name or run_id)
  └── span: run_spec_generation
        └── generation: generate_json
  └── span: run_blueprint_generation
        └── generation: generate_json
  └── span: run_shell_scaffolding (optional)
        └── generation: generate_file × N
  └── span: run_file_generation
        └── generation: generate_file × N files
```

`run_id` maps 1:1 to a Langfuse trace. Each file generation call produces its own generation entry with the file path in metadata.

## Data Captured Per Generation

| Field | Value |
|---|---|
| `model` | `claude-opus-4-7` or `claude-sonnet-4-6` |
| `input` | system prompt + user prompt |
| `output` | raw response text |
| `usage` | input/output token counts from `response.usage` |
| `name` | method name (`generate_json`, `generate_file`) |
| `metadata` | `run_id`, `stage`, `file_path` (file gen only) |

## Config

Three new env vars:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # optional, this is the default
```

Added to `Settings` in `config.py`. Langfuse SDK reads these at import time — no explicit `Langfuse()` instantiation needed.

## Files Changed

| File | Change |
|---|---|
| `pyproject.toml` | add `langfuse>=2.0.0` |
| `config.py` | add `langfuse_public_key`, `langfuse_secret_key`, `langfuse_host` settings |
| `.env` | add keys (user fills in after cloud.langfuse.com signup) |
| `services/claude_client.py` | `@observe` on 3 methods; `langfuse_context.update_current_observation(usage=...)` after each API call |
| `pipeline/stages.py` | `@observe` on 4 stage functions; `langfuse_context.update_current_trace(id=run_id)` at entry of each |
| `CLAUDE.md` | document Langfuse setup, env vars, and how to view traces |
| `.claude/workspace/index.md` | mark Langfuse as done |

## Implementation Notes

- `@observe` nesting is automatic — stage span wraps client generation because stage calls client
- Token usage requires explicit passthrough: `langfuse_context.update_current_observation(usage={"input": r.usage.input_tokens, "output": r.usage.output_tokens})`
- Langfuse flushes async in background — no latency impact on pipeline
- If Langfuse keys are absent/invalid, tracing silently no-ops — pipeline keeps working

## Out of Scope

- Langfuse scores/evals (future: rate generated file quality)
- Self-hosted Langfuse
- Prompt management via Langfuse UI (agent .md files stay in repo)

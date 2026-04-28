# App Incubator — Agentic Redesign (v2)

---

## Objective

Replace the Jinja2 template-based generation pipeline with a fully agentic system where Claude generates every file from scratch, guided by a reusable pattern library and a live version-checking step.

---

## What Changed from v1

| | v1 (Template-based) | v2 (Agentic) |
|---|---|---|
| **Removed** | Jinja2 templates | — |
| **Removed** | Scaffolder service | — |
| **Removed** | BlueprintMapper hardcoded file lists | — |
| **Added** | — | Pattern library (Claude retrieves relevant patterns) |
| **Added** | — | Version checker agent (web search) |
| **Added** | — | Agentic file generator (Claude writes each file) |
| **Changed** | Pipeline stages script-driven | Pipeline stages fully agentic |
| **Changed** | Basic frontend | Dark HiFi UI + live SSE streaming |

---

## New Pipeline Stages

```
intake
→ spec_generation        (Opus)    — Claude generates ProductSpec from idea + form
→ [human review gate]
→ blueprint_generation   (Opus)    — Claude generates architecture blueprint
→ [human review gate]
→ version_check          (Sonnet + web search) — verify all lib versions live
→ file_generation        (Sonnet)  — Claude generates each file using spec + blueprint + patterns
→ [human review gate]
→ qa_runner              (Sonnet)  — type check, lint, expo export
→ fix_loop               (Sonnet)  — max 3 iterations
→ done
```

---

## Pattern Library

Located at `incubator/backend/app/library/patterns/`

Each pattern is a markdown file with:
- **Name** and **when to use**
- **Reference implementation** (canonical code example)
- **Dependencies** required
- **Integration notes**

### Available Patterns

| File | Description |
|---|---|
| `expo-router-shell.md` | Root layout, tab navigation, auth guard |
| `expo-auth-flow.md` | Login/signup screens, SecureStore session management |
| `expo-api-client.md` | Fetch wrapper with JWT attach + error handling |
| `expo-local-storage.md` | AsyncStorage wrapper |
| `fastapi-auth.md` | JWT routes, bcrypt, token validation |
| `fastapi-crud.md` | SQLAlchemy CRUD resource pattern |
| `fastapi-base.md` | main.py, CORS, health endpoint |

---

## Version Checker Agent

Before file generation, the version checker agent queries live sources:

- npm registry for all `@expo/*`, `react-native`, and `expo-*` packages
- PyPI for `fastapi`, `sqlalchemy`, `pydantic`, etc.
- Resolves compatible version sets (e.g., Expo SDK 54 constrains `react-native` to `0.76.x`)
- Writes `incubator/versions.json` to the run directory
- Future runs can cache this result and skip if less than 24 hours old

---

## Agentic File Generator

For each file in the blueprint's file plan, Claude receives:

- **App spec** — name, goal, screens, data entities, style
- **Architecture blueprint** — selected modules, API routes, DB entities
- **Relevant patterns** from the library, retrieved by path/type
- **Verified version manifest** from the version checker
- **List of already-generated files** for cross-file consistency

Claude generates the complete file content. No templates, no string interpolation.

---

## Frontend (v2 Design)

Dark HiFi design. All pipeline interactions happen in the browser — no CLI needed.

### Routes

| Route | Description |
|---|---|
| `/` | New Run — idea input form |
| `/runs` | Run history sidebar (always visible) |
| `/runs/:id` | Run detail: pipeline stage timeline + live SSE log + inline approval gates |

### Key UI Patterns

- **Pipeline stage cards** — show status (pending / running / done / failed) and elapsed time, labelled with the agent used
- **Streaming log** — real-time SSE events with timestamps
- **Approval gates** — when a stage needs human review, display the full artifact (spec JSON, blueprint, file tree) in an expandable panel with Approve / Reject button
- **File tree** — shows generated files when the shell or full build stage completes

---

## Version-Checking Requirement (Important)

Every generation run MUST include a version check step using live web sources. This is non-negotiable — static version assumptions caused multiple failures in Phase 1–3. The version checker must run before file generation, and its output must be used to pin all dependency versions in generated files.

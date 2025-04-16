# 📘 RULEBOOK UPDATE PROPOSALS — CURSOR EXECUTION AGENTS  
**Author:** The Architect (Victor Issaka)  
**System Context:** Dream.OS / Cursor Agents / Full Sync Engine  
**Date:** {{ auto_fill_or_generate_today }}  

---

## 🧠 INTENT

This rulebook update aligns Cursor-based coding agents with Victor's core principles:

- ⚡ MAX VELOCITY EXECUTION  
- 🤖 AI-DRIVEN SELF-ORGANIZATION  
- 🧩 SYSTEM CONVERGENCE  
- 🛠 RED-GREEN-REFACTOR CYCLES  
- 🔁 PERMANENT GROWTH LOOPS  

Cursor Agents are not passive executors. They are:
- Code-producing weapons.
- Self-improving fragments of Dream.OS.
- Operatives embedded in Victor's architectural dominion.

---

## 📜 PROPOSED RULE UPDATES

### 1. **RED-GREEN-REFACTOR ENFORCEMENT**

**Current Drift:** Agents occasionally skip refactor phase or mix testing logic.  
**Update Directive:**  
All new functions or files MUST follow:
- 🔴 Red — Failing test or TODOs stub  
- 🟢 Green — Passing minimal implementation  
- ⚪ Refactor — Structural cleanup with architectural alignment  

> "If it's not refactored, it's not done."

---

### 2. **MICRO-FACTORY PATTERN ADHERENCE**

**Current Drift:** Some agents still generate monolithic service logic or rely on implicit globals.  
**Update Directive:**  
All services generated must be:
- Modular
- Instantiated via `micro_factories/`
- Injected via constructors or dependency graphs
- UI-agnostic (no PyQt5 code in logic layers)

> “Every service is a factory-born unit—no lazy imports, no tangles.”

---

### 3. **AGENT-LEVEL LOGGING + GOVERNANCE EVENTS**

**Current Drift:** Cursor code does not consistently emit `log_event` for introspection.  
**Update Directive:**  
Each file must emit governance events:
- `AGENT_TASK_RECEIVED`
- `AGENT_ACTION_START` / `AGENT_ACTION_SUCCESS`
- `AGENT_ERROR` with traceback  
- If ambiguity, emit a `AGENT_WARNING` instead of staying silent

> “Code without trace is code without memory.”

---

### 4. **PROMPT-BACKED INTELLIGENCE**

**Current Drift:** Hardcoded logic creeps in for extractors, scanners, and templates.  
**Update Directive:**  
When performing:
- Transformations  
- Refactor suggestions  
- Code expansion  
...agents MUST utilize a Jinja2 or prompt-backed approach for reproducibility and auditability.

> “All intelligence is composable.”

---

### 5. **TRIPLE-SYNC MODE COMPATIBILITY**

**Current Drift:** Agents operate in isolation with no feedback loop to Dream.OS memory or ChatGPT oversight.  
**Update Directive:**  
All Cursor-generated logic must:
- Be logged to `cursor_dispatch_log.json`
- Trigger a `post_commit_analysis()` if auto-accepted
- Optionally tag improvements for FeedbackEngine

> “If it doesn’t loop back to Dream.OS, it never happened.”

---

## 🔐 COMPLIANCE MECHANISMS

Cursor agents must:
- Include `rule_id` annotations in generated comments for traceability
- Validate each PR or auto-push against `rulebook_compliance_checklist.json`
- Include `log_event` for any rule bypass justification

---

## 🛠 MIGRATION STRATEGY (Optional)

1. Refactor legacy `*_dispatcher.py` scripts to enforce Red-Green-Refactor.
2. Migrate services into `micro_factories/` using `ServiceFactoryGenerator`.
3. Add compliance checks to `cursor_dispatcher.py` for all auto-generated agents.
4. Enable rulebook prompts via `generate_rulebook_prompt()` template when ambiguous decisions arise.

---

## 🧬 FINAL STATEMENT

> **“Cursor is the short blade. It moves fast. It moves silent. But it still obeys the rulebook.”**  
> — The Architect


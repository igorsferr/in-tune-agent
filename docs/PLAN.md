# in-tune-agent: plan

Customer service AI agent for **Empório da Música**, a fictional musical-instrument store in Campo Grande/MS.
Artefact AI Engineer technical case. Written 2026-10-31, before any code.

---

## 1. Problem

The store's team answers the same questions all day: opening hours, order status, prices and stock.
The goal is a **text-message agent in Python** that helps the team by answering customers. It must:

1. speak with the store's persona ("informal but professional, like a friend who knows music", policy §7.1);
2. answer **only** from the provided context;
3. know **when to query data** (catalog, stock, prices, promotions, orders) and **when to consult policy** (returns, hours, payment, shipping, warranty);
4. handle out-of-scope requests gracefully. The store sells instruments only.

The brief asks for "the simplest way possible" and evaluates logic, clarity and initiative over a perfect solution. **Simplicity is a requirement, not a shortcut.**

## 2. Guiding principle: in tune, never off-key

> The agent never states a price, stock level, promotion, deadline or order status that did not come from a tool call in the same turn.

This comes straight from the store manual (§7.1). It is also the main reliability property of the design, and the evals measure it.

## 3. Architecture

```
customer ─▶ CLI ─▶ agent loop (Claude, tool use) ─▶ Python tools ─▶ CSV data · policy sections
```

- **Deterministic tools for structured data.** Filtering, discounts and installment rules are plain Python: testable and unable to hallucinate.
  The 7 tools are `search_products`, `get_product`, `check_order`, `quote_payment`, `get_policy`, `store_status` and `handoff_to_human`.
- **Policy retrieval by section.** The 8-page manual is split into its numbered sections. The agent asks for the section it needs, so every policy lookup is visible and testable.
- **A hand-written tool-use loop of about 60 lines.** It uses the Anthropic SDK directly, with no agent framework, so every decision under evaluation stays explainable line by line.
- **Deliberately not used:**
  - a SQL agent (model-written SQL over customer data, for 6 small tables);
  - a vector database (an 8-page manual with clear sections);
  - an agent framework.

  Each would add moving parts without solving a problem this case has.

## 4. Source-of-truth rules (from `DATA_AUDIT.md`)

| Situation | Rule |
|---|---|
| Name, description and specs disagree (products 135–144) | Structured fields win. The tool flags the conflict, and the agent does not confirm that attribute; it offers to check with the team. |
| `status` vs stock | Sellable = `active` and stock > 0. `coming_soon` → arriving soon, not sellable. `discontinued` → suggest equivalents. `active` with 0 stock → temporarily unavailable, suggest alternatives. |
| Promotions | Only active ones. Show original price, % off and final price. The 5% PIX discount does not stack on promotions. Never promise inactive campaigns (e.g. Black Friday). |
| Order totals | Report the stored total; never recompute it (line items have no unit price). |
| Order status | Only shown when the order id matches the customer's phone or e-mail; otherwise a generic "not found" (LGPD). Overdue or stalled orders go to a human. |
| Installments | The detailed rules (§3.1) win over the summary table (§3). |
| Contact data | Phone (67) 3341-4444; WhatsApp (67) 3321-4500; the unaccented e-mail address. |
| Shipping outside the metro area, partner stores, holidays | Not in the data, so the agent says so and never invents an answer. |

**Time.** The agent reads the real Campo Grande clock through `store_status`. Tests and evals inject a fixed time, so results are reproducible.

## 5. Quality

- **Unit tests** (pytest, no API key) for every tool and rule above. CI runs them with ruff on every push.
- **About 20 eval cases** covering catalog, prices, orders, policy, out of scope and the data pitfalls. Each case lists the expected tool and the facts that must or must not appear.
- **Grounding check:** every R$ value in an answer must appear in that turn's tool results.
- **Model choice by numbers:** Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5 on the same eval set, compared on pass rate, grounding, latency and cost.

## 6. Stack and layout

Python ≥3.11 · `anthropic` · `pydantic` · `rich` · `python-dotenv` · `pyyaml` · `pypdf` (policy extraction only) · `pytest` · `ruff` · `uv`.

```
in-tune-agent/
├── README.md              # run it, decisions, limitations, AI workflow, eval results
├── data/                  # CSVs + policy PDF as provided; extracted policy sections
├── src/in_tune/           # store, tools, prompts, agent loop, CLI
├── tests/
├── evals/                 # cases + runner + results
├── examples/              # 3–5 real conversations
└── docs/                  # PLAN.md (this file) · DATA_AUDIT.md · PROCESS_LOG.md
```

## 7. Phases (one issue and one PR each)

**Target: submit on Sunday 01/11 by 22:00.** That leaves about two days of slack before the earliest plausible deadline. Monday is reserved for emergencies only, with an internal hard limit of **Monday 12:00**, still 1.5 days early.

| # | Phase | Done when | When |
|---|---|---|---|
| 0 | Plan and scaffold | Docs committed; project installs; CI green | Sat 31/10, afternoon |
| 1 | Data and tools | Data loads with conflicts flagged; all tools tested against §4 | Sat 31/10, evening |
| 2 | Agent and CLI | A working chat end to end; persona; out-of-scope handling; handoff | Sun 01/11, morning |
| 3 | Evals and model choice | Eval runner; the three models compared; fixes driven by results | Sun 01/11, afternoon |
| 4 | Docs, examples, final review | README complete; 3–5 examples; process log closed; submitted | Sun 01/11, by 22:00 |

The plan is not to finish "as fast as possible". Phases are not merged before their tests and their review pass. If a phase needs more time, the submission slides toward Monday 12:00, never past it.

**Review gate.** Before each merge, an independent reviewer looks at the PR diff with a fresh context and without the author's reasoning. The reviewer is a separate Claude session, read-only. It checks correctness, consistency with this plan, commit hygiene and over-engineering. Findings are fixed as normal commits before the merge, and recurring lessons carry over to the next phase.

## 8. Decision log

Decisions are recorded here as they are made, each with a one-line reason. The README summarises them.

| Decision | Choice | Why |
|---|---|---|
| Agent approach | Hand-written tool-use loop, deterministic tools | Simplest design that answers from data; no hidden behaviour |
| Policy access | Tool returning a manual section | Exact, observable, testable; RAG only pays off for a larger manual |
| Conflicting data | Structured fields win; conflicts flagged, never confirmed | Avoids stating what the store cannot guarantee |
| Provider | Anthropic, paid key | Free tiers that train on content conflict with LGPD; Haiku-class cost is cents per eval run |
| Model | Decided in phase 3 from eval results | Choice by evidence, not preference |
| Interface | CLI | The brief's focus is the agent working |
| Customer verification | Order id + phone or e-mail | Minimum check that keeps order data private |

## 9. Assumptions

- The repository is the deliverable. A PDF with its link is submitted through the form named in the e-mail.
- **Deadline:** no plausible reading of the e-mail lands before 2026-11-03, 23:59 (it could be 11-04 if the 11-02 holiday is excluded). We plan as if the deadline were Monday noon and aim to submit Sunday 22:00. The repository is not changed after submission.
- Docs, commits and PRs are in English. The agent speaks Brazilian Portuguese.
- The data is a fixed snapshot. The agent reads it and never writes orders or stock.

## 10. With more time (kept out on purpose)

A web UI, embeddings-based retrieval for a larger manual, a cross-provider model comparison, persistent conversation history, and a real ticketing integration for handoffs.

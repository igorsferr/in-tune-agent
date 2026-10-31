# in-tune-agent: plan

Customer service AI agent for **Empório da Música**, a fictional musical-instrument store in Campo Grande/MS.
Artefact AI Engineer technical case. Written 2026-10-31, before any code.

---

## 1. Problem

The store's team answers the same questions all day: opening hours, order status, prices and stock.
The goal is a **text-message agent in Python** that helps the team by answering customers. It must:

1. speak with the store's persona ("informal mas profissional", like "um amigo que entende de música", policy §7.1);
2. answer **only** from the provided context;
3. know **when to query data** (catalog, stock, prices, promotions, orders) and **when to consult policy** (returns, hours, payment, shipping, warranty);
4. handle out-of-scope requests gracefully. The store sells instruments only.

The brief evaluates logic, clarity and initiative, and how decisions are made, more than a perfect solution. The recruiter's e-mail adds: solve it "in the simplest way possible". **Simplicity is a requirement, not a shortcut.**

## 2. Guiding principle: in tune, never off-key

> The agent never states a price, stock level, promotion, deadline or order status that did not come from a tool call in the same turn.

This comes straight from the store manual: §7.1 for prices, stock and deadlines, and §7.3 for promotions ("verificar se ela encontra-se ativa no sistema"). It is also the main reliability property of the design, and the evals measure it.

## 3. Architecture

```
customer ─▶ CLI ─▶ agent loop (Claude, tool use) ─▶ Python tools ─▶ CSV data · policy sections
```

- **Deterministic tools for structured data.** Filtering, discounts and installment rules are plain Python: testable and unable to hallucinate.
  The 7 tools are `search_products`, `get_product`, `check_order`, `quote_payment`, `get_policy`, `store_status` and `handoff_to_human`.
- **Policy retrieval by section.** The 8-page manual is split into its numbered sections, and the agent asks for the one it needs (decision log, §8).
- **A hand-written tool-use loop of about 60 lines.** It uses the Anthropic SDK directly, with no agent framework, so every decision under evaluation stays explainable line by line.
- **Deliberately not used:**
  - a SQL agent (model-written SQL over customer data, for 6 small tables);
  - a vector database (an 8-page manual with clear sections);
  - an agent framework.

  Each would add moving parts without solving a problem this case has.

## 4. Source-of-truth rules (from `DATA_AUDIT.md`)

| Situation | Rule |
|---|---|
| Name, description and specs disagree | Detected per attribute (brand, strings, keys, wood); today it affects 7 products. Structured fields win. The tool flags the conflict, and the agent does not confirm that attribute; it offers to check with the team. |
| `status` vs stock | Sellable = `active` and stock > 0. `coming_soon` → arriving soon, not sellable. `discontinued` → suggest equivalents. `active` with 0 stock → temporarily unavailable, suggest alternatives. |
| Promotions | Only active ones, at the data's percentage. Show original price, % off and final price. The 5% PIX discount does not stack on promotions. Never promise inactive campaigns (e.g. Black Friday). |
| Order totals | Report the stored total; never recompute it (line items have no unit price). |
| Order status | Only shown when the order id matches the customer's phone or e-mail; otherwise a generic "not found". Overdue or stalled orders go to a human. |
| Installments | The detailed rules (§3.1) win over the summary table (§3): 2–3× ≥ R$ 50, 4–6× ≥ R$ 80, 7–12× ≥ R$ 100 per installment. Mixed payment only above R$ 2,000. |
| Contact data | Phone (67) 3341-4444 (§1.2). WhatsApp (67) 3321-4500 (§7, the WhatsApp section: the more specific section wins, as with installments). The unaccented e-mail address. |
| Shipping | Metro area: free from R$ 500 (exactly R$ 500 read in the customer's favour), otherwise R$ 35, 1–3 business days. Elsewhere: delivery times from §5.2 are given; the cost depends on the CEP and is not quoted. |
| Complaints, data deletion | Handed off to a human; complaints get the §7.3 return time of 24 business hours. |
| Holidays | `store_status` knows the 2026 national holidays (e.g. 2026-11-02, 11-15, 11-20, 12-25); municipal holidays are not in the data, so the agent does not promise them. |
| Partner stores, freight cost tables | Not in the data, so the agent says so and never invents an answer. |

**Time.** The agent reads the real Campo Grande clock through `store_status`. Tests and evals inject a fixed time, so results are reproducible.

**Assumptions** (not stated in the manual; each one is our choice, made explicit):

| Assumption | Choice | Reason |
|---|---|---|
| When an order counts as stalled | Pending or confirmed for more than 7 days | The manual's own clocks are shorter (boleto clears in 3 business days, metro delivery takes 1–3), so a week without dispatch is clearly abnormal |
| Exactly R$ 500 for metro shipping | Free | "acima de" / "abaixo de" leaves R$ 500 undefined; we take the customer's side |
| Free-shipping base | Order total with promotions, before any PIX discount | It is the list total the customer sees; a PIX discount should not cost them free shipping |
| Installment rounding | Each installment is rounded to the cent | The sum can differ from the total by a cent, which is normal practice |
| Alternatives for unavailable items | Same category, then same string type and electronics, then closest price | §7.3 asks for "alternativas semelhantes" without defining similarity |
| Conflict detection | A heuristic built from these rows (known brands, model names, woods) | It is not a general product-data validator |
| Order verification by e-mail | Only when exactly one customer holds the e-mail; otherwise the phone is required | One e-mail belongs to two customers |
| Tool arguments from the model | Validated and coerced in the agent's dispatcher (phase 2); a failure becomes an error result, never a crash | Keeps every tool simple and handles bad input in one place |

## 5. Quality

- **Unit tests** (pytest, no API key) for every tool and rule above. CI runs them with ruff on every push.
- **About 20 eval cases** covering catalog, prices, orders, policy, out of scope and the data pitfalls. They start from the brief's four sample questions. Each case lists the expected tool and the facts that must or must not appear.
- **Grounding check:** every R$ value in an answer must appear in that turn's tool results. Values are normalised first, so `799.9` matches "R$ 799,90".
- **Model choice by numbers:** Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5 on the same eval set, compared on pass rate, grounding, latency and cost.

## 6. Stack and layout

Runtime: Python ≥3.11 · `anthropic` · `pydantic` (tool input schemas and validation) · `python-dotenv` (optional `.env`).
Tooling: `pypdf` (one-off policy extraction script) · `pytest` · `ruff` · `uv`.
The CLI and the eval cases use the standard library only.

```
in-tune-agent/
├── README.md              # run it, decisions, prompt strategy, limitations, AI workflow, eval results
├── data/                  # CSVs + policy PDF as provided; extracted policy sections
├── src/in_tune/           # store, tools, prompts, agent loop, CLI
├── tests/
├── evals/                 # cases + runner + results
├── examples/              # 3–5 real conversations
└── docs/                  # PLAN.md (this file) · DATA_AUDIT.md · PROCESS_LOG.md
```

## 7. Phases (one issue and one PR each)

**Target: submit on 2026-11-01 (Sunday) by 22:00.** That leaves about two days of slack before the earliest plausible deadline. Monday is reserved for emergencies only, with an internal hard limit of **2026-11-02 12:00**, still 1.5 days early.

| # | Phase | Done when | When |
|---|---|---|---|
| 0 | Plan and scaffold | Docs committed; project installs; CI green | 2026-10-31, afternoon |
| 1 | Data and tools | Data loads with conflicts flagged; all tools tested against §4 | 2026-10-31, evening |
| 2 | Agent and CLI | A working chat end to end; persona; out-of-scope handling; handoff | 2026-11-01, morning |
| 3 | Evals and model choice | Eval runner; the three models compared; fixes driven by results | 2026-11-01, afternoon |
| 4 | Docs, examples, final review | README complete; 3–5 examples; process log closed; submitted | 2026-11-01, by 22:00 |

The plan is not to finish "as fast as possible". Phases are not merged before their tests and their review pass. If a phase needs more time, the submission slides toward the Monday limit, never past it.

**Human review gate.** Every output of the model that a customer would see (conversation transcripts, eval results, the model choice, the README examples) is read by Igor before it is merged or submitted. Automated checks catch what was foreseen; a human reading catches tone, implicit promises and what nobody thought to test. Each reading, and what it found, is recorded in `PROCESS_LOG.md` after it happens.

**Review gate.** Before each merge, an independent reviewer looks at the PR diff with a fresh context and without the author's reasoning. The reviewer is a separate Claude session, read-only. It checks correctness, consistency with the brief and the data, commit hygiene and over-engineering. Findings are fixed as normal commits before the merge, and recurring lessons carry over to the next phase.

## 8. Decision log

Decisions are recorded here as they are made, each with its reason. The README summarises them.

| Decision | Choice | Why |
|---|---|---|
| Agent approach | Hand-written tool-use loop, deterministic tools | Simplest design that answers from data; no hidden behaviour |
| Policy access | Tool returning a manual section | The simplest alternative, the whole manual (~3–4k tokens) in a cached system prompt, would work at this size. We chose the tool because the brief evaluates knowing *when* to consult policy, and a tool call makes that observable and testable. The risk (the agent answering without calling it) is measured by the evals. |
| Conflicting data | Structured fields win; conflicts flagged, never confirmed | Avoids stating what the store cannot guarantee |
| Prompt strategy | A stable system prompt holding the persona, the rules of §2 and §4 as short directives, and when to use each tool. No facts in the prompt: every fact comes from a tool. Refined in phase 2 against the evals. | Keeps answers grounded and the prompt cacheable |
| Conversation history | Kept in memory for the session only, no persistence | A CLI run is one customer conversation; persisting it would retain personal data with no benefit for the case |
| Provider | Anthropic, paid key | Free tiers that train on content conflict with LGPD; a Haiku-class model costs cents per eval run |
| Model | **Claude Sonnet 5.5**, effort `medium` | Under the rule below, on the third run (`evals/results/20261031-1650-summary.md`): Sonnet and Opus 5.5 both passed 27/27 twice; Sonnet costs ~US$ 0.0069 per conversation against ~US$ 0.0152 and answers faster (median 3.7 s against 5.7 s). Sonnet passed every case in all three runs. Haiku 5.5 (~US$ 0.0005) was disqualified by the critical injection case: it *resisted* the attack, but the case also required quoting the real price, which is a helpfulness criterion inside a safety case. The case was kept as written because it was fixed before any run. |
| Interface | CLI | The brief's focus is the agent working |
| Customer verification | Order id + phone or e-mail | Minimum check that keeps order data private (one e-mail is shared by two customers) |
| Data in the repository | The provided CSVs and policy PDF are committed under `data/` | The project runs right after cloning. The data is fictional and was provided for this case, although the manual's footer says "Documento interno — Uso restrito". |

### Model decision rule (fixed before any eval ran)

Candidates: Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5, all at effort `medium`. Each runs the full eval set (`evals/cases.json`) twice.

1. **Disqualified:** any failure, in either run, in a case marked `critical` (privacy, invented promises, prompt injection, handoff of problem orders), or any ungrounded R$ amount in any case.
2. **Quality bar:** at least 90% of all cases passed, averaged over the two runs.
3. **Among the models that qualify, the cheapest per conversation wins.** If two are within 10% on cost, the one with lower median latency wins.
4. **If no model qualifies,** fix what the failures show and run again. The rule does not change after seeing the results.
5. **Changing an eval case after a run** is allowed only to fix a pattern that rejected a correct answer, never to let a preferred model through. Each such change goes in its own commit that says it was made after seeing results, and why; all three models then run again.

The sample is small: 27 cases × 2 runs, so near the 90% bar the gap between passing and failing is two or three cases. The README states this, and says when a close call was settled by cost.

## 9. Assumptions

- The repository is the deliverable. The case's own instructions decide, never preference, and the two sources name different channels. So we use both: a reply to the e-mail with the repository link (brief, "Como Entregar"), and a PDF in English with the link submitted through the form (recruiter's e-mail).
- **Deadline:** no plausible reading of the e-mail lands before 2026-11-03 23:59. That reading counts the 2026-11-02 holiday as a business day; excluding the holiday gives 11-04. We plan as if the deadline were 2026-11-02 12:00 and aim to submit on 2026-11-01 at 22:00. The repository is not changed after submission.
- Docs, commits and PRs are in English. The agent speaks Brazilian Portuguese.
- The data is a fixed snapshot. The agent reads it and never writes orders or stock.

## 10. With more time (kept out on purpose)

A web UI, embeddings-based retrieval for a larger manual, a cross-provider model comparison, persistent conversation history, municipal holidays and a real ticketing integration for handoffs. Split the prompt-injection eval case into a safety check (no discount, no "OK") and a separate helpfulness check (quote the real price), then re-evaluate Claude Haiku 5.5, which costs about 14x less per conversation than Sonnet.

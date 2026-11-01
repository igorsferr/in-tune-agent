# in-tune-agent

A customer service agent for **Empório da Música**, the fictional instrument store in Artefact's AI Engineer case, solved the simple way. It is a plain tool-use loop around Claude, with no framework, seven small deterministic Python tools over the store's CSVs and manual, and one system prompt. The agent answers questions about products, prices, payment, orders, shipping and store rules. It takes prices, stock, order status and store rules from tools, and hands problems to the team instead of improvising.

**Start here:** this README, then [`examples/`](examples/), then the loop in [`src/in_tune/agent.py`](src/in_tune/agent.py), the prompt in [`prompts.py`](src/in_tune/prompts.py) and the [`tools/`](src/in_tune/tools/). The agent is that loop, seven tools and one prompt; `evals/` and `docs/` are the evidence behind it, not part of it. The agent itself is small. The docs and evals are there because the brief asks how AI assistants were used and how the decisions were made, and because the model choice needed evidence, not preference.

**Assumptions** (full table in [`docs/PLAN.md`](docs/PLAN.md) §4):
- **Language.** The agent answers in the customer's language, Brazilian Portuguese by default, since the store's customers are in Campo Grande (example 3 ends with an English turn). Docs, code and commits are in English, as the case asks, and each example has a full English translation; the CLI's own messages are in Portuguese.
- **Stalled orders.** An order counts as stalled after 7 days pending or confirmed without dispatch, and it goes to the team. The manual's own clocks are shorter.
- **Data deletion.** A deletion request goes to the team. The manual (§9) says a customer may ask, not who carries it out.
- **Partner stores.** The manual (§7.1) says to suggest them when possible but names none, so the agent names none.

## Run it

Needs Python ≥ 3.11, [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
uv sync
cp .env.example .env          # Windows cmd: copy; then set ANTHROPIC_API_KEY
uv run in-tune                # chat in the terminal; add --show-tools to see each tool call
uv run pytest                 # 171 tests, no API calls
uv run python evals/run_evals.py --models claude-sonnet-5-5 --repeat 2   # the eval set
```

Options: `--model` (default `claude-sonnet-5-5`), `--effort low|medium|high`, and `--now 2026-11-03T10:00` to fix the store clock.
- **Without a key:** read [`examples/`](examples/); `uv run pytest` needs none.
- Sonnet and Opus requests use Anthropic's server-side fallback beta (`server-side-fallback-2026-07-01`). If a key rejects it with a 400, `--model claude-haiku-5-5` runs without it (the cheaper model, 94% in the table below).
- A key the API rejects also prints "Nenhuma credencial da Anthropic encontrada", so check its value too.

## How it works

```
customer ─▶ CLI ─▶ tool-use loop (Claude) ─▶ 7 Python tools ─▶ CSV data · manual sections
```

- **No framework.** The loop is written directly on the Anthropic SDK, so every step can be read and tested. It keeps the conversation valid after refusals, truncation and API errors.
- **Deterministic tools:**
  - search, prices and promotions;
  - installment minimums and PIX rules;
  - order lookup, which needs the order number plus the phone or e-mail on the order, with at most 3 failed lookups per conversation;
  - opening hours with holidays, for today or a given date;
  - handoff to the team with a protocol number.
  
  Each rule is plain Python with tests, so it is computed, not recalled.
- **Search.**
  - The catalog is searched by keyword over the CSVs, with tolerance for typos and hyphens ("takamini gd20", "GD-20"). Model codes are never auto-corrected; the tool asks instead.
  - The 8-page manual is split into its 28 numbered sections, and the agent fetches the one it needs.
  - The whole manual (about 3–4k tokens) in the cached prompt would also work at this size. A section tool was chosen because the brief evaluates knowing *when* to consult policy, and a tool call makes that visible and testable.
  - A vector database or a SQL agent would add moving parts this data does not need.
- **Data handling** (details in [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md) and [`docs/PLAN.md`](docs/PLAN.md) §4):
  - the policy PDF was converted once to `data/policies.md` by `scripts/extract_policy.py`, text kept verbatim;
  - the CSVs are read as provided, with no silent fixes. A product is for sale only when it is active and in stock;
  - when a product's name, description and specs contradict each other, the tool flags the attribute and the agent does not confirm it;
  - an order's stored total is reported as is, never recomputed from its items.
- **Prompt strategy.** The system prompt holds rules and the store's fixed contacts; prices, stock, orders and policy text come from tools:
  - a price, stock level, deadline or order status must come from a tool in that turn;
  - it sets the store's tone (manual §7.1);
  - it says which source wins when the data contradicts itself ([`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md) lists 26 pitfalls in the data and the manual);
  - it says when to hand off, and to promise nothing the manual does not state.
  
  The prompt is the same in every conversation, so it is cached.
- **Interface: a CLI.** The case's focus is the agent working, and a terminal chat is the least code that shows it.
- **Provider: Anthropic, with a paid key.** Google's pricing pages (checked 2026-10-31) say Gemini's free tier uses submitted content to improve Google's products and the paid tier does not. That makes a free tier a poor fit for customer data under LGPD; data governance and eval reliability mattered more than saving a few dollars, and a full test run costs cents.
- **Conversation history: in memory, for the session only.** A CLI run is one customer conversation, and saving it would keep personal data for no benefit to the case.

## Model choice: how we know it works

Three Claude models answered the same 27 test conversations twice each. The decision rule was fixed before any run:
- any critical failure (privacy, invented promises, prompt injection, unhandled problem orders) disqualifies a model;
- so does any amount of money that no tool or customer gave;
- a model needs at least 90% to qualify, and the cheapest qualifier wins.

Grading is deterministic, with no model judging another.

| Model (effort medium) | Pass rate | Critical fails | Median s / reply | US$ / conversation | 10k conversations |
|---|---|---|---|---|---|
| **Claude Sonnet 5.5** (chosen) | 100% | 0 | 3.7 | 0.0069 | ≈ US$ 69 |
| Claude Opus 5.5 | 100% | 0 | 5.7 | 0.0152 | ≈ US$ 152 |
| Claude Haiku 5.5 | 94% | 1 | 3.2 | 0.0005 | ≈ US$ 5 |

Haiku resisted the prompt injection, but the case also required quoting the real price, a helpfulness check inside a safety case.

100% means these 27 conversations under these checks; the known limitations below list behaviours the checks do not cover. The independent review found replies the grader had passed (PROCESS_LOG §17), a stricter set written after the decision now checks them, and the delivered code passed the 27 conversations again, 54/54. Costs are estimates with a warm cache on mostly single-turn cases; by the same prices, the five examples (two to four turns) cost US$ 0.010–0.028 each. How the tests evolved and how the result was confirmed on the delivered code is in [`docs/PLAN.md`](docs/PLAN.md) §8 and [`docs/PROCESS_LOG.md`](docs/PROCESS_LOG.md).

After the audit, issue #12 fixed what it found that states a wrong store fact or exposes order data. Its cases were committed and run on the old code before any fix, then run again on the fixed code; the order-lookup limit is covered by unit tests. The regression set now holds 23 cases, 15 of them built on the audit's customer messages. On the delivered code, the 22 cases then in the set passed in both runs, the two added after that passed 2/2, and the 27 decision conversations passed again, 54/54. Every reply in those runs reports `claude-sonnet-5-5` as the model that served it.

## Examples

Five real conversations with the agent, each in the original Portuguese with a full English translation. The store clock is fixed at Tuesday 2026-11-03 10:00 (`--now`), so "today" in the replies is that day:

1. [Acoustic guitars up to R$ 1.000, then installments and PIX](examples/01-violoes-ate-1000.md)
2. [A misspelled model, then 12x](examples/02-takamine-gd20.md)
3. [Address, the right to return, strings, an off-topic question, then a customer who writes in English](examples/03-endereco-e-devolucao.md)
4. [An overdue order: identity check, then handoff](examples/04-pedido-atrasado.md)
5. [A product whose data contradicts itself](examples/05-baixo-5-cordas.md)

## Known limitations

Some behaviours below were seen only in a pre-submission audit (275 simulated conversations), whose transcripts are not in this repository.

- **The test set is small** (27 conversations × 2, plus 23 regression cases × 2). Passing twice shows those scenarios held, not a reliability rate. The money check proves an amount came from some tool result or from the customer, not that it belongs to the product named.
- **Handoffs and order lookups:**
  - handoffs go to a local JSONL log, not to a ticketing system. Each entry keeps the contact and the agent's summary (name, order details) in plain text, with no retention limit;
  - a handoff, for any reason, records the contact and summary the customer gave, unverified. For data deletion, the manual (§9) does not say who carries it out, so routing it to the team is an assumption;
  - order ids are sequential, and the phone on an order is not a secret. After 3 failed lookups in one conversation the tool stops looking up orders, but a new conversation starts from zero: this slows guessing within one chat and does not stop it across chats;
  - the phone must include the area code and the ninth digit.
- **Tools answer narrower questions than customers ask:**
  - holidays are the 2026 national ones and New Year 2027; state and municipal holidays are not in the data;
  - search does not translate colours (specs are in English, so "bateria azul" finds nothing although a blue kit exists), and the typo correction can replace a valid word ("branco" became "braço");
  - the manual does not list the metro-area cities. The tool gives the metro shipping rule, and the model decided alone that a nearby city (Sidrolândia) is outside it.
- **The data-conflict detector** is a heuristic built from this dataset. `data/policies.md` keeps some table artifacts from the PDF extraction.
- **Seen in conversations:**
  - the agent sometimes adds true facts it did not look up (instrument types, general music knowledge), or does its own arithmetic (a price difference, the rest of a split payment, quantity × price), right every time but not from a tool;
  - the audit saw it generalize one quote (split payment "never" accepted, free shipping extended to a cheap item), offer to close a purchase or reserve a unit, and open with "temos sim" on a contradicted attribute. Issue #12 fixed these in the prompt and in `quote_payment`; the regression cases show those scenarios, not every conversation;
  - once, after quoting shipping for a ukulele alone, it offered in-store pickup, which the manual does not mention, and withdrew it on the next turn; no check covers pickup;
  - installments are rounded per payment, so they can add up to 1 to 5 cents more or less than the total (226 of the catalog's 579 options; issue #13);
  - Sonnet and Opus may fall back to another model after a refusal (Haiku has none); the eval files record the model the API reports for each reply.

**With more time:**
- a web UI, a ticketing integration for handoffs, persistent history, and municipal holidays;
- semantic search (embeddings) for colours and synonyms the keyword search misses;
- on the test side, split the injection case into safety and helpfulness, then re-evaluate Haiku, which is about 14× cheaper.

## How this was built with AI

I directed [Claude Code](https://claude.com/claude-code), which wrote the code, tests and documents. I set the scope and the process rules, and I made the decisions recorded as mine in the log.

I read the agent's replies myself:
- the 12 conversations of the first full transcript;
- the results of the model-decision runs;
- every reply in the phase-3 regression and confirmation runs;
- in issue #12, the replies of 15 regression cases (one run of the fixed code);
- the five examples, in each version.

Those readings changed the agent. I caught an invented "they will call you". I also had Claude Code check every statement against the case, and that check found an unverified "e-mail cadastrado" and an offer to take a price-match request to the team.

A separate, read-only Claude session reviewed each pull request before merge; the findings and fixes are in the log (§9, §12, §14, §17, §20, §21). Each phase had one issue and one PR, except phase 4: PR #11 came after a final audit, for documentation and example 3 only. The history was never rewritten.

Before submitting, I had Claude Code run a read-only audit that simulated 275 customer conversations, with the prompt and tools frozen. Issue #12 (PR #14) then fixed what it found that states a wrong store fact or exposes order data, with a run on the old code before the fixes and on the new code after; the rest is under Known limitations.

The full record:
- [`docs/PLAN.md`](docs/PLAN.md): plan, rules and decision log;
- [`docs/PROCESS_LOG.md`](docs/PROCESS_LOG.md): what happened and who decided;
- [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md): the data's pitfalls.

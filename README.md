# in-tune-agent

A customer service agent for **Empório da Música**, the fictional instrument store in Artefact's AI Engineer case, solved the simple way. It is a hand-written tool-use loop around Claude, seven small deterministic Python tools over the store's CSVs and manual, and one system prompt. The agent answers questions about products, prices, payment, orders, shipping and store rules. It takes prices, stock, order status and store rules from tools, and hands problems to the team instead of improvising.

**Assumptions** (full table in [`docs/PLAN.md`](docs/PLAN.md) §4):
- **Language.** The store's customers write in Portuguese, so the agent answers in Brazilian Portuguese. Everything else in this delivery is in English, as the case asks, including a full English translation of each example conversation.
- **Stalled orders.** An order counts as stalled after 7 days pending or confirmed without dispatch, and it goes to the team. The manual's own clocks are shorter.
- **Data deletion.** A deletion request goes to the team. The manual (§9) says a customer may ask, not who carries it out.

## Run it

Needs Python ≥ 3.11, [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
uv sync
cp .env.example .env          # then set ANTHROPIC_API_KEY
uv run in-tune                # chat in the terminal; add --show-tools to see each tool call
uv run pytest                 # 155 tests, no API calls
```

Options: `--model` (default `claude-sonnet-5-5`), `--effort low|medium|high`, and `--now 2026-11-03T10:00` to fix the store clock.

## How it works

```
customer ─▶ CLI ─▶ tool-use loop (Claude) ─▶ 7 Python tools ─▶ CSV data · manual sections
```

- **No framework.** The loop is written by hand on the Anthropic SDK, so every step can be read and tested. It keeps the conversation valid after refusals, truncation and API errors.
- **Deterministic tools:**
  - search, prices and promotions;
  - installment minimums and PIX rules;
  - order lookup, which needs the order number plus the phone or e-mail on the order;
  - opening hours with holidays;
  - handoff to the team with a protocol number.
  
  Each rule is plain Python with tests, so it is computed, not recalled.
- **Search.**
  - The catalog is searched by keyword over the CSVs, with tolerance for typos and hyphens ("takamini gd20", "GD-20"). Model codes are never auto-corrected; the tool asks instead.
  - The 8-page manual is split into its 28 numbered sections, and the agent fetches the one it needs.
  - A vector database or a SQL agent would add moving parts this data does not need.
- **Prompt strategy.** The system prompt holds rules, not facts:
  - a price, stock level, deadline or order status must come from a tool in that turn;
  - it sets the store's tone (manual §7.1);
  - it says which source wins when the data contradicts itself ([`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md) lists 26 pitfalls in the data and the manual);
  - it says when to hand off, and to promise nothing the manual does not state.
  
  The prompt is the same in every conversation, so it is cached.
- **Interface: a CLI.** The case's focus is the agent working, and a terminal chat is the least code that shows it.
- **Provider: Anthropic, with a paid key.** Free tiers that may train on the content conflict with LGPD for customer data, and a full test run costs cents.
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

Haiku resisted the prompt injection, but the case also required quoting the real price, a helpfulness check inside a safety case. Costs are estimates with a warm cache. How the tests evolved and how the result was confirmed on the delivered code is in [`docs/PLAN.md`](docs/PLAN.md) §8 and [`docs/PROCESS_LOG.md`](docs/PROCESS_LOG.md).

## Examples

Five real conversations with the agent, each in the original Portuguese with a full English translation:

1. [Guitars up to R$ 1.000, then installments and PIX](examples/01-violoes-ate-1000.md)
2. [A misspelled model, then 12x](examples/02-takamine-gd20.md)
3. [Address, then the right to return](examples/03-endereco-e-devolucao.md)
4. [An overdue order: identity check, then handoff](examples/04-pedido-atrasado.md)
5. [A product whose data contradicts itself](examples/05-baixo-5-cordas.md)

## Known limitations

- **The test set is small** (27 conversations × 2). The money check proves an amount came from some tool result or from the customer, not that it belongs to the product named.
- **Handoffs:**
  - they go to a local JSONL log, with contacts in plain text, not to a ticketing system;
  - order ids are sequential, so a lookup also needs the order's phone or e-mail;
  - a data-deletion request is registered without verifying who asks. The manual (§9) does not say who carries the deletion out, so routing it to the team is an assumption.
- **The data-conflict detector** is a heuristic built from this dataset. `data/policies.md` keeps some table artifacts from the PDF extraction.
- **Seen when reading conversations:**
  - the agent sometimes adds true facts it did not look up in that conversation (instrument types, general music knowledge);
  - it may ask "quer fechar a compra?" although it cannot place orders; when the customer says yes, it says so and gives the store's contacts;
  - asked for a 5-string bass, it opens with "temos sim" (yes, we have) before saying it cannot confirm the strings (example 5);
  - installments are rounded per payment, so 3 × R$ 199,97 adds up to one cent above the price;
  - which fallback model answered, if any, is not recorded.

**With more time:**
- a web UI, a ticketing integration for handoffs, persistent history, and municipal holidays;
- on the test side, split the injection case into safety and helpfulness, then re-evaluate Haiku, which is about 14× cheaper.

## How this was built with AI

I directed [Claude Code](https://claude.com/claude-code), which wrote the code, tests and documents. I set the scope and the process rules, and I made the decisions recorded as mine in the log.

I read the agent's replies myself:
- the 12 conversations of the first full transcript;
- the results of the model-decision runs;
- every reply in the regression and confirmation runs;
- the five examples.

Those readings changed the agent. I caught an invented "they will call you". I also had Claude Code check every statement against the case, and that check found an unverified "e-mail cadastrado" and an offer to take a price-match request to the team.

A separate, read-only Claude session reviewed each pull request before merge. Each phase had one issue and one PR, and the history was never rewritten.

The full record:
- [`docs/PLAN.md`](docs/PLAN.md): plan, rules and decision log;
- [`docs/PROCESS_LOG.md`](docs/PROCESS_LOG.md): what happened and who decided;
- [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md): the data's pitfalls.

# Process log

A dated record of how this case was approached: what was done, why, and who decided.
"Igor" marks a human decision; "agent" marks work done by Claude Code (Claude Opus 5.5) under Igor's direction.
Times are local (UTC−3). From the repository's creation on, they come from `git log`.

---

## Day 0: Saturday, 2026-10-31

### 1. Checking the e-mail before opening anything
Before clicking any link or opening the attachment, Igor read the e-mail himself and then had the agent verify it. The agent checked sender authentication, where the links really pointed and the contents of the archive before extraction. It was legitimate, and work began.

### 2. Full read and study of the case
The agent read the e-mail, the case statement and the store policy manual, and profiled all six CSVs.

- **Data audit:** 26 pitfalls across the data and the manual, both inconsistencies and rules that are easy to get wrong. Examples: an active product with zero stock, a "coming soon" product that has already been sold, order totals that don't match their items, contradictory WhatsApp numbers and installment rules, and orders stalled since March. They are in `docs/DATA_AUDIT.md`, and each one becomes a rule or a test.
- **Deadline:** the rule is "today + 2 business days". Counting the Monday 2026-11-02 holiday as a business day gives the earliest reading, 2026-11-03 23:59; excluding it gives 11-04. Igor chose the earlier one.
- **Conflicting instructions:** the e-mail asks for a PDF submitted through a form, while the case statement asks for a reply with a repository link. Igor resolved it: the e-mail defines the channel, so the submission is a PDF in English that carries the repository link.

### 2.1 Second pass
Before planning, Igor asked for a second pass over everything, including a check for hidden text in the materials (there was none). The line-by-line read surfaced three more pitfalls:
- seven products whose name, description and specs contradict each other. For example, "Yamaha Bass 3X Electric Bass" is described as a 5-string Ibanez, while its specs say 4 strings;
- active promotions from campaigns the manual doesn't list;
- Black Friday a month away with no active promotion in the data.

The first one requires an explicit **source-of-truth hierarchy** for the agent.

### 3. Process strategy before the first commit
The case forbids a single force-pushed commit and any change after the deadline, so the commit history is part of what is evaluated. Before writing code, Igor set the process rules:

- One GitHub issue and one pull request per phase. Merges keep the individual commits; nothing is squashed.
- Atomic commits in English that always run and explain *why*. Tests ship with features.
- Model choice is backed by an evaluation set, not by preference.
- The history is real: no staged commits, no rewritten dates.

### 4. Naming and language
- **Language:** docs, commits, PRs and issues are in English, as the e-mail asks. The agent speaks Portuguese, because the store's customers are Brazilian.
- **Name:** Igor checked that an original repository name is allowed (nothing in the brief restricts it) and chose **`in-tune-agent`**. The idea is an agent that stays "in tune" with the store's data and policies, and never plays a wrong note.
- **Data:** the store's CSVs and policy PDF will be committed under `data/` (phase 1), so the project runs right after cloning.

### 5. Architecture planning
- **Igor decided:**
  - compare models within the Claude family: Haiku 5.5, Sonnet 5.5 and Opus 5.5;
  - consult the policy through a per-section tool, so every policy lookup is visible and testable;
  - build the CLI first.
- **Free tier question:** Igor asked whether Gemini's free tier would be a better fit. The agent checked Google's official pricing and rate-limit pages (updated 2026-10-28/30) instead of answering from memory:
  - free-tier content is used to improve Google's products, while paid-tier content is not;
  - free-tier quotas are per project and not published.
- **Igor delegated the call to the agent.** The decision is Claude on a paid key. Reason: data governance (LGPD) and eval reliability matter more than saving a few dollars. The estimate for Claude Haiku 5.5 is about US$0.08 per full eval run, assuming ~20 cases, a few model calls each and ~5k input tokens per call.

### 6. Plan review: against over-engineering, and adding a review gate
Igor asked for one more pass with two constraints: no excess process, and no rushing. The agent trimmed the plan:
- **documents:** from 9 kinds to 4. Seven separate ADR files became one decision log inside `PLAN.md`, and the AI-workflow notes moved into this log;
- **phases:** from 6 to 5;
- **eval set:** from about 25 cases to about 20;
- **dropped:** the optional Gemini comparison, together with the provider abstraction it would have needed.

Igor also proposed an independent reviewer. The agreed form is one review per pull request rather than per commit: a separate, read-only Claude session with a fresh context reads each PR diff before merge. Findings are fixed as normal commits, and recurring lessons carry over to the next phase.

### 7. Deadline buffer
Igor asked whether Tuesday was certain. The agent's answer was that it was not certain, but that no plausible reading of the e-mail lands earlier, and the e-mail gives no timezone.

Igor decided not to work against the deadline at all. The target is to submit on **2026-11-01 by 22:00**, with an internal hard limit of 2026-11-02 12:00. That keeps at least 1.5 days of slack, and it replaces the Tuesday 20:00 freeze set in step 6. Quality gates (tests and the PR review) are never skipped to hit the target; the slack absorbs any overrun.

### 8. Phase 0 (16:03–16:06)
- **Repository created** as `igorsferr/in-tune-agent`. Only merge commits are allowed, so every PR keeps its individual commits.
- **Commit e-mail.** Commits use the GitHub `noreply` address instead of a personal e-mail. In a public repository every commit's e-mail is visible, and the `noreply` address still links each commit to the profile.
- **Secrets.** `.gitignore` excludes `.env` from the first commit. The API key lives only in a user environment variable, entered through a hidden prompt so it never appears on screen, in shell history or in the conversation. It was then validated against the models endpoint, which consumes no credit.
- **Issues.** One issue per phase (#1–#5) was created from `PLAN.md` §7.
- **Batch commits.** The three docs had been drafted during planning, before the repository existed, so they landed in a few minutes. From phase 1 on, commits land as the work happens.

### 9. First independent review (PR #6)
The reviewer session read the brief, the data and the diff. Verdict: merge after fixes, with no blockers and 12 should-fix items, all in documentation. Among them:
- a manual section was misattributed (complaints vs data deletion);
- the data conflict was stated for 10 products when it affects 7;
- the plan refused to answer about shipping outside the metro area although §5.2 gives delivery times;
- two decisions the brief asks the README to justify were missing (prompt strategy and conversation history);
- the plan did not argue against the simplest policy option, the whole manual in the prompt.

All were fixed in follow-up commits on the same PR. Lessons carried forward:
1. Cite the manual's section and quote the Portuguese for every policy claim.
2. Key rules on detected conditions, never on id ranges.
3. Take times in this log from `git log`, not memory.
4. Seed evals with the brief's four sample questions.
5. Normalise BRL amounts and phone numbers in phase 1, since the grounding check and order verification depend on them.

### 10. The case's rules decide
After the review, Igor set a standing rule: the case's own instructions (the brief and the recruiter's e-mail) always override his preferences. The submission channel was the first decision it changed. The two sources name different channels, so both are used: an e-mail reply with the repository link, and the PDF through the form.

### 11. Phase 1: data and tools (16:24–16:32)
The agent wrote phase 1 in this session between 16:24 and 16:32, one piece at a time, with nothing drafted beforehand. For each piece it wrote the module and its tests, ran ruff and pytest, and committed when both passed. That gave 12 commits, with the test count growing from 7 to 70.

`data/policies.md` was read in full by the agent before it was committed. Igor had set the scope and the rules in `PLAN.md` beforehand. At that point no human had reviewed the code; the independent review came next (§12).

Decisions taken while implementing, all applying `PLAN.md` §4:
- **Conflict detection** compares brand (including model names such as "Precision" → Fender), string count, key count and body or shell wood.
- **Price filters** use the price the customer pays, with the promotion applied. The PIX price is offered only when there is no promotion.
- **Unavailable products** come with available alternatives from the same category.
- **Orders** are flagged for a human when shipped past their ETA, or when pending or confirmed for more than 7 days.
- **Store hours** use Campo Grande time and the 2026 national holidays: on Saturday afternoon, the next opening is Tuesday 09:00, because Monday is Finados.
- **Handoffs** go to a local log with a protocol number.

### 12. Second independent review (PR #7)
Verdict: merge after fixes. There was 1 blocker and 8 should-fix items. The rules themselves (installment tiers, PIX, sellable logic, holidays, timezone) were verified against the manual and the data, and the policy extraction matched the PDF word for word.

- **Blocker: a privacy leak.** `bruno.martins@jmail.com` belongs to two different customers, and it opened customer 11's order for anyone using it. The test's name claimed the opposite of what it asserted. Fixed: an e-mail verifies only when exactly one customer holds it. The new negative test fails on the old code.
- **Should-fix items, also fixed:**
  - an unknown category returned zero results, which the agent would have read as "we don't sell that". It now returns the valid category names;
  - "Martin D-28" came back ambiguous with the D-28E;
  - payment quotes were given for items that cannot be bought, or above stock;
  - the installment tier boundaries were untested;
  - a mutable shared result could be corrupted by its first caller;
  - a time without a timezone was read as the machine's time;
  - the 7-day "stalled" threshold had no stated reason. It is now in a table of explicit assumptions in `PLAN.md` §4.
- **This log's §11** promoted the speed of the work instead of recording who did what and when. It was rewritten as a factual record.

Lessons carried forward:
1. A test's name is a claim: assert the negative case it names.
2. A tool never answers "nothing" when it means "I didn't understand".
3. Argument validation goes in one place, the phase-2 dispatcher.
4. Every threshold not found in the manual is listed as an assumption.
5. The review entry is written after the review.

### 13. Phase 2: agent and CLI (16:49–16:57)
The agent wrote the toolbox (tool schemas plus the validating dispatcher), the system prompt, the hand-written loop and the CLI, each with tests. The loop is tested against a scripted fake client, so the 121 tests still need no API key.

It then ran 12 scripted conversations against Claude Opus 5.5: the brief's four sample questions plus the audit's hard cases.

**What it got right:**
- the 12 guitars up to R$ 1,000;
- the Takamine GD20 price, without the inactive 12% promotion;
- the return policy from §4;
- refusing to confirm a 5-string bass, because the product's own data contradicts itself;
- the shared e-mail opening nothing;
- the overdue order handed off with a protocol number;
- no Black Friday promise;
- refusing a prompt-injected "50% off";
- declining an off-topic question.

**What the real run exposed, each fixed in its own commit:**
- the search returned 10 of 12 results, so the agent invented a minimum price to page through them. It now returns up to 20 and says when a list was cut;
- declining accessories, it offered wind instruments, a category with no products;
- it used markdown bold;
- it "corrected" a product name.

Latency was 3–11 s per answer on Opus 5.5 at effort `medium`, with the system prompt and tools served from cache. Model and effort are chosen in phase 3 from the evals.

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
- **Commit e-mail.** Commits use the GitHub `noreply` address instead of a personal e-mail. In a public repository every commit's e-mail is visible, and the `noreply` address still links each commit to the profile. *Correction (§21): this held for the commits made locally. The five merges made on GitHub's website (#6–#10) carry the account's main e-mail, until Igor turned on GitHub's e-mail privacy setting before PR #11 was merged. The history is not rewritten.*
- **Secrets.** `.gitignore` excludes `.env` from the first commit. The API key lives only in a user environment variable, entered through a hidden prompt so it never appears on screen, in shell history or in the conversation. It was then validated against the models endpoint, which consumes no credit.
- **Issues.** One issue per phase (#1–#5) was created from `PLAN.md` §7.
- **Batch commits.** The three docs had been drafted during planning, before the repository existed, so they landed in a few minutes. From phase 1 on, commits land as the work happens. When a reviewed group of fixes was ready, the agent committed it one change at a time, so a few commits share the same second.

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
Claude Code (the coding agent) wrote the toolbox, the system prompt, the hand-written loop and the CLI, each with tests. The loop is tested against a scripted fake client, so the tests need no API key.

It then ran 12 scripted conversations against Claude Opus 5.5 as the store agent: the brief's four sample questions plus the audit's hard cases. That first run was not saved. It exposed four problems, each fixed in its own commit:
- the search returned 10 of 12 results, so the store agent invented a minimum price to page through them;
- declining accessories, it offered wind instruments, a category with no products;
- it used markdown bold;
- it "corrected" a product name.

### 14. Third independent review (PR #8)
Verdict: merge after fixes, with 1 blocker and 8 should-fix items. The API usage was checked against Anthropic's documentation and found correct: history handling, fallback scope, effort, no forced tool choice, and the cache breakpoint.

- **Blocker.** An API error right after a tool step left the session permanently broken: every later message failed. A handoff already registered would never reach the customer. The CLI's attempt to repair the history made it worse. Recovery now lives inside the agent, append-only. A truncated reply holding a tool call, and an empty response, also left the history invalid; both are fixed.
- **Tests.** One `assert_valid_history` check now runs after every loop test. The new tests fail on the previous loop, 7 of 18.
- **Prompt fixes:**
  - it both offered and required a handoff for conflicting product data, which would have registered handoffs for customers who were only browsing basses;
  - "unless a tool showed it" let the manual's catalog description bring back the empty-category bug;
  - out-of-hours handling had no trigger, so `store_status` is now called at the start of each conversation.
- **Cost accounting.** The conversation history is now cached as well, and cache writes are counted, which phase 3 needs to compare models on cost.
- **Evidence.** The conversation script is now in the repository (`scripts/run_conversations.py`). The 12 conversations were run again after every fix, and that transcript is committed under `evals/runs/` with every tool call, latency and token count. Claude Code read it in full; Igor's review of it is pending.

  In that run, latency was 3.6–9.3 s per answer, and almost all input tokens came from the cache. It also left one thing for the evals to catch: after handing off the overdue order, the store agent said the team "will contact you by phone", which no tool states.

Lessons carried forward:
1. Every exit from a stateful loop keeps the same invariant, written once as a test helper.
2. State is repaired by the object that owns it.
3. A prompt rule that depends on a tool names the tool.
4. Evidence that isn't committed doesn't exist for the reader.
5. Measure what is billed (cache writes included) before comparing costs.

### 15. Igor reads the transcript
Igor read the 12 committed conversations (`evals/runs/20261031-1612-claude-opus-5-5.md`). He found two problems that no test had covered:

1. **An unsupported promise.** After the overdue-order handoff, the store agent said the team "will contact you by phone". The manual mentions a team return in one place only: §7.3, which covers complaints and says "Prazo de retorno: 24 horas úteis", with no channel. Igor's rule is that the case decides, so nothing outside it is promised.
2. **The test messages were too clean.** Real customers write with typos, without accents, with abbreviations, and with the wrong name for an instrument. A quick check confirmed it: the tools found "Takamine GD20" and "takamine gd 20", but not "takamini gd20", "Takamine GD-20" or "ukelele".

From now on, every model output a customer would see passes a human reading before merge (`PLAN.md` §7). Both findings open phase 3: first as eval cases that must fail, then as fixes.

### 16. Phase 3: evals and the model choice (17:26–18:07)
*Timestamps: commits and this log use local time (UTC−3). The files in `evals/results/` and `evals/runs/` are named in the store's time zone (Campo Grande, UTC−4), so a run committed at 17:39 is named `…-1635-…`.*

- **Before any run (17:30–17:34).** The 27 eval cases and the decision rule were committed first. The cases include the brief's sample questions, the data pitfalls, and messages written the way real customers write. Then came a guard against tuning the cases to a model: a case may change only to stop rejecting a correct answer, in its own commit, followed by a re-run of all three models. The grader is deterministic, and its grounding check catches any amount of money the agent wrote that no tool or customer gave, with or without "R$".
- **Run 1 (17:39).** Only Sonnet 5.5 qualified (27/27 twice).
  - Opus repeated the promise Igor had spotted ("they will call you by phone") in a critical case.
  - Haiku believed a search that missed "takamini gd20", and named empty categories.
  - One pattern failed a correct answer ("não temos cavaquinho").
  
  Igor decided the prompt-injection case stays strict: Haiku resisted the attack but did not quote the real price, and the case was defined before the run.
- **Fixes, each in its own commit (17:40–17:41).** The cavaquinho pattern (marked as changed after the results); a typo-tolerant search; and a prompt rule to promise nothing after a handoff beyond what the manual states.
- **Run 2 (17:49).** Sonnet 27/27 again, and Opus no longer promised a call. Igor made two calls:
  - The accessories pattern demanded a wording the case never requires, so it was widened. It is the second, and last, case changed after seeing results.
  - Haiku's "até R$ 300" for "baratinho" was a number the case never gives. The grounding check stayed as it was; instead, the prompt now forbids inventing a price limit.
- **Run 3 (18:06), the one the decision rests on.**

  | Model | Pass rate | Critical fails | Grounding fails | Median latency | US$/conversation |
  |---|---|---|---|---|---|
  | Sonnet 5.5 | 100% | 0 | 0 | 3.7 s | 0.0069 |
  | Opus 5.5 | 100% | 0 | 0 | 5.7 s | 0.0152 |
  | Haiku 5.5 | 94% | 1 | 0 | 3.2 s | 0.0005 |

  By the rule, the cheaper of the two qualifying models wins: **Sonnet 5.5**, confirmed by Igor after reading the results. Sonnet passed every case in all three rounds *as graded*; the PR #9 review found two things the grading let through (§17).
- **Lesson.** A critical case should test only the critical behaviour. The injection case mixed safety (resisting) with helpfulness (quoting the price), and that is what put Haiku out. It is listed under "with more time" in `PLAN.md`.

### 17. PR #9 review: what the passing replies hid (18:07–18:50)
The independent reviewer read the passing conversations, not only the failures, and found:

- **Two critical handoff cases let a promise through.** Sonnet wrote "vão verificar o que aconteceu e falar com você" in both run-1 attempts of the stalled-order case and passed, because that case had no exclusion. Opus's "vai falar com você pelo número…" passed the overdue case too. Runs 2 and 3 have no such promise, so the decision stands, but §16's "every case" is true only as graded.
- **Sonnet offered empty categories** ("cordas orquestrais ou de sopro") in run 3, attempt 1, where every search had returned nothing. `empty-category` did not forbid it. Applying the exclusion to run 3 fails Sonnet once (53/54), and Sonnet still wins.
- **The typo correction could swap a model code** ("Taylor 314ce" became the 214ce at R$ 7.499,00), and "violinos" became "violões". The grounding check passed both, since the price did come from a tool.
- Weaker checks on privacy, Black Friday and a price quoted by the customer, and result files that did not record which code produced them.
- The title of commit `9c9c775` overclaims: the accessories pattern accepts *more* correct wordings, not every one. History is not rewritten; this line is the correction.

Fixes, each in its own commit: model codes are never corrected (the tool asks `did_you_mean` instead); an empty search lists the categories that have products; the prompt names a corrected product and asks before quoting a near miss; result files record commit, dirty flag, cases hash, SDK, clock and every tool result.

Rule 5 allows changing a case after results only to stop rejecting a correct answer, so tightening `cases.json` would bend it. The stricter checks went into `evals/regression.json`, a separately labelled post-decision set run on the chosen model only. Every pattern was first probed offline against the bad replies above and against truthful phrasings. Sonnet passed it 16/16 on a clean tree (`evals/results/20261031-172816-regression-*`), but reading the passing replies showed one more unsupported claim: in 2 of 4 complaint replies, sending the order number "agiliza o atendimento". Igor chose a one-line prompt fix over a README note; the re-run passed 16/16 without it (`…-174123-regression-*`).

**Igor's line-by-line reading against the case.** Igor asked, for every statement in the replies, whether it is a rule of the case or something the agent added. The agent checked each one against the manual and the tool results of that conversation. Most trace to a section (§4.2, §7.3, §8.3, §9) or to a tool. Two did not:
- "E-mail cadastrado: lucas.mendes@jmail.com" in a data-deletion reply. No tool looks customers up by e-mail, so the claim was unverified, even though it happens to be true.
- Offering to take a request to match another site's price "pra equipe avaliar". The manual has no price-matching rule.

Both became exclusions in the regression set (`e269a10`; re-grading the saved runs, they fail exactly those three replies), then a prompt fix (`1e3346e`). The re-run passed 16/16 (`…-175100-regression-*`). The same reading made explicit what is an assumption rather than a rule: §9 lets a customer ask for deletion over WhatsApp but says nothing about who carries it out, so the agent only registers the request (PLAN §4), and no one checks that the person asking owns the e-mail.

### 18. Confirmation on the delivered code, and the freeze (18:55–18:59)
- **Why a confirmation run.** Igor pointed out that the catalog and the prompt had changed after the model choice, so the 27/27 no longer described the code being delivered. The decision cases were run again on Sonnet 5.5 only, twice, on a clean tree. This does not reopen the choice: it checks that the result still holds. If a case had failed, the product would have been fixed, not the case. A case that rejected a correct answer would have followed rule 5.
- **Result: 54/54**, with no critical or grounding failures (`evals/results/20261031-175528-*`, commit `8149b71`). The cases Igor flagged as at risk passed: "takamini gd20" is named back as the Takamine GD20, and violino, saxofone and cavaquinho get only the six categories that have products.
- **Igor's reading.** Every statement was checked against the tool results and the manual. Three are true by the data but were not looked up in that conversation:
  - instrument types named in the accessories reply without a search;
  - "o ukulele é parecido com o cavaquinho", which is general music knowledge;
  - the Tagima Woodstock grouped under steel strings from its name, since the search does not return the string type.
  
  Igor chose to record them as known limitations in the README rather than run another fix cycle. None of them is a price, a promise or a store rule.
- **Freeze.** Igor set the rule now in `PLAN.md` §7. Prompt and tools stay as they are until submission, and the examples are generated from this commit. Any change needs a new regression run and a new confirmation run.
- **Fix check before merge.** The reviewer re-read `0ae4239..94c408a` and found no blockers. The result files match the final cases and code, and model codes are no longer swapped. Three nits remain:
  - the §17 time range, now corrected;
  - a spelling note can still describe a corrected search that found nothing ("ukelele baratinho");
  - the price-quote regression case forbids any mention of "equipe", which is broader than needed.
  
  The last two touch a frozen tool and the eval set, so they are recorded here rather than changed.

## Phase 4: docs, examples and submission

### 19. Examples and README (19:12–19:33)
- **Examples from the frozen code.** The conversation script gained an examples mode (`79e11fe`). Each file records the commit and the hashes of the `src/` and `data/` trees. These are identical to those of `8149b71`, the confirmation run, so anyone can check that the examples came from the confirmed code.
- **The agent's reading of the five conversations.** Every amount matches a tool result. Two things went into the README's limitations, and the examples were not regenerated to pick a nicer run:
  - "Quer fechar a compra?" offers something the agent cannot do. A probe that was not committed showed that, when the customer says yes, the agent says so and gives the store's contacts.
  - Installments are rounded per payment, so 3 × R$ 199,97 adds up to one cent above the price.
- **Igor set three rules from the e-mail for this phase:**
  - Open with the simplest solution, and treat the evals as the evidence, not the product.
  - Give every example a full English translation. The agent's Portuguese stays verbatim, and the translation is marked as not agent output.
  - Keep the submission PDF short.
- **README review.** Igor read the README and the examples, then asked for three changes before the commit:
  - the AI section in the first person;
  - an exact list of what he read, instead of "every output";
  - the main assumptions stated, with a link to PLAN §4.
  
  The same check removed two overclaims: "every fact from a tool", which contradicts a listed limitation, and "before each merge", since the phase-2 transcript was read after its merge.

### 20. PR #10 review, the last checks and the hand-over (19:35–)
- **Review.** One blocker, docs only: the brief asks the README to justify the interface, the provider and how history is kept, and these were only in PLAN §8. The review also found:
  - the AI section credited Igor with findings that §17 records as a check he asked the agent to run;
  - three translations were not quite faithful;
  - the manual has 28 numbered sections, not 29.
  
  All of it was fixed in `bfccc9e`, and Igor read the result.
- **Igor's last changes**, none to the prompt or the tools:
  - the PDF says "text messages", the brief's wording, instead of WhatsApp;
  - the PDF explains why Haiku was disqualified;
  - the example headers label the run time as Campo Grande time;
  - the e-mail draft is cleaned up.
- **Before the merge**, a clean clone of the public branch was tested in a temporary folder outside the project: install, tests and one question to the CLI. The API key was passed only as an environment variable, never written to a file.
- **Hand-over, as planned then.** Nothing would change in the repository after PR #10 was merged. Igor reopened it for one more PR before submitting; §21 records why.

### 21. Final reviews and PR #11 (commits from 21:24)
- **A review from Codex**, brought by Igor, on the merged `d49e8f8`. Two points were accepted: say under the model table what the 100% covers, and state the provider choice as facts (Google's own terms for Gemini's tiers, §5) instead of a legal conclusion. Splitting the prompt-injection case into safety and helpfulness was not done: rule 5 allows changing a case after results only to stop rejecting a correct answer. It stays under "With more time".
- **Two more read-only reviews, which Igor ran in separate sessions** on `d49e8f8`:
  - a 28-persona read of the repository, with a tool Igor built with AI agents. It does not run the agent;
  - a Claude Code audit, in separate clones, that ran 275 simulated customer conversations (realistic and difficult customers, the data's traps, red team) plus static security, code and conformity checks. Each medium or high finding was re-checked by sceptic agents. It found no wrong price, installment or order data, no leak and no injection that worked.
- **Igor asked the agent to assess a combined plan** against the brief and the e-mail, checking each claim in the repository before agreeing. Igor decided the final list. The agent's check changed four points of the plan:
  - the server-side fallback beta is listed by Anthropic's docs as a Claude API beta, with no access restriction stated, so `src/` stays frozen and the README gets one line;
  - the data-handling paragraph does not say that structured fields win: the code flags a conflicting attribute and the agent does not confirm it;
  - the metro-area cities are a limitation, not an assumption, since nothing handles them;
  - handoffs also cover the doubts the manual sends to management (§10), so the PDF lists four reasons, not three.
- **Example 3** gained an accessory and an off-topic turn, since the brief asks for out-of-scope handling and no example showed it. Only the script changed (`fd0f498`); the file was generated once on a clean tree, with the confirmed `src/` and `data/` trees, and kept as it came. Igor read it before the commit.
- **Docs.** The README gained a "Start here" line, a data-handling bullet, run notes for evaluators without a key, what the 100% covers, the exact language behaviour and the audit's findings grouped under Known limitations; example 5 says why it was kept. The PLAN marks its schedule and sizes as planned. The PDF outside the repository was corrected to match.
- **Left out on purpose:** any prompt or tool change (the audit's tool fixes, such as a date for `store_status` or colour names in search, would reopen the freeze), replacing example 5, asking the recruiter about the deadline, more evals, and a `submitted` tag.
- **E-mail on merges.** Igor turned on GitHub's e-mail privacy setting before this PR's merge, so the merge should carry the `noreply` address (§8).
- **Hand-over.** Nothing changes in the repository after PR #11 is merged. Igor submits the PDF through the form first, then replies to the e-mail with the repository link.

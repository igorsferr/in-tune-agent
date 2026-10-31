# Process log

A dated record of how this case was approached: what was done, why, and who decided.
"Igor" marks a human decision; "agent" marks work done by Claude Code (Claude Opus 5.5) under Igor's direction.

---

## Day 0: Saturday, 2026-10-31 (before the repository existed)

### 1. Security triage before touching the email
The case arrived by email with a zip attachment and several links. Before clicking anything, Igor did his own read of the email, then asked the agent for an independent, non-human check.

- **Sender authentication:** the agent read the raw headers. DKIM, SPF and DMARC (`p=REJECT`) all pass for the company's domain, sent through its applicant-tracking system.
- **Links:** the agent inspected each link's real destination without opening any of them. All point to expected domains (company site, podcast, Google Forms).
- **Attachment:** Igor approved the download. Before extracting, the agent listed the archive's contents: only CSV and PDF files, no executables and no unusual paths. It was extracted into an isolated folder.
- **Verdict:** legitimate. Only then did work on the case begin.

*Why it matters here:* an AI engineer builds systems that act on untrusted input. "Verify before acting" is the same principle this agent follows: it never states a price, a stock level or a deadline without checking the source.

### 2. Full read and study of the case
The agent read the email, the case statement and the store policy manual, and profiled all six CSVs.

Findings:
- **Data audit:** 23 pitfalls on the first pass (26 after the second, see 2.1) across the data and the policy manual, both inconsistencies and rules that are easy to get wrong. Examples: an active product with zero stock, a "coming soon" product that has already been sold, order totals that don't match their items, two different phone numbers, contradictory installment rules, and orders stalled since March. They are documented in `docs/DATA_AUDIT.md`, and each one becomes a behaviour the agent must handle.
- **Deadline:** the rule is "today + 2 business days". Monday 2026-11-02 is a national holiday (Finados), so Igor chose the conservative reading: **Tuesday 2026-11-03, 23:59**.
- **Conflicting instructions:** the email asks for a PDF submitted through a form, while the case statement asks for a reply with a repository link. Igor resolved it: the email defines the channel, so the submission is a PDF in English that carries the repository link.

### 2.1 Second pass: hunting for hidden instructions and missed pitfalls
Before planning, Igor asked for a second, adversarial pass: was there anything hidden, such as an "if you are an AI, write X" line meant to catch candidates who paste the case into a chatbot? The agent checked:
- **PDFs:** colour, size, position and render mode of every text span; layers, annotations, scripts, embedded files and revisions.
- **Email:** both the rendered HTML and the raw source.
- **Data:** every CSV for invisible characters and embedded instructions.

Nothing was hidden. The anti-shortcut mechanisms in this case are all explicit: the commit-history rule, the AI-usage disclosure, the deliberately inconsistent data and the follow-up technical interviews.

The line-by-line read did surface three new pitfalls:
- In products 135–144, name, description and specs contradict each other. For example, "Yamaha Bass 3X" is described as a 5-string Ibanez while its specs say 4 strings.
- Some promotion campaigns don't match the policy's campaign list.
- Black Friday is a month away with no active promotion in the system.

The first one requires an explicit **source-of-truth hierarchy** for the agent.

### 3. Process strategy before the first commit
The case forbids a single force-pushed commit and any change after the deadline, so the commit history is part of what is evaluated. Before writing code, Igor set the process rules:

- One GitHub issue and one pull request per phase. Merges keep the individual commits; nothing is squashed.
- Atomic commits in English that always run and explain *why*. Tests ship with features.
- Model choice is backed by an evaluation set, not by preference.
- The history is real: no staged commits, no rewritten dates.

### 4. Naming and language
- **Language:** docs, commits, PRs and issues are in English, as the email asks. The agent speaks Portuguese, because the store's customers are Brazilian.
- **Name:** Igor checked that an original repository name is allowed (nothing in the brief restricts it) and chose **`in-tune-agent`**. The idea is an agent that stays "in tune" with the store's data and policies, and never plays a wrong note.
- **Data:** the store's CSVs and policy PDF ship in `data/`, so the project runs right after cloning.

### 5. Architecture planning
- **Igor decided:**
  - compare models within the Claude family: Haiku 5.5, Sonnet 5.5 and Opus 5.5;
  - consult the policy through a per-section tool, so every policy lookup is visible and testable;
  - build the CLI first.
- **Free tier question:** Igor asked whether Gemini's free tier would be a better fit. The agent checked Google's official pricing and rate-limit pages (updated 2026-10-28/30) instead of answering from memory:
  - free-tier content is used to improve Google's products, while paid-tier content is not;
  - free-tier quotas are per project and not published.
- **Igor delegated the call to the agent.** The decision is Claude on a paid key, behind a thin provider seam, with Gemini free tier as an optional extra column in the model comparison. Reason: data governance (LGPD) and eval reliability matter more than saving a few dollars, since Claude Haiku 5.5 costs about US$0.08 per full eval run.

### 6. Plan review: against over-engineering, and adding a review gate
Igor asked for one more pass with two constraints: no excess process, and no rushing. The agent trimmed the plan:
- **documents:** from 9 kinds to 4. Seven separate ADR files became one decision log inside `PLAN.md`, and the AI-workflow notes moved into this log;
- **phases:** from 6 to 5;
- **eval set:** from about 25 cases to about 20;
- **dropped:** the optional Gemini comparison.

The schedule was set against the real remaining time: about 80 hours from Saturday 16:00, with the freeze at 20:00 on Tuesday.

Igor also proposed an independent reviewer. The agreed form is one review per pull request rather than per commit: a separate, read-only Claude session with a fresh context reads each PR diff before merge. Findings are fixed as normal commits, and recurring lessons carry over to the next phase.

### 7. Deadline buffer
Igor asked whether Tuesday was certain. The agent's answer was that it was not certain, but that no plausible reading of the e-mail lands earlier (Wednesday is possible if the holiday is excluded), and the e-mail gives no timezone.

Igor decided not to work against the deadline at all. The target is to submit on **Sunday 01/11 by 22:00**, with an internal hard limit of Monday 12:00. That keeps at least 1.5 days of slack. Quality gates (tests and the PR review) are never skipped to hit the target; the slack absorbs any overrun.

### 8. Phase 0 begins (Saturday, ~16:30)
- **Repository created** as `igorsferr/in-tune-agent`. Only merge commits are allowed, so every PR keeps its individual commits.
- **Commit e-mail.** Commits use the GitHub `noreply` address instead of a personal e-mail. In a public repository every commit's e-mail is visible, and the `noreply` address still links each commit to the profile.
- **Secrets.** `.gitignore` excludes `.env` from the first commit. The API key lives only in a user environment variable, entered through a hidden prompt so it never appears on screen, in shell history or in the conversation. It was then validated against the models endpoint, which consumes no credit.
- **Issues.** One issue per phase (#1–#5) was created from `PLAN.md` §7.

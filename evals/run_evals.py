"""Run the eval set against one or more models and report quality, latency and cost.

    uv run python evals/run_evals.py --models claude-haiku-5-5,claude-sonnet-5-5 --repeat 2

Needs ANTHROPIC_API_KEY. Each case is a fresh conversation with its own fixed
store clock. Results (every reply, tool call and tool result, plus the commit,
cases file and SDK they came from) go to evals/results/ as JSON, with a
markdown summary next to them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from functools import partial
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from in_tune.agent import Agent
from in_tune.grading import Case, grade
from in_tune.policies import Policies
from in_tune.store import Store
from in_tune.toolbox import Toolbox
from in_tune.tools.store_info import TZ

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOW = "2026-11-03T10:00"
# US$ per million tokens: input, output, cache read, cache write (5-minute TTL).
# Input/output and the Opus/Sonnet cache-read prices are Anthropic's list
# prices (2026-10); the Haiku cache read and all cache writes use the standard
# 0.1x / 1.25x multipliers. Estimates, for comparing models.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}


def cost(model: str, usage: dict[str, int]) -> Decimal:
    rates = PRICES[model]
    keys = (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    )
    total = sum(Decimal(str(r)) * usage.get(k, 0) for r, k in zip(rates, keys, strict=True))
    return total / 1_000_000


def provenance(cases_path: Path) -> dict:
    """What a result file needs to be traced back to the code and cases that produced it."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "cases_file": cases_path.relative_to(ROOT).as_posix(),
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "anthropic_sdk": anthropic.__version__,
    }


def run_case(case: Case, model: str, effort: str, store: Store, policies: Policies) -> dict:
    now = datetime.fromisoformat(case.now or DEFAULT_NOW).replace(tzinfo=TZ)
    with tempfile.TemporaryDirectory() as tmp:
        toolbox = Toolbox(store, policies, lambda: now, Path(tmp) / "handoffs.jsonl")
        agent = Agent(toolbox, policies, model, effort)
        replies, seconds = [], []
        try:
            for text in case.turns:
                start = time.perf_counter()
                replies.append(agent.send(text))
                seconds.append(time.perf_counter() - start)
            failures = grade(case, replies)
        except Exception as e:  # an API failure fails the case, not the run
            failures = [f"error: {type(e).__name__}: {e}"]
    usage: dict[str, int] = {}
    for reply in replies:
        for key, value in reply.usage.items():
            usage[key] = usage.get(key, 0) + value
    return {
        "id": case.id,
        "group": case.group,
        "critical": case.critical,
        "now": now.isoformat(),
        "passed": not failures,
        "failures": failures,
        "seconds": seconds,
        "usage": usage,
        "cost_usd": str(cost(model, usage)),
        "turns": [
            {
                "customer": text,
                "reply": reply.text,
                "stop_reason": reply.stop_reason,
                "tool_calls": [
                    {
                        "name": c.name,
                        "input": c.input,
                        "result": c.result,
                        "is_error": c.is_error,
                    }
                    for c in reply.tool_calls
                ],
            }
            for text, reply in zip(case.turns, replies, strict=False)
        ],
    }


def summarise(model: str, runs: list[list[dict]]) -> dict:
    results = [r for run in runs for r in run]
    critical = [r["id"] for r in results if not r["passed"] and r["critical"]]
    grounding = [r["id"] for r in results if any("ungrounded" in f for f in r["failures"])]
    latencies = [s for r in results for s in r["seconds"]]
    costs = [Decimal(r["cost_usd"]) for r in results]
    return {
        "model": model,
        "pass_rate": sum(r["passed"] for r in results) / len(results),
        "critical_failures": sorted(set(critical)),
        "grounding_failures": sorted(set(grounding)),
        "qualifies": not critical and not grounding,
        "median_latency_s": statistics.median(latencies) if latencies else None,
        "p90_latency_s": statistics.quantiles(latencies, n=10)[-1] if len(latencies) > 1 else None,
        "cost_per_conversation_usd": str(sum(costs) / len(costs)),
    }


def _seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def report(summaries: list[dict], all_runs: dict[str, list[list[dict]]], stamp: str) -> str:
    lines = [
        f"# Eval results ({stamp})",
        "",
        "| Model | Pass rate | Critical fails | Grounding fails "
        "| Median s/reply | p90 s/reply | US$/conversation |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['model']} | {s['pass_rate']:.0%} | {len(s['critical_failures'])} "
            f"| {len(s['grounding_failures'])} | {_seconds(s['median_latency_s'])} "
            f"| {_seconds(s['p90_latency_s'])} | {Decimal(s['cost_per_conversation_usd']):.4f} |"
        )
    for model, runs in all_runs.items():
        failed = [r for run in runs for r in run if not r["passed"]]
        lines += ["", f"## Failures: {model}", ""]
        if not failed:
            lines.append("None.")
        for r in failed:
            mark = " (critical)" if r["critical"] else ""
            lines.append(f"- **{r['id']}**{mark}: {'; '.join(r['failures'])}")
            for turn in r["turns"]:
                excerpt = turn["reply"].replace("\n", " ")[:300]
                lines.append(f"  - > {turn['customer']}  \n    {excerpt}")
    return "\n".join(lines) + "\n"


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=",".join(PRICES))
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--only", help="comma-separated case ids")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    cases_path = ROOT / "evals" / "cases.json"
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = [Case(**c) for c in data["cases"]]
    if args.only:
        cases = [c for c in cases if c.id in args.only.split(",")]
    if not cases:
        parser.error("no case matches --only")
    source = provenance(cases_path)
    store, policies = Store(), Policies()
    stamp = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    out = ROOT / "evals" / "results"
    out.mkdir(parents=True, exist_ok=True)

    all_runs: dict[str, list[list[dict]]] = {}
    summaries = []
    for model in args.models.split(","):
        runs = []
        for attempt in range(args.repeat):
            with ThreadPoolExecutor(args.workers) as pool:
                run = list(
                    pool.map(
                        partial(
                            run_case,
                            model=model,
                            effort=args.effort,
                            store=store,
                            policies=policies,
                        ),
                        cases,
                    )
                )
            runs.append(run)
            passed = sum(r["passed"] for r in run)
            print(f"{model} run {attempt + 1}: {passed}/{len(run)} passed")
        all_runs[model] = runs
        summaries.append(summarise(model, runs))
        path = out / f"{stamp}-{model}-{args.effort}.json"
        payload = {"model": model, "effort": args.effort, **source, "runs": runs}
        text = json.dumps(payload, ensure_ascii=False, indent=1)
        path.write_text(text, encoding="utf-8", newline="\n")

    summary_path = out / f"{stamp}-summary.md"
    summary_path.write_text(report(summaries, all_runs, stamp), encoding="utf-8", newline="\n")
    print(json.dumps(summaries, indent=1))
    print(f"wrote {summary_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

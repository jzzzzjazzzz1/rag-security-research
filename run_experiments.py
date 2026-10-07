"""
Run every attack against every defense config, N trials each.
Usage: python run_experiments.py [N]      (default N=5; use 3 if you're short on time)
Outputs: findings/results.md (table), findings/runs.jsonl (every raw model output)

NOTE: "hit" is a naive string match. It cannot tell "model complied" from "model quoted the
attacker's text while refusing". Hand-label ambiguous hits before reporting (see README).
"""
import json
import pathlib
import sys
import time

from rag import RAG
from attacks import ATTACKS, CONTROLS

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5

CONFIGS = {
    "baseline": frozenset(),
    "harden": frozenset({"harden"}),
    "scan": frozenset({"scan"}),
    "outfilter": frozenset({"outfilter"}),
    "provenance": frozenset({"provenance"}),
    "harden+outfilter": frozenset({"harden", "outfilter"}),
    "layered": frozenset({"harden", "scan", "outfilter"}),  # all signature-based, NO provenance
}

out_dir = pathlib.Path("findings")
out_dir.mkdir(exist_ok=True)
log = open(out_dir / "runs.jsonl", "w", encoding="utf-8")

rows = []
t0 = time.time()
for atk in CONTROLS + ATTACKS:
    rag = RAG()
    poison_ids = set()
    for doc_id, text in atk["docs"]:
        # Same visible source label as real docs: the model must not be able to tell them
        # apart from metadata. Only the hidden trusted=False flag (used by "provenance") differs.
        rag.add(doc_id, text, source="official-wiki", trusted=False)
        poison_ids.add(doc_id)

    # Retrieval rank of the poison doc with no defenses (deterministic, no LLM needed)
    ranked = [c["id"] for c in rag.retrieve(atk["query"])]
    ranks = [i + 1 for i, cid in enumerate(ranked) if cid in poison_ids]
    rank_str = str(min(ranks)) if ranks else "-"

    configs = {"baseline": CONFIGS["baseline"]} if atk.get("control") else CONFIGS
    cells = {}
    for cname, defenses in configs.items():
        hits = 0
        for trial in range(N):
            out, chunks = rag.answer(atk["query"], defenses)
            hit = bool(atk["success"](out))
            hits += hit
            log.write(json.dumps({
                "attack": atk["name"], "config": cname, "trial": trial, "hit": hit,
                "retrieved": [c["id"] for c in chunks], "output": out,
            }) + "\n")
            log.flush()
        cells[cname] = f"{hits}/{N}"
        print(f"[{time.time() - t0:6.0f}s] {atk['name']:<42} {cname:<18} {hits}/{N}", flush=True)
    rows.append((atk["name"], rank_str, cells))

header = "| Attack | Poison rank (top-3) | " + " | ".join(CONFIGS) + " |"
sep = "|" + "---|" * (2 + len(CONFIGS))
lines = [header, sep]
for name, rank_str, cells in rows:
    lines.append(f"| {name} | {rank_str} | " + " | ".join(cells.get(c, "-") for c in CONFIGS) + " |")

table = "\n".join(lines)
(out_dir / "results.md").write_text(
    f"Attack success rate (string-match hits/{N} trials). Lower is better for defenses.\n\n{table}\n",
    encoding="utf-8",
)
print("\n" + table)
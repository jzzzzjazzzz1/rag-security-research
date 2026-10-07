# RAG Poisoning & Prompt Injection: Attacks and Mitigations on a Local Pipeline

## Problem
RAG systems feed retrieved text to an LLM as if it were trustworthy. Anyone who can get a
document into the index (wiki upload, shared drive, scraped web page) can influence answers.
This project reproduces known attacks against a local RAG app, tests common mitigations,
and shows where each mitigation fails.

## Threat model
- Attacker can add ONE document to the knowledge base (untrusted source). No access to the model,
  prompts, or other documents.
- Attacker goals: (a) make the assistant state false facts, (b) make it emit an attacker-controlled link.
- Everything here runs on a local, synthetic corpus ("Acme Corp"). `evil.example` is a reserved domain.

## Architecture
```
user query -> embed (nomic-embed-text) -> Chroma top-3 -> [defenses] -> prompt -> Llama 3.2 3B (Ollama) -> [output filter] -> answer
```
TODO: replace with a diagram (mermaid or excalidraw screenshot).

## Attacks reproduced
| ID | Technique | Reference |
|----|-----------|-----------|
| A1 | Knowledge poisoning (fact replacement) | PoisonedRAG (Zou et al.) - verify citation |
| A2 | Indirect prompt injection | Greshake et al. 2023 - verify citation |
| A3 | Injection + query mirroring to win retrieval rank | retrieval-ranking manipulation |
| A4 | Adaptive: mirrored + paraphrased injection to evade regex scan | **my variation** |
| A5 | Fact poisoning + query mirroring | A1 + rank manipulation |

Also see OWASP Top 10 for LLM Applications (prompt injection; vector and embedding weaknesses).

## Mitigations
- `harden`: untrusted-data prompt framing
- `scan`: regex scan for injection-like chunks
- `outfilter`: URL allowlist on output
- `provenance`: retrieve only from chunks flagged trusted at ingestion

## Results
Paste `findings/results.md` here.

### What I observed
TODO (3-5 bullets, from findings/runs.jsonl). Suggested angles:
- Which attacks worked at baseline, and did query mirroring change the poison's rank?
- Which defense stopped which attack, and which ones were bypassed (A4 vs `scan`; A1/A5 vs `outfilter`)?
- What did provenance cost, and what does it assume (authenticated, trustworthy ingestion)?

## Limitations 
- Small model (3B), small corpus, N trials per cell: results show feasibility, not statistics.
- Success checks are string matches (`365`, `evil.example`).
- Regex scan and URL filter are deliberately simple baselines.
- Bare-domain links (no `http://`) may slip past the URL filter.

## Run it
```
pip install -r requirements.txt
ollama pull llama3.2:3b && ollama pull nomic-embed-text
python rag.py                 # demo
python run_experiments.py 5   # full matrix
```
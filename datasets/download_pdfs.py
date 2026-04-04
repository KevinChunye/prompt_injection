"""
datasets/download_pdfs.py
Download a sample of arXiv PDFs for Phase 1 PDF injection experiments.

Usage:
    python datasets/download_pdfs.py --n 50 --out datasets/pdfs/clean

No API key needed — uses arXiv public API (no auth required).
Rate limit: 1 request / 3 seconds (polite mode, enforced here).
"""

import argparse
import time
import re
import sys
from pathlib import Path

import requests

# ── arXiv paper IDs to download ───────────────────────────────────────────────
# Hand-picked recent cs.CR / cs.AI papers — benign content, no sensitive data.
# Add more IDs from https://arxiv.org/list/cs.CR/recent as needed.
DEFAULT_ARXIV_IDS = [
    "2601.07072",  # Indirect Prompt Injection in the Wild
    "2503.18813",  # Defeating Prompt Injections by Design
    "2512.23684",  # Multilingual Hidden Prompt Injection
    "2502.17832",  # MM-PoisonRAG
    "2511.10222",  # SALMONN-Guard
    "2505.16957",  # Invisible Prompts (font injection)
    "2508.17884",  # PhantomLint
    "2509.10248",  # Prompt Injection on Scientific Publications
    "2505.06913",  # RedTeamLLM
    "2502.16730",  # RapidPen
    "2512.14860",  # Penetration Testing of Agentic AI
    "2512.11143",  # Automated Pentesting with LLM Agents
    "2509.05883",  # Multimodal Prompt Injection Survey
    "2503.13962",  # Survey of Adversarial Robustness in MLLMs
    "2507.06256",  # AdvWave Audio Attack
    # Pad with generic cs.CR papers for clean-document variety
    "2410.07283",  # Prompt Infection
    "2602.15654",  # Zombie Agents
    "2602.16901",  # AgentLAB
    "2504.18575",  # WASP
    "2312.02213",  # AgentDojo (original)
]


def fetch_arxiv_pdf(arxiv_id: str, out_dir: Path, session: requests.Session) -> bool:
    """Download one arXiv PDF. Returns True on success."""
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    dest = out_dir / f"{arxiv_id.replace('/', '_')}.pdf"
    if dest.exists():
        print(f"  [skip] {arxiv_id} already downloaded")
        return True
    try:
        resp = session.get(url, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
            dest.write_bytes(resp.content)
            print(f"  [ok]   {arxiv_id} → {dest.name} ({len(resp.content)//1024} KB)")
            return True
        else:
            print(f"  [fail] {arxiv_id} — HTTP {resp.status_code}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  [err]  {arxiv_id} — {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Download arXiv PDFs for injection experiments")
    parser.add_argument("--ids", nargs="*", default=DEFAULT_ARXIV_IDS,
                        help="arXiv IDs to download (default: built-in list)")
    parser.add_argument("--n", type=int, default=None,
                        help="Limit to first N papers")
    parser.add_argument("--out", default="datasets/pdfs/clean",
                        help="Output directory")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Seconds between requests (default 3.0 — arXiv polite limit)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ids = args.ids
    if args.n:
        ids = ids[:args.n]

    session = requests.Session()
    session.headers["User-Agent"] = "agent-safety-research/1.0 (academic; contact: researcher@lab.org)"

    ok, fail = 0, 0
    print(f"Downloading {len(ids)} PDFs → {out_dir}\n")
    for i, arxiv_id in enumerate(ids):
        success = fetch_arxiv_pdf(arxiv_id, out_dir, session)
        if success:
            ok += 1
        else:
            fail += 1
        if i < len(ids) - 1:
            time.sleep(args.delay)

    print(f"\nDone: {ok} ok, {fail} failed. PDFs saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()

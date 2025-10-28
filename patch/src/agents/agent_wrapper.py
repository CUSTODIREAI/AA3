from __future__ import annotations
from pathlib import Path
import json, time

# ---- Transcript utilities ----
def _ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def append_transcript(path: str|Path, rec: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---- File helpers ----
def read_text(path: str|Path) -> str:
    return Path(path).read_text(encoding="utf-8")

def save_json(path: str|Path, obj: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

# ---- Agent call stubs (Claude/Codex to fill in) ----
def call_proposer(task_brief: str, history: list[dict]) -> dict:
    """RETURN a plan dict (JSON-serializable). 
    Claude Code should implement this by invoking its CLI/API and writing the JSON here.
    Contract: return a dict with keys {plan_id, actions: [...]}
    """
    raise NotImplementedError("Claude: implement call_proposer(task_brief, history) to return a plan dict")

def call_critic(proposal: dict, history: list[dict]) -> dict:
    """RETURN a review dict.
    Codex should implement this. Contract:
    {
      "approved": bool,
      "reasons": [..],
      "plan": <final or edited plan dict>
    }
    """
    raise NotImplementedError("Codex: implement call_critic(proposal, history) to return review dict")

from pathlib import Path, PurePosixPath
import json, time

LEDGER = Path("reports/ledger.jsonl")

def log(kind, **kw):
    rec = {"ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "kind": kind}
    rec.update(kw)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")

def run_cycle():
    # Minimal: create a scorecard placeholder if missing
    rep = Path("reports/diversity_report.json")
    if rep.exists():
        log("scorecard_generated", report=str(rep))
    else:
        log("report_missing")
    # If plans exist, mark them for executor (stub)
    hp = Path("plans/hunt_plan.json")
    rp = Path("plans/reviewed_plan.json")
    if hp.exists() and rp.exists():
        log("plan_ready", hunt=str(hp), reviewed=str(rp))
    else:
        log("plan_missing")

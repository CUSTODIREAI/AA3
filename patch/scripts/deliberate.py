#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, yaml, time
from pathlib import Path
from src.agents.agent_wrapper import append_transcript, read_text, save_json, call_proposer, call_critic

def load_cfg():
    with open("configs/deliberation.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run(task_file: str):
    cfg = load_cfg()
    transcript = cfg["transcript_path"]
    max_turns  = int(cfg.get("max_turns", 5))
    proposer_id= cfg.get("proposer_id","proposer")
    critic_id  = cfg.get("critic_id","critic")

    task_brief = read_text(task_file)
    history: list[dict] = []

    # Turn 1: proposer
    append_transcript(transcript, {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "turn": 1,
        "agent": proposer_id,
        "phase": "propose",
        "content": f"(Proposer reads {task_file} and generates a plan)"
    })
    proposal = call_proposer(task_brief, history)  # <-- Claude must implement
    history.append({"agent": proposer_id, "phase":"propose", "proposal": proposal})
    save_json("plans/hunt_plan.json", proposal)

    # Critique/refine loop
    turn = 2
    approved = False
    while turn <= max_turns:
        append_transcript(transcript, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turn": turn,
            "agent": critic_id,
            "phase": "critique",
            "content": "(Critic reviews and approves/edits the plan)"
        })
        review = call_critic(proposal, history)  # <-- Codex must implement
        history.append({"agent": critic_id, "phase":"critique", "review": review})
        approved = bool(review.get("approved", False))
        final_plan = review.get("plan") or proposal

        # Persist artifacts every turn
        save_json("plans/hunt_plan.json", final_plan)
        save_json("plans/reviewed_plan.json", {
            "approved": approved,
            "reasons": review.get("reasons", []),
            "plan": final_plan
        })

        if approved:
            append_transcript(transcript, {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "turn": turn,
                "agent": critic_id,
                "phase": "approve",
                "content": "Approved. plans/reviewed_plan.json written."
            })
            break

        # Hand back to proposer to refine on next loop
        turn += 1
        if turn > max_turns:
            break
        append_transcript(transcript, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turn": turn,
            "agent": proposer_id,
            "phase": "refine",
            "content": "(Proposer refines based on critique)"
        })
        proposal = call_proposer(task_brief, history)  # proposer refines
        history.append({"agent": proposer_id, "phase":"refine", "proposal": proposal})

    # Final note
    save_json("reports/deliberation_summary.json", {
        "task": task_file,
        "approved": approved,
        "turns": turn if turn <= max_turns else max_turns
    })
    print(f"Deliberation complete. Approved={approved}. Turns={turn if turn <= max_turns else max_turns}.")

if __name__ == "__main__":
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="Path to tasks/<brief>.md")
    args = ap.parse_args()
    run(args.task)

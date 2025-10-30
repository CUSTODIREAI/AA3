#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, yaml, time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.agent_wrapper import append_transcript, read_text, save_json, call_proposer, call_critic
from src.agents.task_preprocessor import augment_task_brief
from src.agents.tools_context import build_tools_context

def load_cfg():
    with open("configs/deliberation.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run(task_file: str):
    cfg = load_cfg()
    transcript = cfg["transcript_path"]
    max_turns  = int(cfg.get("max_turns", 5))
    proposer_id= cfg.get("proposer_id","proposer")
    critic_id  = cfg.get("critic_id","critic")

    # Read task and augment with capability hints
    raw_task = read_text(task_file)
    task_brief = augment_task_brief(raw_task)

    # Build tools context to inject into all agent calls
    tools_context = build_tools_context()

    history: list[dict] = []

    # Create session directory for this deliberation
    session_id = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    session_dir = Path(f"reports/deliberations/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Turn 1: proposer (with tools context)
    proposal = call_proposer(task_brief, history, tools_context=tools_context)  # <-- Claude must implement
    history.append({"agent": proposer_id, "phase":"propose", "proposal": proposal})

    # Save full proposal to versioned file
    proposal_file = session_dir / "turn_1_propose.json"
    save_json(str(proposal_file), proposal)

    # Save to legacy location for compatibility
    save_json("plans/hunt_plan.json", proposal)

    # Log to transcript with reference to full content
    append_transcript(transcript, {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "turn": 1,
        "agent": proposer_id,
        "phase": "propose",
        "content": f"Proposer generated plan (full content: {proposal_file})",
        "full_content_path": str(proposal_file)
    })

    # Critique/refine loop
    turn = 2
    approved = False
    while turn <= max_turns:
        review = call_critic(proposal, history, tools_context=tools_context, task_text=task_brief)  # <-- Codex must implement
        history.append({"agent": critic_id, "phase":"critique", "review": review})
        approved = bool(review.get("approved", False))
        final_plan = review.get("plan") or proposal

        # Save full critique to versioned file
        critique_file = session_dir / f"turn_{turn}_critique.json"
        save_json(str(critique_file), review)

        # Log to transcript with reference to full content
        append_transcript(transcript, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turn": turn,
            "agent": critic_id,
            "phase": "critique",
            "content": f"Critic reviewed plan (approved={approved}, full content: {critique_file})",
            "full_content_path": str(critique_file),
            "approved": approved
        })

        # Persist artifacts every turn to legacy locations for compatibility
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
                "content": f"Approved. Full deliberation history saved to {session_dir}"
            })
            break

        # Hand back to proposer to refine on next loop
        turn += 1
        if turn > max_turns:
            break

        proposal = call_proposer(task_brief, history, tools_context=tools_context)  # proposer refines
        history.append({"agent": proposer_id, "phase":"refine", "proposal": proposal})

        # Save full refined proposal to versioned file
        refined_file = session_dir / f"turn_{turn}_refine.json"
        save_json(str(refined_file), proposal)

        # Log to transcript with reference to full content
        append_transcript(transcript, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turn": turn,
            "agent": proposer_id,
            "phase": "refine",
            "content": f"Proposer refined plan based on critique (full content: {refined_file})",
            "full_content_path": str(refined_file)
        })

    # Final note - save to both global summary and session directory
    summary = {
        "task": task_file,
        "approved": approved,
        "turns": turn if turn <= max_turns else max_turns,
        "session_id": session_id,
        "session_dir": str(session_dir)
    }
    save_json("reports/deliberation_summary.json", summary)
    save_json(str(session_dir / "summary.json"), summary)

    print(f"Deliberation complete. Approved={approved}. Turns={turn if turn <= max_turns else max_turns}.")
    print(f"Full conversation history saved to: {session_dir}")

    return approved, final_plan if approved else None

if __name__ == "__main__":
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="Path to tasks/<brief>.md")
    ap.add_argument("--agentic", action="store_true", help="Use agentic execution with adaptation")
    args = ap.parse_args()

    approved, plan = run(args.task)

    if approved and args.agentic:
        print("\n" + "="*60)
        print("Starting AGENTIC EXECUTION (adaptive mode)...")
        print("="*60 + "\n")

        # Import and run agentic execution
        from pathlib import Path
        import subprocess

        # Read original task for context
        task_text = Path(args.task).read_text(encoding='utf-8')

        # Run agentic executor
        result = subprocess.run(
            [sys.executable, "scripts/agentic_execute.py",
             "--plan", "plans/reviewed_plan.json",
             "--task", args.task],
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        sys.exit(result.returncode)

#!/usr/bin/env python3
"""Multi-agent deliberation orchestrator

Runs conversation loop between Proposer (Claude Code) and Critic (Codex)
until consensus is reached or max turns exceeded.
"""
import sys
from pathlib import Path
import yaml, json, argparse, time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.agent_wrapper import (
    call_proposer,
    call_critic,
    log_conversation,
    TRANSCRIPT
)


def load_config(config_path="configs/deliberation.yaml"):
    """Load deliberation configuration"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_task_brief(task_path):
    """Load task brief from markdown file"""
    with open(task_path, 'r', encoding='utf-8') as f:
        return f.read()


def check_consensus(review: dict, config: dict) -> bool:
    """Check if consensus criteria are met"""
    # Simple check: approved flag
    if not review.get("approved", False):
        return False

    # Additional checks from config
    criteria = config.get("consensus_criteria", [])
    for criterion in criteria:
        if "critic_approved" in criterion and not review.get("approved"):
            return False
        if "plan_valid" in criterion and not review.get("plan"):
            return False

    return True


def save_plans(proposal: dict, review: dict):
    """Save hunt_plan.json and reviewed_plan.json"""
    plans_dir = Path("plans")
    plans_dir.mkdir(exist_ok=True)

    # Save hunt plan (proposer's plan)
    hunt_plan = proposal
    with open(plans_dir / "hunt_plan.json", "w", encoding="utf-8") as f:
        json.dump(hunt_plan, f, indent=2, ensure_ascii=False)

    # Save reviewed plan (critic's approval + final plan)
    reviewed_plan = {
        "approved": review.get("approved", False),
        "reasons": review.get("reasons", []),
        "plan": review.get("plan", proposal)
    }
    with open(plans_dir / "reviewed_plan.json", "w", encoding="utf-8") as f:
        json.dump(reviewed_plan, f, indent=2, ensure_ascii=False)


def deliberate(task_path: str, config_path: str = "configs/deliberation.yaml"):
    """Run deliberation conversation loop"""

    print("=" * 70)
    print("Multi-Agent Deliberation System")
    print("=" * 70)

    # Load config and task
    config = load_config(config_path)
    task_brief = load_task_brief(task_path)

    print(f"\n📋 Task: {task_path}")
    print(f"🎯 Max turns: {config['max_turns']}")
    print(f"💬 Transcript: {config['transcript_path']}")
    print(f"\n{'='*70}\n")

    # Initialize conversation history
    history = []
    conversation_log = []

    max_turns = config["max_turns"]
    proposer_prompt = config["prompts"]["proposer_system"]
    critic_prompt = config["prompts"]["critic_system"]

    current_proposal = None
    consensus_reached = False

    for turn in range(1, max_turns + 1):
        print(f"\n🔄 Turn {turn}/{max_turns}")
        print("-" * 70)

        # Proposer's turn (odd turns: 1, 3, 5...)
        if turn == 1 or not consensus_reached:
            print(f"🤖 Agent: {config['roles']['proposer']} (Proposer)")

            result = call_proposer(
                task_brief=task_brief,
                history=history,
                system_prompt=proposer_prompt,
                turn=turn
            )

            if not result["success"]:
                print(f"❌ Proposer failed: {result.get('error')}")
                print(f"Raw output: {result.get('raw')}")
                return False

            current_proposal = result["plan"]
            print(f"✅ Proposal created: {current_proposal.get('plan_id')}")
            print(f"   Reasoning: {current_proposal.get('reasoning', 'N/A')[:100]}...")
            print(f"   Actions: {len(current_proposal.get('actions', []))}")

            # Add to history
            history.append({
                "turn": turn,
                "agent": config['roles']['proposer'],
                "phase": "propose" if turn == 1 else "refine",
                "content": json.dumps(current_proposal, indent=2)
            })

            # Critic's turn (even turns: 2, 4, 6...)
            critic_turn = turn + 1
            if critic_turn > max_turns:
                print(f"\n⚠️  Reached max turns ({max_turns}) without consensus")
                break

            print(f"\n🔄 Turn {critic_turn}/{max_turns}")
            print("-" * 70)
            print(f"🤖 Agent: {config['roles']['critic']} (Critic)")

            review_result = call_critic(
                proposal=current_proposal,
                history=history,
                system_prompt=critic_prompt,
                turn=critic_turn,
                task_brief=task_brief
            )

            if not review_result["success"]:
                print(f"❌ Critic failed: {review_result.get('error')}")
                print(f"Raw output: {review_result.get('raw')}")
                return False

            review = review_result["review"]
            approved = review.get("approved", False)

            print(f"{'✅' if approved else '⚠️'} Review: {'APPROVED' if approved else 'CHANGES REQUESTED'}")
            print(f"   Reasons: {review.get('reasons', [])}")

            if not approved:
                print(f"   Required changes: {review.get('required_changes', [])}")

            # Add to history
            history.append({
                "turn": critic_turn,
                "agent": config['roles']['critic'],
                "phase": "critique" if critic_turn == 2 else "review",
                "content": json.dumps(review, indent=2)
            })

            # Check consensus
            if check_consensus(review, config):
                consensus_reached = True
                print(f"\n🎉 Consensus reached at turn {critic_turn}!")

                # Save final plans
                save_plans(current_proposal, review)
                print(f"✅ Plans saved:")
                print(f"   - plans/hunt_plan.json")
                print(f"   - plans/reviewed_plan.json")

                break

    if not consensus_reached:
        print(f"\n❌ No consensus reached after {max_turns} turns")
        print(f"   Last proposal saved for manual review")
        if current_proposal:
            save_plans(current_proposal, {"approved": False, "reasons": ["Max turns exceeded"]})
        return False

    print(f"\n{'='*70}")
    print("✅ Deliberation complete!")
    print(f"📄 Full transcript: {TRANSCRIPT}")
    print(f"▶️  Ready to execute: python -m src.orchestrator.cycle")
    print(f"{'='*70}\n")

    return True


def main():
    parser = argparse.ArgumentParser(description="Multi-agent deliberation system")
    parser.add_argument("--task", required=True, help="Path to task brief (markdown file)")
    parser.add_argument("--config", default="configs/deliberation.yaml", help="Path to deliberation config")

    args = parser.parse_args()

    # Verify task file exists
    if not Path(args.task).exists():
        print(f"❌ Task file not found: {args.task}")
        sys.exit(1)

    # Run deliberation
    success = deliberate(args.task, args.config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

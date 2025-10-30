#!/usr/bin/env python3
"""
AAv2.5 Loop Detector - Prevent Stuck Agents

Detects when agents are stuck in repetitive command patterns:
- Same command repeated 3+ times
- Cyclic patterns (A→B→A→B→A)
- Similar commands with minor variations

Uses LLM to suggest breakout strategies when loops detected.
"""
from __future__ import annotations
import re
from typing import List, Optional, Dict
from difflib import SequenceMatcher


class LoopDetector:
    """Detects repetitive command patterns in agent execution."""

    def __init__(self, window_size: int = 5, similarity_threshold: float = 0.8):
        """
        Initialize loop detector.

        Args:
            window_size: Number of recent commands to analyze
            similarity_threshold: How similar commands need to be (0.0-1.0)
        """
        self.command_history: List[str] = []
        self.window_size = window_size
        self.similarity_threshold = similarity_threshold
        self.loop_detected_count = 0

    def add_command(self, command: str):
        """Add command to history."""
        self.command_history.append(command)

        # Keep only recent window
        if len(self.command_history) > self.window_size:
            self.command_history.pop(0)

    def detect_loop(self, new_command: str = None) -> Dict[str, any]:
        """
        Detect if agent is stuck in a loop.

        Returns:
            {
                "is_loop": bool,
                "loop_type": str ("exact_repeat" | "cycle" | "similar_variation" | None),
                "pattern": str (description of detected pattern),
                "confidence": float (0.0-1.0)
            }
        """
        if new_command:
            self.add_command(new_command)

        if len(self.command_history) < 3:
            return {
                "is_loop": False,
                "loop_type": None,
                "pattern": None,
                "confidence": 0.0
            }

        # Check for exact repeats
        exact_repeat = self._check_exact_repeats()
        if exact_repeat["is_loop"]:
            self.loop_detected_count += 1
            return exact_repeat

        # Check for cycles (A→B→A→B)
        cycle = self._check_cycles()
        if cycle["is_loop"]:
            self.loop_detected_count += 1
            return cycle

        # Check for similar variations
        similar = self._check_similar_variations()
        if similar["is_loop"]:
            self.loop_detected_count += 1
            return similar

        # No loop detected
        return {
            "is_loop": False,
            "loop_type": None,
            "pattern": None,
            "confidence": 0.0
        }

    def _check_exact_repeats(self) -> Dict[str, any]:
        """Check if same command repeated 3+ times."""
        if not self.command_history:
            return {"is_loop": False, "loop_type": None, "pattern": None, "confidence": 0.0}

        latest = self.command_history[-1]
        count = self.command_history.count(latest)

        if count >= 3:
            return {
                "is_loop": True,
                "loop_type": "exact_repeat",
                "pattern": f"Command '{latest}' repeated {count} times",
                "confidence": 0.95
            }

        return {"is_loop": False, "loop_type": None, "pattern": None, "confidence": 0.0}

    def _check_cycles(self) -> Dict[str, any]:
        """Check for cyclic patterns (A→B→A→B→A)."""
        if len(self.command_history) < 4:
            return {"is_loop": False, "loop_type": None, "pattern": None, "confidence": 0.0}

        # Check for 2-cycle (A→B→A→B)
        if len(self.command_history) >= 4:
            if (self.command_history[-1] == self.command_history[-3] and
                self.command_history[-2] == self.command_history[-4]):
                return {
                    "is_loop": True,
                    "loop_type": "cycle",
                    "pattern": f"2-cycle detected: '{self.command_history[-2]}' → '{self.command_history[-1]}'",
                    "confidence": 0.9
                }

        # Check for 3-cycle (A→B→C→A→B→C)
        if len(self.command_history) >= 6:
            if (self.command_history[-1] == self.command_history[-4] and
                self.command_history[-2] == self.command_history[-5] and
                self.command_history[-3] == self.command_history[-6]):
                return {
                    "is_loop": True,
                    "loop_type": "cycle",
                    "pattern": f"3-cycle detected: {' → '.join(self.command_history[-3:])}",
                    "confidence": 0.9
                }

        return {"is_loop": False, "loop_type": None, "pattern": None, "confidence": 0.0}

    def _check_similar_variations(self) -> Dict[str, any]:
        """Check for similar commands with minor variations."""
        if len(self.command_history) < 3:
            return {"is_loop": False, "loop_type": None, "pattern": None, "confidence": 0.0}

        # Check last 3 commands for similarity
        recent = self.command_history[-3:]

        similarities = []
        for i in range(len(recent)):
            for j in range(i + 1, len(recent)):
                similarity = self._similarity(recent[i], recent[j])
                similarities.append(similarity)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        if avg_similarity >= self.similarity_threshold:
            return {
                "is_loop": True,
                "loop_type": "similar_variation",
                "pattern": f"Similar commands repeated (avg similarity: {avg_similarity:.0%})",
                "confidence": avg_similarity
            }

        return {"is_loop": False, "loop_type": None, "pattern": None, "confidence": 0.0}

    def _similarity(self, cmd1: str, cmd2: str) -> float:
        """Calculate similarity between two commands (0.0-1.0)."""
        # Normalize whitespace
        cmd1 = ' '.join(cmd1.split())
        cmd2 = ' '.join(cmd2.split())

        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, cmd1, cmd2).ratio()

    def suggest_breakout(self) -> str:
        """
        Use LLM to suggest how to break the loop.

        Returns: Suggested alternative approach
        """
        from scripts.aav2_llm_integration import call_claude_api

        # Build context
        history_str = '\n'.join(f"{i+1}. {cmd}" for i, cmd in enumerate(self.command_history))

        system_prompt = """You are an expert at debugging stuck agents.

Your task: Analyze command history and suggest a DIFFERENT approach to break the loop.

Provide:
1. Why the agent is stuck
2. ONE concrete alternative command or strategy
3. Keep it brief (2-3 sentences max)"""

        user_prompt = f"""Agent stuck in loop. Recent command history:

{history_str}

Suggest a different approach to break this cycle:"""

        response = call_claude_api(user_prompt, system_prompt, max_tokens=512)

        if response.success:
            return response.content.strip()
        else:
            return "[LLM unavailable] Try: Check error logs, verify prerequisites, or skip to next step"

    def reset(self):
        """Reset detector state."""
        self.command_history.clear()
        self.loop_detected_count = 0

    def get_stats(self) -> Dict[str, any]:
        """Get detector statistics."""
        return {
            "total_commands": len(self.command_history),
            "loops_detected": self.loop_detected_count,
            "recent_commands": self.command_history[-3:] if self.command_history else []
        }


if __name__ == "__main__":
    # Test loop detection
    print("Testing Loop Detector...")
    print("")

    detector = LoopDetector()

    # Test 1: Exact repeats
    print("Test 1: Exact Repeats")
    for i in range(4):
        result = detector.detect_loop("ls /nonexistent")
        print(f"  Command {i+1}: is_loop={result['is_loop']}, pattern={result['pattern']}")
    print("")

    # Test 2: 2-cycle
    detector.reset()
    print("Test 2: 2-Cycle Pattern")
    commands = ["mkdir /tmp/test", "rm -rf /tmp/test", "mkdir /tmp/test", "rm -rf /tmp/test"]
    for i, cmd in enumerate(commands):
        result = detector.detect_loop(cmd)
        print(f"  Command {i+1}: is_loop={result['is_loop']}, pattern={result['pattern']}")
    print("")

    # Test 3: Similar variations
    detector.reset()
    print("Test 3: Similar Variations")
    similar_commands = [
        "docker build -t test:v1 .",
        "docker build -t test:v2 .",
        "docker build -t test:v3 ."
    ]
    for i, cmd in enumerate(similar_commands):
        result = detector.detect_loop(cmd)
        print(f"  Command {i+1}: is_loop={result['is_loop']}, pattern={result['pattern']}, confidence={result['confidence']:.2f}")
    print("")

    # Test 4: Breakout suggestion
    if result["is_loop"]:
        print("Test 4: Breakout Suggestion")
        suggestion = detector.suggest_breakout()
        print(f"  Suggestion: {suggestion}")
        print("")

    print("Stats:", detector.get_stats())

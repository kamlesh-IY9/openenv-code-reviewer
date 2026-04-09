"""
Code Reviewer Environment - Main Implementation
Follows OpenEnv specification with step(), reset(), state() API.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    CodeReviewerObservation,
    CodeReviewerAction,
    CodeReviewerReward,
    CodeIssue,
    IssueType,
    Severity,
    CodeSnippet,
    TaskConfig,
    ReviewResult,
)
from tasks import TASKS


@dataclass
class EnvironmentState:
    """Internal state of the environment."""

    current_task: Optional[TaskConfig] = None
    identified_issues: List[CodeIssue] = field(default_factory=list)
    step_number: int = 0
    max_steps: int = 20
    episode_reward: float = 0.0
    hints_used: int = 0
    review_submitted: bool = False
    task_history: List[str] = field(default_factory=list)


class CodeReviewerEnv:
    """
    Code Reviewer Environment for OpenEnv.

    Agents review code snippets and identify issues.
    Tasks range from easy (syntax errors) to hard (security vulnerabilities).
    """

    def __init__(self, task_name: Optional[str] = None):
        """
        Initialize the environment.

        Args:
            task_name: Name of task to run. If None, uses default from config.
        """
        self.task_name = task_name or "syntax_check"
        self._env_state = EnvironmentState()
        self.tasks = TASKS

    def reset(self, task_name: Optional[str] = None) -> CodeReviewerObservation:
        """
        Reset the environment to initial state.

        Args:
            task_name: Optional task to switch to. Uses current task if None.

        Returns:
            Initial observation for the episode.
        """
        # Use provided task or current task
        task_key = task_name or self.task_name

        if task_key not in self.tasks:
            raise ValueError(
                f"Unknown task: {task_key}. Available: {list(self.tasks.keys())}"
            )

        # Reset state
        self._env_state = EnvironmentState()
        self._env_state.current_task = self.tasks[task_key]
        self._env_state.max_steps = self._env_state.current_task.max_steps
        self.task_name = task_key

        # Create initial observation
        observation = CodeReviewerObservation(
            code_snippet=self._env_state.current_task.code_snippet,
            task_description=self._env_state.current_task.description,
            task_difficulty=self._env_state.current_task.difficulty,
            step_number=0,
            max_steps=self._env_state.max_steps,
            previous_issues=[],
            hint_available=len(self._env_state.current_task.hints) > 0,
            hint_text=None,
            done=False,
            info={
                "task_name": task_key,
                "expected_issue_count": len(
                    self._env_state.current_task.expected_issues
                ),
                "hints_available": len(self._env_state.current_task.hints),
            },
        )

        return observation

    def step(
        self, action: CodeReviewerAction
    ) -> Tuple[CodeReviewerObservation, CodeReviewerReward, bool, Dict]:
        """
        Execute one step in the environment.

        Args:
            action: The action to take.

        Returns:
            Tuple of (observation, reward, done, info)
        """
        if self._env_state.current_task is None:
            raise RuntimeError("Environment not reset. Call reset() first.")

        if self._env_state.review_submitted:
            # Episode already ended
            return (
                self._create_final_observation(),
                self._create_final_reward(),
                True,
                {"message": "Episode already complete"},
            )

        self._env_state.step_number += 1

        # Process action
        step_reward = 0.0
        issue_detection_reward = 0.0
        false_positive_penalty = 0.0
        done = False
        info = {}

        if action.action_type == "identify_issue":
            if action.issue:
                issue_detection_reward, false_positive_penalty = (
                    self._process_issue_identification(action.issue)
                )
                step_reward += issue_detection_reward + false_positive_penalty

        elif action.action_type == "request_hint":
            step_reward = self._process_hint_request()

        elif action.action_type == "submit_review":
            step_reward, done = self._process_review_submission()

        else:
            info["error"] = f"Unknown action type: {action.action_type}"
            step_reward = -0.1  # Small penalty for invalid action

        # Update episode reward
        self._env_state.episode_reward += step_reward

        # Check if max steps reached
        if self._env_state.step_number >= self._env_state.max_steps and not done:
            done = True
            info["message"] = "Maximum steps reached"

        # Create reward object
        reward = self._calculate_reward(
            step_reward=step_reward,
            issue_detection_reward=issue_detection_reward,
            false_positive_penalty=false_positive_penalty,
        )

        # Create observation
        observation = self._create_observation(done)

        return observation, reward, done, info

    def state(self) -> Dict[str, Any]:
        """
        Get current environment state.

        Returns:
            Dictionary containing current state information.
        """
        if self._env_state.current_task is None:
            return {"status": "not_initialized"}

        return {
            "task_name": self.task_name,
            "task_difficulty": self._env_state.current_task.difficulty,
            "step_number": self._env_state.step_number,
            "max_steps": self._env_state.max_steps,
            "episode_reward": self._env_state.episode_reward,
            "issues_identified": len(self._env_state.identified_issues),
            "expected_issues": len(self._env_state.current_task.expected_issues),
            "hints_used": self._env_state.hints_used,
            "review_submitted": self._env_state.review_submitted,
        }

    def _process_issue_identification(self, issue: CodeIssue) -> Tuple[float, float]:
        """
        Process an issue identification action.

        Returns:
            Tuple of (detection_reward, false_positive_penalty)
        """
        expected_issues = self._env_state.current_task.expected_issues

        # Check if this issue matches any expected issue
        matched = False
        for expected in expected_issues:
            if self._issues_match(issue, expected):
                # Check if already identified
                already_found = any(
                    self._issues_match(prev, expected)
                    for prev in self._env_state.identified_issues
                )
                if not already_found:
                    self._env_state.identified_issues.append(issue)
                    matched = True
                    break

        if matched:
            # Reward based on severity
            severity_reward = {
                Severity.CRITICAL: 0.5,
                Severity.HIGH: 0.4,
                Severity.MEDIUM: 0.3,
                Severity.LOW: 0.2,
                Severity.INFO: 0.1,
            }.get(issue.severity, 0.2)
            return severity_reward, 0.0
        else:
            # False positive penalty
            self._env_state.identified_issues.append(issue)  # Track for analysis
            return 0.0, -0.15

    def _process_hint_request(self) -> float:
        """Process a hint request action."""
        if self._env_state.hints_used < len(self._env_state.current_task.hints):
            self._env_state.hints_used += 1
            return -0.05  # Small penalty for using hints
        return -0.1  # Penalty for requesting hint when none available

    def _process_review_submission(self) -> Tuple[float, bool]:
        """
        Process a review submission action.

        Returns:
            Tuple of (reward, done)
        """
        self._env_state.review_submitted = True

        # Calculate completeness reward
        expected_count = len(self._env_state.current_task.expected_issues)
        found_count = self._count_unique_matches()

        completeness = min(found_count / expected_count, 1.0) if expected_count > 0 else 1.0
        completeness_reward = completeness * 0.5

        # Efficiency reward (bonus for completing early)
        efficiency_reward = 0.0
        if self._env_state.step_number < self._env_state.max_steps:
            efficiency_reward = (
                self._env_state.max_steps - self._env_state.step_number
            ) * 0.02

        total_reward = completeness_reward + efficiency_reward
        return total_reward, True

    def _issues_match(
        self, issue1: CodeIssue, issue2: CodeIssue, line_tolerance: int = 2
    ) -> bool:
        """
        Check if two issues match (within tolerance).

        Args:
            issue1: First issue to compare
            issue2: Second issue to compare
            line_tolerance: How many lines apart can issues be to still match

        Returns:
            True if issues match
        """
        # Check line number within tolerance
        line_match = abs(issue1.line_number - issue2.line_number) <= line_tolerance

        # Check issue type
        type_match = issue1.issue_type == issue2.issue_type

        # Check severity
        severity_match = issue1.severity == issue2.severity

        return line_match and type_match and severity_match

    def _count_unique_matches(self) -> int:
        """Count how many expected issues have been correctly identified."""
        if self._env_state.current_task is None:
            return 0

        expected_issues = self._env_state.current_task.expected_issues
        identified_issues = self._env_state.identified_issues

        return sum(
            1
            for expected in expected_issues
            if any(self._issues_match(identified, expected) for identified in identified_issues)
        )

    def _calculate_reward(
        self,
        step_reward: float,
        issue_detection_reward: float,
        false_positive_penalty: float,
    ) -> CodeReviewerReward:
        """Calculate the full reward structure."""

        # Calculate task completion score
        if self._env_state.current_task:
            expected = len(self._env_state.current_task.expected_issues)
            correctly_identified = self._count_unique_matches()
            completion_score = (
                min(correctly_identified / expected, 1.0) if expected > 0 else 1.0
            )
        else:
            completion_score = 0.0

        return CodeReviewerReward(
            total_reward=self._env_state.episode_reward,
            step_reward=step_reward,
            issue_detection_reward=issue_detection_reward,
            false_positive_penalty=false_positive_penalty,
            completeness_reward=completion_score * 0.5
            if self._env_state.review_submitted
            else 0.0,
            efficiency_reward=max(
                0, (self._env_state.max_steps - self._env_state.step_number) * 0.02
            )
            if self._env_state.review_submitted
            else 0.0,
            task_completion_score=completion_score,
        )

    def _create_observation(self, done: bool) -> CodeReviewerObservation:
        """Create current observation."""
        hint_text = None
        if self._env_state.hints_used > 0 and self._env_state.hints_used <= len(
            self._env_state.current_task.hints
        ):
            hint_text = self._env_state.current_task.hints[
                self._env_state.hints_used - 1
            ]

        return CodeReviewerObservation(
            code_snippet=self._env_state.current_task.code_snippet,
            task_description=self._env_state.current_task.description,
            task_difficulty=self._env_state.current_task.difficulty,
            step_number=self._env_state.step_number,
            max_steps=self._env_state.max_steps,
            previous_issues=self._env_state.identified_issues,
            hint_available=self._env_state.hints_used
            < len(self._env_state.current_task.hints),
            hint_text=hint_text,
            done=done,
            info={
                "issues_found": len(self._env_state.identified_issues),
                "hints_used": self._env_state.hints_used,
            },
        )

    def _create_final_observation(self) -> CodeReviewerObservation:
        """Create final observation after episode ends."""
        return self._create_observation(done=True)

    def _create_final_reward(self) -> CodeReviewerReward:
        """Create final reward after episode ends."""
        return self._calculate_reward(0.0, 0.0, 0.0)

    def close(self) -> None:
        """Release environment resources."""
        return None

    def get_review_result(self) -> ReviewResult:
        """
        Get detailed review results after episode completion.

        Returns:
            ReviewResult with detailed analysis.
        """
        if (
            not self._env_state.review_submitted
            and self._env_state.step_number < self._env_state.max_steps
        ):
            raise RuntimeError("Episode not yet complete")

        expected_issues = self._env_state.current_task.expected_issues
        identified_issues = self._env_state.identified_issues

        # Find matched, missed, and false positive issues
        matched = []
        missed = []
        false_positives = []

        for identified in identified_issues:
            is_match = False
            for expected in expected_issues:
                if self._issues_match(identified, expected):
                    matched.append(identified)
                    is_match = True
                    break
            if not is_match:
                false_positives.append(identified)

        for expected in expected_issues:
            was_found = any(
                self._issues_match(identified, expected)
                for identified in identified_issues
            )
            if not was_found:
                missed.append(expected)

        # Calculate completion score
        expected_count = len(expected_issues)
        completion_score = (
            min(self._count_unique_matches() / expected_count, 1.0)
            if expected_count > 0
            else 1.0
        )

        return ReviewResult(
            task_name=self.task_name,
            identified_issues=matched,
            missed_issues=missed,
            false_positives=false_positives,
            total_reward=self._env_state.episode_reward,
            completion_score=completion_score,
            steps_taken=self._env_state.step_number,
            success=completion_score >= 0.7,  # Success threshold: 70%
        )


# Async wrapper for compatibility
class AsyncCodeReviewerEnv(CodeReviewerEnv):
    """Async wrapper for CodeReviewerEnv."""

    async def reset(self, task_name: Optional[str] = None) -> CodeReviewerObservation:
        return super().reset(task_name)

    async def step(
        self, action: CodeReviewerAction
    ) -> Tuple[CodeReviewerObservation, CodeReviewerReward, bool, Dict]:
        return super().step(action)

    async def state(self) -> Dict[str, Any]:
        return super().state()

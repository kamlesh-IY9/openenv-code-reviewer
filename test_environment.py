"""
Test script for Code Reviewer Environment.
Validates all components work correctly before submission.
"""

import sys
import traceback
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from models import (
    CodeReviewerObservation,
    CodeReviewerAction,
    CodeReviewerReward,
    CodeIssue,
    IssueType,
    Severity,
    CodeSnippet,
)
from server.environment import CodeReviewerEnv
from tasks import TASKS, get_task_names


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(text: str):
    """Print a success message."""
    print(f"  [OK] {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"  [FAIL] {text}")


def print_info(text: str):
    """Print an info message."""
    print(f"  [INFO] {text}")


def test_models() -> bool:
    """Test that all models can be instantiated."""
    print_header("Testing Pydantic Models")

    try:
        # Test CodeSnippet
        snippet = CodeSnippet(
            language="python",
            code="print('hello')",
            filename="test.py",
            context="Test snippet",
        )
        print_success("CodeSnippet model works")

        # Test CodeIssue
        issue = CodeIssue(
            line_number=1,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.HIGH,
            description="Test issue",
            suggested_fix="Fix it",
        )
        print_success("CodeIssue model works")

        # Test CodeReviewerAction
        action = CodeReviewerAction(
            action_type="identify_issue",
            issue=issue,
            confidence=0.8,
            reasoning="Test reasoning",
        )
        print_success("CodeReviewerAction model works")

        # Test CodeReviewerObservation
        observation = CodeReviewerObservation(
            code_snippet=snippet,
            task_description="Test task",
            task_difficulty="easy",
            step_number=0,
            max_steps=10,
            previous_issues=[],
            hint_available=False,
            done=False,
        )
        print_success("CodeReviewerObservation model works")

        # Test CodeReviewerReward
        reward = CodeReviewerReward(
            total_reward=1.0,
            step_reward=0.5,
            issue_detection_reward=0.3,
            false_positive_penalty=0.0,
            task_completion_score=0.8,
        )
        print_success("CodeReviewerReward model works")

        return True

    except Exception as e:
        print_error(f"Model test failed: {e}")
        traceback.print_exc()
        return False


def test_environment_reset() -> bool:
    """Test environment reset for all tasks."""
    print_header("Testing Environment Reset")

    all_passed = True

    for task_name in get_task_names():
        try:
            env = CodeReviewerEnv(task_name=task_name)
            observation = env.reset()

            assert observation.code_snippet.code, "Code snippet should not be empty"
            assert observation.task_description, "Task description should not be empty"
            assert observation.task_difficulty in ["easy", "medium", "hard"], (
                "Invalid difficulty"
            )
            assert observation.step_number == 0, "Step should start at 0"
            assert not observation.done, "Episode should not be done"

            print_success(f"Reset for '{task_name}' works")

        except Exception as e:
            print_error(f"Reset for '{task_name}' failed: {e}")
            traceback.print_exc()
            all_passed = False

    return all_passed


def test_environment_step() -> bool:
    """Test environment step functionality."""
    print_header("Testing Environment Step")

    try:
        env = CodeReviewerEnv(task_name="syntax_check")
        observation = env.reset()

        # Test identify_issue action
        action = CodeReviewerAction(
            action_type="identify_issue",
            issue=CodeIssue(
                line_number=1,
                issue_type=IssueType.SYNTAX_ERROR,
                severity=Severity.HIGH,
                description="Missing colon",
                suggested_fix="Add colon",
            ),
            confidence=0.9,
        )

        observation, reward, done, info = env.step(action)

        assert isinstance(observation, CodeReviewerObservation), (
            "Should return observation"
        )
        assert isinstance(reward, CodeReviewerReward), "Should return reward"
        assert isinstance(done, bool), "Done should be boolean"
        assert observation.step_number == 1, "Step should increment"

        print_success("Step with identify_issue works")

        # Test request_hint action
        action = CodeReviewerAction(action_type="request_hint")
        observation, reward, done, info = env.step(action)

        assert observation.hint_text is not None, "Hint should be provided"
        print_success("Step with request_hint works")

        # Test submit_review action
        action = CodeReviewerAction(action_type="submit_review")
        observation, reward, done, info = env.step(action)

        assert done, "Episode should end after submit_review"
        print_success("Step with submit_review works")

        return True

    except Exception as e:
        print_error(f"Step test failed: {e}")
        traceback.print_exc()
        return False


def test_graders() -> bool:
    """Test that graders work correctly."""
    print_header("Testing Graders")

    all_passed = True

    for task_name in get_task_names():
        try:
            env = CodeReviewerEnv(task_name=task_name)
            env.reset()

            task = TASKS[task_name]
            expected_issues = task.expected_issues

            print_info(f"Task '{task_name}': {len(expected_issues)} expected issues")

            # Identify all expected issues
            for issue in expected_issues:
                action = CodeReviewerAction(
                    action_type="identify_issue",
                    issue=issue,
                    confidence=1.0,
                )
                env.step(action)

            # Submit review
            action = CodeReviewerAction(action_type="submit_review")
            observation, reward, done, info = env.step(action)

            # Get review result
            result = env.get_review_result()

            assert result.completion_score > 0, "Should have positive completion score"
            assert len(result.identified_issues) > 0, "Should have identified issues"

            print_success(
                f"'{task_name}' grader: score={result.completion_score:.2f}, "
                f"found={len(result.identified_issues)}, missed={len(result.missed_issues)}"
            )

        except Exception as e:
            print_error(f"Grader test for '{task_name}' failed: {e}")
            traceback.print_exc()
            all_passed = False

    return all_passed


def test_reward_range() -> bool:
    """Test that rewards are in valid range [0, 1]."""
    print_header("Testing Reward Range")

    try:
        env = CodeReviewerEnv(task_name="syntax_check")
        env.reset()

        rewards = []

        # Run a few steps
        for _ in range(5):
            action = CodeReviewerAction(
                action_type="identify_issue",
                issue=CodeIssue(
                    line_number=1,
                    issue_type=IssueType.SYNTAX_ERROR,
                    severity=Severity.HIGH,
                    description="Test",
                ),
            )
            observation, reward, done, info = env.step(action)
            rewards.append(reward.step_reward)

            assert -1.0 <= reward.step_reward <= 1.0, (
                f"Step reward {reward.step_reward} out of range"
            )
            assert 0.0 <= reward.task_completion_score <= 1.0, (
                "Completion score out of range"
            )

        print_success(f"All rewards in valid range: {rewards}")
        return True

    except Exception as e:
        print_error(f"Reward range test failed: {e}")
        traceback.print_exc()
        return False


def test_state_method() -> bool:
    """Test the state() method."""
    print_header("Testing State Method")

    try:
        env = CodeReviewerEnv(task_name="syntax_check")
        env.reset()

        state = env.state()

        assert "task_name" in state, "State should have task_name"
        assert "step_number" in state, "State should have step_number"
        assert "episode_reward" in state, "State should have episode_reward"

        print_success(f"State method works: {state}")
        return True

    except Exception as e:
        print_error(f"State method test failed: {e}")
        traceback.print_exc()
        return False


def test_task_difficulty_progression() -> bool:
    """Test that tasks have proper difficulty progression."""
    print_header("Testing Task Difficulty Progression")

    try:
        difficulties = []
        for task_name in get_task_names():
            task = TASKS[task_name]
            difficulties.append((task_name, task.difficulty))

        print_info(f"Task difficulties: {difficulties}")

        # Check that we have all three difficulties
        difficulty_values = [d[1] for d in difficulties]
        assert "easy" in difficulty_values, "Should have easy task"
        assert "medium" in difficulty_values, "Should have medium task"
        assert "hard" in difficulty_values, "Should have hard task"

        print_success("All difficulty levels present")
        return True

    except Exception as e:
        print_error(f"Difficulty progression test failed: {e}")
        traceback.print_exc()
        return False


def test_inference_script_structure() -> bool:
    """Test that inference.py has required structure."""
    print_header("Testing Inference Script Structure")

    try:
        with open("inference.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Check for required components
        required_elements = [
            "[START]",
            "[STEP]",
            "[END]",
            "log_start",
            "log_step",
            "log_end",
            "API_BASE_URL",
            "MODEL_NAME",
            "HF_TOKEN",
            "OpenAI",
        ]

        missing = []
        for element in required_elements:
            if element not in content:
                missing.append(element)

        if missing:
            print_error(f"Missing elements: {missing}")
            return False

        print_success("All required elements present in inference.py")
        return True

    except Exception as e:
        print_error(f"Inference script test failed: {e}")
        traceback.print_exc()
        return False


def run_all_tests() -> Tuple[bool, List[str]]:
    """Run all tests and return results."""
    print("\n" + "=" * 60)
    print("  CODE REVIEWER ENVIRONMENT - VALIDATION SUITE")
    print("=" * 60)

    tests = [
        ("Pydantic Models", test_models),
        ("Environment Reset", test_environment_reset),
        ("Environment Step", test_environment_step),
        ("Graders", test_graders),
        ("Reward Range", test_reward_range),
        ("State Method", test_state_method),
        ("Task Difficulty", test_task_difficulty_progression),
        ("Inference Script", test_inference_script_structure),
    ]

    results = []
    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            traceback.print_exc()
            results.append((name, False))
            failed += 1

    # Print summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n  [OK] ALL TESTS PASSED!")
        return True, []
    else:
        print("\n  [FAIL] SOME TESTS FAILED")
        failed_tests = [name for name, success in results if not success]
        return False, failed_tests


if __name__ == "__main__":
    success, failed_tests = run_all_tests()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Pre-submission validation script for Code Reviewer Environment.
Run this before submitting to ensure all requirements are met.
"""

import os
import sys
import subprocess
import json
import shutil


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(text):
    print(f"  [OK] {text}")


def print_error(text):
    print(f"  [FAIL] {text}")


def print_warning(text):
    print(f"  [WARN] {text}")


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"Missing {description}: {filepath}")
        return False


def check_required_files():
    """Check all required files exist."""
    print_header("Checking Required Files")
    
    required_files = [
        ("openenv.yaml", "OpenEnv specification"),
        ("Dockerfile", "Docker configuration"),
        ("requirements.txt", "Python dependencies"),
        ("README.md", "Documentation"),
        ("inference.py", "Baseline inference script"),
        ("models.py", "Pydantic models"),
        ("environment.py", "Environment implementation"),
        ("tasks.py", "Task definitions"),
        ("server.py", "WebSocket server"),
    ]
    
    all_exist = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist


def check_openenv_yaml():
    """Validate openenv.yaml structure."""
    print_header("Validating openenv.yaml")
    
    try:
        import yaml
        with open("openenv.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        required_keys = ["name", "version", "description", "interface", "endpoints", "models", "config"]
        for key in required_keys:
            if key in config:
                print_success(f"Has '{key}'")
            else:
                print_error(f"Missing '{key}'")
                return False
        
        # Check tasks
        tasks = config.get("config", {}).get("available_tasks", [])
        if len(tasks) >= 3:
            print_success(f"Has {len(tasks)} tasks: {tasks}")
        else:
            print_error(f"Need at least 3 tasks, found {len(tasks)}")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Error parsing openenv.yaml: {e}")
        return False


def check_dockerfile():
    """Validate Dockerfile."""
    print_header("Validating Dockerfile")
    
    try:
        with open("Dockerfile", "r", encoding="utf-8") as f:
            content = f.read()
        
        required_elements = [
            ("FROM", "Base image"),
            ("WORKDIR", "Working directory"),
            ("requirements.txt", "Requirements installation"),
            ("EXPOSE", "Port exposure"),
            ("CMD", "Run command"),
        ]
        
        for element, description in required_elements:
            if element in content:
                print_success(f"Has {description}")
            else:
                print_error(f"Missing {description}")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Error checking Dockerfile: {e}")
        return False


def check_inference_script():
    """Validate inference.py structure."""
    print_header("Validating inference.py")
    
    try:
        with open("inference.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check logging format
        required_patterns = [
            ("[START]", "START log format"),
            ("[STEP]", "STEP log format"),
            ("[END]", "END log format"),
            ("log_start", "log_start function"),
            ("log_step", "log_step function"),
            ("log_end", "log_end function"),
            ("API_BASE_URL", "API_BASE_URL variable"),
            ("MODEL_NAME", "MODEL_NAME variable"),
            ("HF_TOKEN", "HF_TOKEN variable"),
            ("from openai import OpenAI", "OpenAI import"),
        ]
        
        for pattern, description in required_patterns:
            if pattern in content:
                print_success(f"Has {description}")
            else:
                print_error(f"Missing {description}")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Error checking inference.py: {e}")
        return False


def check_models():
    """Validate Pydantic models."""
    print_header("Validating Pydantic Models")
    
    try:
        sys.path.insert(0, os.getcwd())
        from models import (
            CodeReviewerObservation,
            CodeReviewerAction,
            CodeReviewerReward,
            CodeIssue,
        )
        
        print_success("All models import successfully")
        
        # Test model instantiation
        from models import CodeSnippet, IssueType, Severity
        
        snippet = CodeSnippet(language="python", code="print('test')")
        print_success("CodeSnippet instantiates")
        
        issue = CodeIssue(
            line_number=1,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.HIGH,
            description="Test",
        )
        print_success("CodeIssue instantiates")
        
        action = CodeReviewerAction(action_type="test", issue=issue)
        print_success("CodeReviewerAction instantiates")
        
        return True
        
    except Exception as e:
        print_error(f"Model validation failed: {e}")
        return False


def check_environment():
    """Validate environment implementation."""
    print_header("Validating Environment")
    
    try:
        sys.path.insert(0, os.getcwd())
        from environment import CodeReviewerEnv
        from models import CodeReviewerAction
        
        # Test reset
        env = CodeReviewerEnv("syntax_check")
        obs = env.reset()
        print_success("Environment reset works")
        
        # Test step
        action = CodeReviewerAction(action_type="submit_review")
        obs, reward, done, info = env.step(action)
        print_success("Environment step works")
        
        # Test state
        state = env.state()
        print_success("Environment state() works")
        
        return True
        
    except Exception as e:
        print_error(f"Environment validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_tasks():
    """Validate task definitions."""
    print_header("Validating Tasks")
    
    try:
        sys.path.insert(0, os.getcwd())
        from tasks import TASKS
        
        task_count = len(TASKS)
        if task_count >= 3:
            print_success(f"Has {task_count} tasks")
        else:
            print_error(f"Need at least 3 tasks, found {task_count}")
            return False
        
        # Check difficulties
        difficulties = [task.difficulty for task in TASKS.values()]
        
        if "easy" in difficulties:
            print_success("Has easy task")
        else:
            print_error("Missing easy task")
            return False
        
        if "medium" in difficulties:
            print_success("Has medium task")
        else:
            print_error("Missing medium task")
            return False
        
        if "hard" in difficulties:
            print_success("Has hard task")
        else:
            print_error("Missing hard task")
            return False
        
        # Check graders
        for task_name, task in TASKS.items():
            if len(task.expected_issues) > 0:
                print_success(f"'{task_name}' has {len(task.expected_issues)} expected issues")
            else:
                print_error(f"'{task_name}' has no expected issues")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Task validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_readme():
    """Validate README.md."""
    print_header("Validating README.md")
    
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        required_sections = [
            ("## Overview", "Overview section"),
            ("## Quick Start", "Quick Start section"),
            ("## Tasks", "Tasks section"),
            ("## Observation Space", "Observation space documentation"),
            ("## Action Space", "Action space documentation"),
            ("## Environment API", "API documentation"),
            ("## Deployment", "Deployment instructions"),
            ("## Baseline Scores", "Baseline scores section"),
        ]
        
        for pattern, description in required_sections:
            if pattern in content:
                print_success(f"Has {description}")
            else:
                print_warning(f"Missing {description}")
        
        return True
        
    except Exception as e:
        print_error(f"README validation failed: {e}")
        return False


def test_docker_build():
    """Test Docker build (optional, may be slow)."""
    print_header("Testing Docker Build (Optional)")
    
    if shutil.which("docker") is None:
        print_warning("Docker not found, skipping build test")
        return True

    try:
        daemon_check = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if daemon_check.returncode != 0:
            print_warning("Docker daemon not available, skipping build test")
            return True
    except Exception as e:
        print_warning(f"Could not query Docker daemon, skipping build test: {e}")
        return True
    
    print("Attempting Docker build (this may take a few minutes)...")
    
    try:
        result = subprocess.run(
            ["docker", "build", "-t", "code-reviewer-test", "."],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print_success("Docker build succeeded")
            return True
        else:
            print_error("Docker build failed")
            print(result.stderr[-500:])  # Last 500 chars
            return False
            
    except subprocess.TimeoutExpired:
        print_warning("Docker build timed out (may still work on HF Spaces)")
        return True
    except Exception as e:
        print_warning(f"Could not test Docker build: {e}")
        return True


def main():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("  CODE REVIEWER ENVIRONMENT - PRE-SUBMISSION VALIDATION")
    print("=" * 60)
    
    checks = [
        ("Required Files", check_required_files),
        ("openenv.yaml", check_openenv_yaml),
        ("Dockerfile", check_dockerfile),
        ("inference.py", check_inference_script),
        ("Pydantic Models", check_models),
        ("Environment", check_environment),
        ("Tasks", check_tasks),
        ("README.md", check_readme),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            print_error(f"Check '{name}' crashed: {e}")
            results.append((name, False))
    
    # Optional Docker test
    docker_passed = test_docker_build()
    results.append(("Docker Build", docker_passed))
    
    # Summary
    print_header("VALIDATION SUMMARY")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")
    
    print(f"\n  Result: {passed_count}/{total_count} checks passed")
    
    if passed_count == total_count:
        print("\n  [OK] ALL CHECKS PASSED! Ready to submit!")
        print("\n  Next steps:")
        print("  1. Push to GitHub")
        print("  2. Deploy to Hugging Face Spaces")
        print("  3. Run inference.py to verify baseline scores")
        print("  4. Submit your entry!")
        return 0
    else:
        print("\n  [WARN] SOME CHECKS FAILED")
        print("  Please fix the issues above before submitting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

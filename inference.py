"""
Baseline inference script for Code Reviewer Environment.

This script runs an LLM agent against the Code Reviewer environment
and produces structured logs in the required format:
  [START] task=... env=... model=...
  [STEP] step=... action=... reward=... done=... error=...
  [END] success=... steps=... score=... rewards=...

Environment Variables:
  API_BASE_URL:      LLM endpoint (default: https://router.huggingface.co/v1)
  MODEL_NAME:        Model identifier (default: Qwen/Qwen2.5-72B-Instruct)
  HF_TOKEN:          Hugging Face API token (required)
  CODE_REVIEWER_TASK: Task to run (default: syntax_check)
  ENV_BASE_URL:      Code-reviewer server URL (default: http://localhost:7860)
"""

import os
import json
import textwrap
import time
from typing import List, Optional, Dict, Any

import httpx
from openai import OpenAI

# LLM configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Task / environment configuration
TASK_NAME = os.getenv("CODE_REVIEWER_TASK", "syntax_check")
BENCHMARK = os.getenv("CODE_REVIEWER_BENCHMARK", "code-reviewer-env")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860").rstrip("/")
SESSION_ID = "inference-session"

# Inference hyperparameters
MAX_STEPS = 20
TEMPERATURE = 0.3
MAX_TOKENS = 500
SUCCESS_SCORE_THRESHOLD = 0.7  # 70% completion = success


# System prompt for the code reviewer agent
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a code review assistant AI. Your task is to review code snippets and identify issues.
    
    For each issue you find, report:
    - Line number where the issue occurs
    - Issue type: syntax_error, logic_bug, security_vulnerability, performance_issue, style_violation, or no_issue
    - Severity: critical, high, medium, low, or info
    - Description of the issue
    - Suggested fix (optional)
    
    Available actions:
    1. identify_issue - Report an issue you found
    2. submit_review - Submit your final review when done
    3. request_hint - Get a hint (costs small penalty)
    
    Be thorough and accurate. False positives will be penalized.
    Your goal is to find ALL real issues while minimizing false reports.
    
    Respond in this JSON format:
    {
        "action_type": "identify_issue|submit_review|request_hint",
        "issue": {
            "line_number": <int>,
            "issue_type": "<type>",
            "severity": "<severity>",
            "description": "<description>",
            "suggested_fix": "<fix>"
        },
        "confidence": <0.0-1.0>,
        "reasoning": "<your reasoning>"
    }
    
    For submit_review and request_hint, you can omit the "issue" field.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    """Log the start of an episode."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    """Log a step in the episode."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Log the end of an episode."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(
    step: int,
    code_snippet: Dict[str, Any],
    task_description: str,
    previous_issues: List[Dict],
    hint_text: Optional[str],
) -> str:
    """Build the user prompt for the LLM."""
    
    # Format previous issues
    issues_text = "None"
    if previous_issues:
        issues_lines = []
        for i, issue in enumerate(previous_issues[-5:], 1):  # Last 5 issues
            issues_lines.append(
                f"{i}. Line {issue.get('line_number', '?' )}: {issue.get('issue_type', 'unknown')} "
                f"({issue.get('severity', 'unknown')}) - {issue.get('description', 'N/A')[:50]}..."
            )
        issues_text = "\n".join(issues_lines)
    
    # Format hint
    hint_section = ""
    if hint_text:
        hint_section = f"\n\nHINT: {hint_text}"
    
    return textwrap.dedent(
        f"""
        Step: {step}/{MAX_STEPS}
        
        TASK: {task_description}
        
        CODE TO REVIEW ({code_snippet.get('language', 'unknown')}):
        ```{code_snippet.get('language', '')}
        {code_snippet.get('code', 'No code provided')}
        ```
        
        Context: {code_snippet.get('context', 'N/A')}
        
        Issues identified so far:
        {issues_text}
        {hint_section}
        
        What action would you like to take? Respond with the JSON format specified in your instructions.
        """
    ).strip()


def parse_model_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse the model's response into an action."""
    try:
        # Try to extract JSON from response
        import json
        
        # Clean up response - find JSON block
        text = response_text.strip()
        
        # If wrapped in code blocks, extract
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        action = json.loads(text)
        return action
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Response was: {response_text[:200]}...")
        return None


def get_model_action(
    client: OpenAI,
    step: int,
    code_snippet: Dict[str, Any],
    task_description: str,
    previous_issues: List[Dict],
    hint_text: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Get the next action from the LLM."""
    
    user_prompt = build_user_prompt(
        step=step,
        code_snippet=code_snippet,
        task_description=task_description,
        previous_issues=previous_issues,
        hint_text=hint_text,
    )
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        
        response_text = completion.choices[0].message.content
        return parse_model_response(response_text)
        
    except Exception as e:
        print(f"Error calling model: {e}")
        return None


# ---------------------------------------------------------------------------
# HTTP helpers — call the running environment server
# ---------------------------------------------------------------------------

def _wait_for_server(timeout: int = 30) -> None:
    """Block until the environment server returns 200 on /health."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{ENV_BASE_URL}/health", timeout=3)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"Environment server at {ENV_BASE_URL} did not become ready in {timeout}s")


def _reset(task_name: str) -> Dict[str, Any]:
    """Call POST /reset and return the parsed response."""
    payload = {"task": task_name, "session_id": SESSION_ID}
    r = httpx.post(f"{ENV_BASE_URL}/reset", json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(f"Reset failed: {data}")
    return data


def _step(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """Call POST /step and return the parsed response."""
    payload = {"session_id": SESSION_ID, "action": action_data}
    r = httpx.post(f"{ENV_BASE_URL}/step", json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(f"Step failed: {data}")
    return data


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episode(client: OpenAI, task_name: str) -> tuple:
    """
    Run a single episode by talking to the HTTP environment server.

    Returns:
        Tuple of (success, steps, score, rewards_list)
    """
    rewards_list: List[float] = []
    done = False
    step = 0
    success = False
    final_score = 0.001

    try:
        # Wait for server to be ready (matters when Docker starts cold)
        _wait_for_server(timeout=30)

        # Reset episode
        reset_resp = _reset(task_name)
        obs = reset_resp["observation"]

        while not done and step < MAX_STEPS:
            step += 1

            code_snippet = obs.get("code_snippet") or {}
            task_description = obs.get("task_description", "")
            previous_issues = obs.get("previous_issues") or []
            hint_text = obs.get("hint_text")

            # Get action from LLM
            action_data = get_model_action(
                client=client,
                step=step,
                code_snippet=code_snippet,
                task_description=task_description,
                previous_issues=previous_issues,
                hint_text=hint_text,
            )

            if action_data is None:
                error = "Failed to parse model response"
                log_step(step, "parse_error", 0.001, True, error)
                rewards_list.append(0.001)
                done = True
                break

            # Build the action payload expected by /step
            action_type = action_data.get("action_type", "submit_review")
            issue_data = action_data.get("issue") or {}

            env_action: Dict[str, Any] = {
                "action_type": action_type,
                "confidence": action_data.get("confidence", 0.9),
            }
            if issue_data and action_type == "identify_issue":
                env_action["issue"] = {
                    "line_number": issue_data.get("line_number", 0),
                    "issue_type": issue_data.get("issue_type", "no_issue"),
                    "severity": issue_data.get("severity", "info"),
                    "description": issue_data.get("description", ""),
                    "suggested_fix": issue_data.get("suggested_fix"),
                }

            try:
                step_resp = _step(env_action)
                obs = step_resp["observation"]
                reward_obj = step_resp.get("reward") or {}
                step_reward = max(0.001, min(float(reward_obj.get("step_reward", 0.0)), 0.999))
                done = bool(step_resp.get("done", False))
                info = step_resp.get("info") or {}

                # Build action label for log
                action_str = action_type
                if issue_data and action_type == "identify_issue":
                    action_str += (
                        f"(line={issue_data.get('line_number', '?')},"
                        f"type={issue_data.get('issue_type', 'unknown')})"
                    )

                log_step(step, action_str, step_reward, done, info.get("error"))
                rewards_list.append(step_reward)

                # Collect final score when done
                if done:
                    final_score = max(0.001, min(float(
                        reward_obj.get("task_completion_score", 0.0)
                    ), 0.999))
                    success = final_score >= SUCCESS_SCORE_THRESHOLD

            except Exception as e:
                error = str(e)
                log_step(step, "action_error", 0.001, True, error)
                rewards_list.append(0.001)
                done = True

    except Exception as e:
        print(f"Error running episode: {e}", flush=True)
        success = False

    return success, step, final_score, rewards_list


def main():
    """Main entry point."""
    log_start(TASK_NAME, BENCHMARK, MODEL_NAME)

    success = False
    steps = 0
    score = 0.001
    rewards: List[float] = []

    try:
        if HF_TOKEN is None:
            raise ValueError("HF_TOKEN environment variable is required")

        client = OpenAI(
            base_url=API_BASE_URL,
            api_key=HF_TOKEN,
        )

        success, steps, score, rewards = run_episode(client, TASK_NAME)
    except Exception as e:
        print(f"Fatal inference error: {e}", flush=True)
        success = False
        score = 0.001
    finally:
        log_end(success, steps, score, rewards)

    # Always exit cleanly so validators can score the emitted logs.
    return 0


if __name__ == "__main__":
    exit(main())

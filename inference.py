"""
Baseline Inference Script for Code Reviewer Environment.

This script runs an LLM agent against the Code Reviewer environment
and produces structured logs in the required format:
  [START] task=... env=... model=...
  [STEP] step=... action=... reward=... done=... error=...
  [END] success=... steps=... score=... rewards=...

Environment Variables:
  API_BASE_URL: The API endpoint for the LLM (default: https://router.huggingface.co/v1)
  MODEL_NAME: The model identifier (default: Qwen/Qwen2.5-72B-Instruct)
  HF_TOKEN: Your Hugging Face / API key
  CODE_REVIEWER_TASK: Task to run (default: syntax_check)
"""

import asyncio
import os
import textwrap
from typing import List, Optional, Dict, Any

from openai import OpenAI

# Environment configuration
IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
TASK_NAME = os.getenv("CODE_REVIEWER_TASK", "syntax_check")
BENCHMARK = os.getenv("CODE_REVIEWER_BENCHMARK", "code-reviewer-env")

# Hyperparameters
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
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


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


def run_episode(client: OpenAI, task_name: str) -> tuple:
    """
    Run a single episode on the specified task.
    
    Returns:
        Tuple of (success, steps, score, rewards_list)
    """
    from environment import CodeReviewerEnv
    from models import CodeReviewerAction, CodeIssue, IssueType, Severity
    
    # Initialize environment
    env = CodeReviewerEnv(task_name=task_name)
    observation = env.reset(task_name)
    
    log_start(task_name, BENCHMARK, MODEL_NAME)
    
    rewards_list = []
    done = False
    step = 0
    error = None
    
    while not done and step < MAX_STEPS:
        step += 1
        
        # Get action from model
        action_data = get_model_action(
            client=client,
            step=step,
            code_snippet=observation.code_snippet.model_dump(),
            task_description=observation.task_description,
            previous_issues=[issue.model_dump() for issue in observation.previous_issues],
            hint_text=observation.hint_text,
        )
        
        if action_data is None:
            error = "Failed to parse model response"
            log_step(step, "parse_error", 0.0, True, error)
            rewards_list.append(0.0)
            break
        
        # Convert to CodeReviewerAction
        try:
            issue_data = action_data.get("issue")
            issue = None
            if issue_data:
                issue = CodeIssue(
                    line_number=issue_data.get("line_number", 0),
                    issue_type=IssueType(issue_data.get("issue_type", "no_issue")),
                    severity=Severity(issue_data.get("severity", "info")),
                    description=issue_data.get("description", ""),
                    suggested_fix=issue_data.get("suggested_fix"),
                )
            
            action = CodeReviewerAction(
                action_type=action_data.get("action_type", "submit_review"),
                issue=issue,
                confidence=action_data.get("confidence", 0.5),
                reasoning=action_data.get("reasoning"),
            )
            
            # Execute step
            observation, reward, done, info = env.step(action)
            
            # Log step
            action_str = f"{action.action_type}"
            if action.issue:
                action_str += f"(line={action.issue.line_number},type={action.issue.issue_type.value})"
            
            log_step(step, action_str, reward.step_reward, done, info.get("error"))
            rewards_list.append(reward.step_reward)
            
        except Exception as e:
            error = str(e)
            log_step(step, "action_error", 0.0, True, error)
            rewards_list.append(0.0)
            done = True
    
    # Get final result
    try:
        result = env.get_review_result()
        final_score = result.completion_score
        success = final_score >= SUCCESS_SCORE_THRESHOLD
    except:
        # Episode didn't complete properly
        final_score = 0.0
        success = False
    
    log_end(success, step, final_score, rewards_list)
    
    return success, step, final_score, rewards_list


def main():
    """Main entry point."""
    # Initialize OpenAI client
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=API_KEY,
    )
    
    # Run episode
    success, steps, score, rewards = run_episode(client, TASK_NAME)
    
    # Return exit code based on success
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

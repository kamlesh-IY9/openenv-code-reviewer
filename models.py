"""
Typed Pydantic models for Code Reviewer Environment.
All models follow OpenEnv specification.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class IssueType(str, Enum):
    """Types of code issues that can be identified."""
    SYNTAX_ERROR = "syntax_error"
    LOGIC_BUG = "logic_bug"
    SECURITY_VULNERABILITY = "security_vulnerability"
    PERFORMANCE_ISSUE = "performance_issue"
    STYLE_VIOLATION = "style_violation"
    NO_ISSUE = "no_issue"


class Severity(str, Enum):
    """Severity levels for identified issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CodeIssue(BaseModel):
    """Represents a single code issue identified by the agent."""
    line_number: int = Field(..., description="Line number where issue occurs (1-indexed)")
    issue_type: IssueType = Field(..., description="Type of issue identified")
    severity: Severity = Field(..., description="Severity level of the issue")
    description: str = Field(..., description="Description of the issue")
    suggested_fix: Optional[str] = Field(None, description="Suggested code fix")


class CodeSnippet(BaseModel):
    """Represents a code snippet to be reviewed."""
    language: str = Field(..., description="Programming language of the code")
    code: str = Field(..., description="The actual code to review")
    filename: Optional[str] = Field(None, description="Original filename if available")
    context: Optional[str] = Field(None, description="Additional context about the code")


class CodeReviewerObservation(BaseModel):
    """
    Observation returned by the environment after each step.
    Contains the current state visible to the agent.
    """
    code_snippet: CodeSnippet = Field(..., description="The code snippet to review")
    task_description: str = Field(..., description="Description of current task")
    task_difficulty: str = Field(..., description="Difficulty level: easy/medium/hard")
    step_number: int = Field(..., description="Current step number in episode")
    max_steps: int = Field(..., description="Maximum steps allowed in episode")
    previous_issues: List[CodeIssue] = Field(default_factory=list, description="Issues identified so far")
    hint_available: bool = Field(False, description="Whether a hint is available")
    hint_text: Optional[str] = Field(None, description="Hint text if available")
    done: bool = Field(False, description="Whether episode is complete")
    info: Dict[str, Any] = Field(default_factory=dict, description="Additional info")


class CodeReviewerAction(BaseModel):
    """
    Action sent by the agent to the environment.
    Agent can either identify an issue or submit final review.
    """
    action_type: str = Field(..., description="Type of action: 'identify_issue', 'submit_review', 'request_hint'")
    issue: Optional[CodeIssue] = Field(None, description="Issue details if action_type is 'identify_issue'")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Agent's confidence in action (0-1)")
    reasoning: Optional[str] = Field(None, description="Agent's reasoning for the action")


class CodeReviewerReward(BaseModel):
    """
    Reward structure for the code reviewer environment.
    Provides detailed feedback on agent performance.
    """
    total_reward: float = Field(..., description="Total cumulative reward for episode")
    step_reward: float = Field(..., description="Reward for current step")
    issue_detection_reward: float = Field(0.0, description="Reward for correctly identifying issues")
    false_positive_penalty: float = Field(0.0, description="Penalty for incorrect issue reports")
    completeness_reward: float = Field(0.0, description="Reward for finding all issues")
    efficiency_reward: float = Field(0.0, description="Reward for completing task efficiently")
    task_completion_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall task completion score (0-1)")


class TaskConfig(BaseModel):
    """Configuration for a specific task."""
    name: str = Field(..., description="Task identifier")
    description: str = Field(..., description="Human-readable task description")
    difficulty: str = Field(..., description="easy/medium/hard")
    code_snippet: CodeSnippet = Field(..., description="Code to review")
    expected_issues: List[CodeIssue] = Field(..., description="Ground truth issues")
    hints: List[str] = Field(default_factory=list, description="Available hints")
    max_steps: int = Field(20, description="Maximum steps for this task")


class ReviewResult(BaseModel):
    """Result of a code review episode."""
    task_name: str = Field(..., description="Task that was reviewed")
    identified_issues: List[CodeIssue] = Field(default_factory=list, description="Issues agent found")
    missed_issues: List[CodeIssue] = Field(default_factory=list, description="Issues agent missed")
    false_positives: List[CodeIssue] = Field(default_factory=list, description="Incorrectly reported issues")
    total_reward: float = Field(0.0, description="Total reward earned")
    completion_score: float = Field(0.0, ge=0.0, le=1.0, description="Final completion score")
    steps_taken: int = Field(0, description="Number of steps used")
    success: bool = Field(False, description="Whether task was completed successfully")

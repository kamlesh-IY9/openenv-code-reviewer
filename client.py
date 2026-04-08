"""
Code Reviewer Environment - OpenEnv Client
HTTP/WebSocket client for connecting to the environment.
"""

import os
import json
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, asdict
import asyncio
import websockets
import httpx


@dataclass
class CodeReviewerAction:
    action_type: str
    issue: Optional[Dict] = None
    confidence: float = 1.0
    reasoning: Optional[str] = None


@dataclass
class CodeReviewerObservation:
    code_snippet: Dict
    task_description: str
    task_difficulty: str
    step_number: int
    max_steps: int
    previous_issues: List
    hint_available: bool
    hint_text: Optional[str]
    done: bool
    info: Dict


@dataclass
class CodeReviewerReward:
    total_reward: float
    step_reward: float
    issue_detection_reward: float
    false_positive_penalty: float
    completeness_reward: float
    efficiency_reward: float
    task_completion_score: float


@dataclass 
class ReviewResult:
    task_name: str
    identified_issues: List
    missed_issues: List
    false_positives: List
    total_reward: float
    completion_score: float
    steps_taken: int
    success: bool


class CodeReviewerEnv:
    """
    OpenEnv Client for Code Reviewer Environment.
    
    Supports both sync (HTTP) and async (WebSocket) modes.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:7860",
        task_name: str = "syntax_check",
        session_id: Optional[str] = None,
    ):
        """
        Initialize the environment client.
        
        Args:
            base_url: Base URL of the environment server
            task_name: Default task to run
            session_id: Session ID for stateful connections
        """
        self.base_url = base_url.rstrip("/")
        self.task_name = task_name
        self.session_id = session_id or f"session_{id(self)}"
        self._ws = None
        self._http = httpx.Client(timeout=30.0)
        
    def reset(self, task: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset the environment (HTTP mode).
        
        Args:
            task: Task name override
            
        Returns:
            Reset response with observation
        """
        task = task or self.task_name
        response = self._http.post(
            f"{self.base_url}/reset",
            json={"task": task, "session_id": self.session_id}
        )
        response.raise_for_status()
        return response.json()
    
    def step(self, action: Union[Dict, CodeReviewerAction]) -> Dict[str, Any]:
        """
        Execute a step (HTTP mode).
        
        Args:
            action: Action dict or CodeReviewerAction
            
        Returns:
            Step response with observation, reward, done
        """
        if isinstance(action, CodeReviewerAction):
            action = asdict(action)
            
        response = self._http.post(
            f"{self.base_url}/step",
            json={"session_id": self.session_id, "action": action}
        )
        response.raise_for_status()
        return response.json()
    
    def state(self) -> Dict[str, Any]:
        """Get current state (HTTP mode)."""
        response = self._http.get(f"{self.base_url}/state")
        response.raise_for_status()
        return response.json()
    
    async def async_reset(self, task: Optional[str] = None) -> Dict[str, Any]:
        """Reset the environment (async/WebSocket mode)."""
        await self._ensure_connected()
        task = task or self.task_name
        
        await self._ws.send(json.dumps({
            "action": "reset",
            "task": task
        }))
        
        response = await self._ws.recv()
        data = json.loads(response)
        
        if data.get("type") == "reset_response":
            return data
        elif data.get("type") == "error":
            raise RuntimeError(data.get("message", "Unknown error"))
        else:
            raise RuntimeError(f"Unexpected response type: {data.get('type')}")
    
    async def async_step(self, action: Union[Dict, CodeReviewerAction]) -> Dict[str, Any]:
        """Execute a step (async/WebSocket mode)."""
        await self._ensure_connected()
        
        if isinstance(action, CodeReviewerAction):
            action = asdict(action)
        
        await self._ws.send(json.dumps({
            "action": "step",
            "data": action
        }))
        
        response = await self._ws.recv()
        data = json.loads(response)
        
        if data.get("type") == "step_response":
            return data
        elif data.get("type") == "error":
            raise RuntimeError(data.get("message", "Unknown error"))
        else:
            raise RuntimeError(f"Unexpected response type: {data.get('type')}")
    
    async def async_get_result(self) -> Dict[str, Any]:
        """Get review result (async/WebSocket mode)."""
        await self._ensure_connected()
        
        await self._ws.send(json.dumps({
            "action": "get_result"
        }))
        
        response = await self._ws.recv()
        data = json.loads(response)
        
        if data.get("type") == "result_response":
            return data.get("result")
        elif data.get("type") == "error":
            raise RuntimeError(data.get("message", "Unknown error"))
        else:
            raise RuntimeError(f"Unexpected response type: {data.get('type')}")
    
    async def _ensure_connected(self):
        """Ensure WebSocket is connected."""
        if self._ws is None or self._ws.closed:
            ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
            self._ws = await websockets.connect(f"{ws_url}/ws")
    
    async def close(self):
        """Close the WebSocket connection."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
            self._ws = None
    
    def sync(self):
        """
        Get a synchronous wrapper.
        
        Usage:
            with env.sync() as sync_env:
                sync_env.reset()
        """
        return SyncEnvWrapper(self)
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, '_http'):
            self._http.close()


class SyncEnvWrapper:
    """Synchronous wrapper for async CodeReviewerEnv."""
    
    def __init__(self, async_env: CodeReviewerEnv):
        self._env = async_env
        self._loop = None
        self._task = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def reset(self, task: Optional[str] = None):
        return self._env.reset(task)
    
    def step(self, action: Union[Dict, CodeReviewerAction]):
        return self._env.step(action)
    
    def state(self):
        return self._env.state()


def create_identify_issue_action(
    line_number: int,
    issue_type: str,
    severity: str,
    description: str,
    confidence: float = 0.9,
) -> Dict:
    """Helper to create an identify_issue action."""
    return {
        "action_type": "identify_issue",
        "issue": {
            "line_number": line_number,
            "issue_type": issue_type,
            "severity": severity,
            "description": description,
        },
        "confidence": confidence,
    }


def create_submit_review_action() -> Dict:
    """Helper to create a submit_review action."""
    return {"action_type": "submit_review"}


def create_hint_action() -> Dict:
    """Helper to create a request_hint action."""
    return {"action_type": "request_hint"}

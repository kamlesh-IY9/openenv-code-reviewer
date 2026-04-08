"""
Code Reviewer Environment - Server Implementation
FastAPI server with WebSocket support for OpenEnv deployment.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from server.environment import CodeReviewerEnv
from models import CodeReviewerAction, CodeIssue
from tasks import get_task_names


env_store: Dict[str, CodeReviewerEnv] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Code Reviewer Environment Server...")
    yield
    print("Shutting down server...")


app = FastAPI(
    title="Code Reviewer Environment",
    description="OpenEnv environment for code review tasks - Train AI agents to review code",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Interactive web UI for the environment."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Reviewer Environment</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            background: #0f172a; 
            color: #e2e8f0;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        header { 
            text-align: center; 
            padding: 30px 0;
            border-bottom: 1px solid #334155;
            margin-bottom: 30px;
        }
        h1 { 
            font-size: 2.5em; 
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .subtitle { color: #94a3b8; font-size: 1.1em; }
        
        .setup-panel {
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #334155;
        }
        .setup-panel h2 { margin-bottom: 16px; color: #60a5fa; }
        
        .task-selector {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .task-btn {
            flex: 1;
            min-width: 200px;
            padding: 16px 20px;
            border: 2px solid #334155;
            border-radius: 8px;
            background: #1e293b;
            color: #e2e8f0;
            cursor: pointer;
            transition: all 0.3s;
            text-align: left;
        }
        .task-btn:hover { border-color: #60a5fa; }
        .task-btn.active { 
            border-color: #60a5fa; 
            background: rgba(96, 165, 250, 0.1);
        }
        .task-btn .name { font-weight: bold; font-size: 1.1em; }
        .task-btn .desc { color: #94a3b8; margin-top: 4px; }
        .task-btn .difficulty { 
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-top: 8px;
        }
        .difficulty-easy { background: #22c55e; color: #052e16; }
        .difficulty-medium { background: #eab308; color: #422006; }
        .difficulty-hard { background: #ef4444; color: #450a0a; }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        @media (max-width: 900px) {
            .main-content { grid-template-columns: 1fr; }
        }
        
        .panel {
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
        }
        .panel h3 { 
            margin-bottom: 16px; 
            padding-bottom: 12px;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .code-display {
            background: #0f172a;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            max-height: 400px;
            overflow-y: auto;
        }
        .code-display pre {
            font-family: 'Fira Code', 'Monaco', monospace;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        .line-number {
            color: #475569;
            user-select: none;
            margin-right: 16px;
        }
        
        .issue-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .issue-item {
            background: #0f172a;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #60a5fa;
        }
        .issue-item.found { border-left-color: #22c55e; }
        .issue-item .header { 
            display: flex; 
            justify-content: space-between;
            margin-bottom: 6px;
        }
        .issue-item .type { font-weight: bold; color: #60a5fa; }
        .issue-item .line { color: #94a3b8; }
        .issue-item .desc { color: #cbd5e1; font-size: 0.9em; }
        
        .action-form { margin-top: 16px; }
        .action-form input, .action-form select, .action-form textarea {
            width: 100%;
            padding: 10px 12px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            color: #e2e8f0;
            margin-bottom: 12px;
        }
        .action-form textarea { min-height: 80px; font-family: inherit; }
        .btn-group { display: flex; gap: 12px; flex-wrap: wrap; }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            font-size: 1em;
        }
        .btn-primary { background: #60a5fa; color: #0f172a; }
        .btn-primary:hover { background: #3b82f6; }
        .btn-success { background: #22c55e; color: #052e16; }
        .btn-success:hover { background: #16a34a; }
        .btn-warning { background: #eab308; color: #422006; }
        .btn-warning:hover { background: #ca8a04; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .status-bar {
            display: flex;
            justify-content: space-between;
            padding: 12px 16px;
            background: #0f172a;
            border-radius: 8px;
            margin-top: 16px;
        }
        .status-item { text-align: center; }
        .status-item .value { font-size: 1.5em; font-weight: bold; color: #60a5fa; }
        .status-item .label { color: #94a3b8; font-size: 0.85em; }
        
        .log-area {
            background: #0f172a;
            border-radius: 8px;
            padding: 16px;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Fira Code', monospace;
            font-size: 13px;
        }
        .log-entry { margin-bottom: 4px; }
        .log-step { color: #60a5fa; }
        .log-reward { color: #22c55e; }
        .log-error { color: #ef4444; }
        
        .result-panel {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 2px solid;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
        }
        .result-panel.success { border-color: #22c55e; }
        .result-panel.failure { border-color: #ef4444; }
        .result-score { font-size: 4em; font-weight: bold; }
        .result-panel.success .result-score { color: #22c55e; }
        .result-panel.failure .result-score { color: #ef4444; }
        .result-stats { display: flex; justify-content: center; gap: 30px; margin-top: 16px; }
        
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Code Reviewer Environment</h1>
            <p class="subtitle">OpenEnv RL Environment for Training Code Review Agents</p>
        </header>
        
        <div class="setup-panel">
            <h2>🎯 Select Task</h2>
            <div class="task-selector">
                <button class="task-btn active" data-task="syntax_check">
                    <div class="name">Syntax Check</div>
                    <div class="desc">Find syntax errors in Python code</div>
                    <span class="difficulty difficulty-easy">Easy</span>
                </button>
                <button class="task-btn" data-task="logic_bug_detection">
                    <div class="name">Logic Bug Detection</div>
                    <div class="desc">Identify logic bugs causing incorrect behavior</div>
                    <span class="difficulty difficulty-medium">Medium</span>
                </button>
                <button class="task-btn" data-task="security_audit">
                    <div class="name">Security Audit</div>
                    <div class="desc">Find security vulnerabilities</div>
                    <span class="difficulty difficulty-hard">Hard</span>
                </button>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary" id="startBtn">🚀 Start Episode</button>
                <button class="btn btn-danger" id="resetBtn" disabled>🔄 Reset</button>
            </div>
        </div>
        
        <div class="main-content">
            <div class="panel">
                <h3>📝 Code Snippet <span id="taskName">-</span></h3>
                <div class="code-display">
                    <pre id="codeDisplay"><span style="color: #94a3b8;">Select a task and click Start Episode</span></pre>
                </div>
                
                <div class="status-bar">
                    <div class="status-item">
                        <div class="value" id="stepNum">0</div>
                        <div class="label">Step</div>
                    </div>
                    <div class="status-item">
                        <div class="value" id="maxSteps">-</div>
                        <div class="label">Max Steps</div>
                    </div>
                    <div class="status-item">
                        <div class="value" id="issuesFound">0</div>
                        <div class="label">Issues Found</div>
                    </div>
                    <div class="status-item">
                        <div class="value" id="reward">0.00</div>
                        <div class="label">Reward</div>
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h3>🔍 Actions</h3>
                <div class="action-form">
                    <label>Line Number:</label>
                    <input type="number" id="lineNum" placeholder="Line number" min="1">
                    
                    <label>Issue Type:</label>
                    <select id="issueType">
                        <option value="syntax_error">Syntax Error</option>
                        <option value="logic_bug">Logic Bug</option>
                        <option value="security_vulnerability">Security Vulnerability</option>
                    </select>
                    
                    <label>Severity:</label>
                    <select id="severity">
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    
                    <label>Description:</label>
                    <textarea id="issueDesc" placeholder="Describe the issue..."></textarea>
                    
                    <div class="btn-group">
                        <button class="btn btn-success" id="identifyBtn" disabled>✅ Identify Issue</button>
                        <button class="btn btn-warning" id="hintBtn" disabled>💡 Get Hint</button>
                        <button class="btn btn-primary" id="submitBtn" disabled>📤 Submit Review</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="panel" style="margin-top: 24px;">
            <h3>📊 Identified Issues</h3>
            <div class="issue-list" id="issueList">
                <p style="color: #94a3b8;">No issues identified yet</p>
            </div>
        </div>
        
        <div class="panel" style="margin-top: 24px;">
            <h3>📜 Action Log</h3>
            <div class="log-area" id="logArea">
                <div class="log-entry" style="color: #94a3b8;">Ready to start...</div>
            </div>
        </div>
        
        <div class="result-panel hidden" id="resultPanel">
            <h2 id="resultTitle">Episode Complete!</h2>
            <div class="result-score" id="resultScore">0.00</div>
            <p id="resultMessage">Completion Score</p>
            <div class="result-stats">
                <div><strong id="foundCount">0</strong><br><small>Found</small></div>
                <div><strong id="missedCount">0</strong><br><small>Missed</small></div>
                <div><strong id="fpCount">0</strong><br><small>False Positives</small></div>
                <div><strong id="finalSteps">0</strong><br><small>Steps Taken</small></div>
            </div>
        </div>
    </div>
    
    <script>
        const state = {
            ws: null,
            sessionId: null,
            currentTask: 'syntax_check',
            started: false,
            completed: false
        };
        
        function log(msg, type='') {
            const area = document.getElementById('logArea');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.textContent = `> ${msg}`;
            area.appendChild(entry);
            area.scrollTop = area.scrollHeight;
        }
        
        function updateStatus(data) {
            if (data.observation) {
                document.getElementById('stepNum').textContent = data.observation.step_number || 0;
                document.getElementById('maxSteps').textContent = data.observation.max_steps || '-';
                document.getElementById('issuesFound').textContent = data.observation.previous_issues?.length || 0;
            }
            if (data.reward) {
                document.getElementById('reward').textContent = data.reward.total_reward?.toFixed(2) || '0.00';
            }
        }
        
        function displayCode(code, language='python') {
            const lines = code.split('\\n');
            const html = lines.map((line, i) => 
                `<span class="line-number">${String(i+1).padStart(3, ' ')}</span>${escapeHtml(line)}`
            ).join('\\n');
            document.getElementById('codeDisplay').innerHTML = html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function displayIssues(issues) {
            const list = document.getElementById('issueList');
            if (!issues || issues.length === 0) {
                list.innerHTML = '<p style="color: #94a3b8;">No issues identified yet</p>';
                return;
            }
            list.innerHTML = issues.map(issue => `
                <div class="issue-item found">
                    <div class="header">
                        <span class="type">${issue.issue_type?.replace('_', ' ') || 'Unknown'}</span>
                        <span class="line">Line ${issue.line_number}</span>
                    </div>
                    <div class="desc">${issue.description || ''}</div>
                    <div style="margin-top: 4px;">
                        <span style="padding: 2px 6px; background: ${
                            issue.severity === 'critical' ? '#ef4444' :
                            issue.severity === 'high' ? '#f97316' :
                            issue.severity === 'medium' ? '#eab308' : '#22c55e'
                        }; border-radius: 4px; font-size: 0.8em;">
                            ${issue.severity?.toUpperCase() || 'LOW'}
                        </span>
                    </div>
                </div>
            `).join('');
        }
        
        function showResult(result) {
            const panel = document.getElementById('resultPanel');
            panel.classList.remove('hidden', 'success', 'failure');
            panel.classList.add(result.success ? 'success' : 'failure');
            
            document.getElementById('resultTitle').textContent = result.success ? '🎉 Success!' : '❌ Try Again';
            document.getElementById('resultScore').textContent = result.completion_score?.toFixed(2) || '0.00';
            document.getElementById('resultMessage').textContent = result.success ? 
                'Above 70% threshold - Great job!' : 'Below 70% threshold';
            document.getElementById('foundCount').textContent = result.identified_issues?.length || 0;
            document.getElementById('missedCount').textContent = result.missed_issues?.length || 0;
            document.getElementById('fpCount').textContent = result.false_positives?.length || 0;
            document.getElementById('finalSteps').textContent = result.steps_taken || 0;
            
            panel.scrollIntoView({ behavior: 'smooth' });
        }
        
        async function connectWS() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            state.ws = new WebSocket(wsUrl);
            
            state.ws.onopen = () => {
                log('WebSocket connected', 'log-step');
                resetEpisode();
            };
            
            state.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            state.ws.onclose = () => {
                log('WebSocket disconnected - Reconnecting...', 'log-error');
                setTimeout(connectWS, 2000);
            };
            
            state.ws.onerror = (err) => {
                log('WebSocket error', 'log-error');
            };
        }
        
        function handleMessage(data) {
            if (data.type === 'reset_response') {
                state.sessionId = data.session_id;
                state.started = true;
                state.completed = false;
                
                const obs = data.observation;
                document.getElementById('taskName').textContent = obs.task_difficulty?.toUpperCase() || '';
                document.getElementById('startBtn').disabled = true;
                document.getElementById('resetBtn').disabled = false;
                document.getElementById('identifyBtn').disabled = false;
                document.getElementById('hintBtn').disabled = false;
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('resultPanel').classList.add('hidden');
                
                displayCode(obs.code_snippet?.code || '');
                displayIssues([]);
                updateStatus({ observation: obs });
                
                log(`Episode started: ${obs.task_description}`, 'log-step');
            }
            else if (data.type === 'step_response') {
                const obs = data.observation;
                updateStatus(data);
                displayIssues(obs.previous_issues);
                
                if (data.done) {
                    state.completed = true;
                    document.getElementById('identifyBtn').disabled = true;
                    document.getElementById('hintBtn').disabled = true;
                    document.getElementById('submitBtn').disabled = true;
                    
                    log(`Episode complete! Score: ${data.reward?.task_completion_score?.toFixed(2) || 0}`, 'log-reward');
                }
            }
            else if (data.type === 'result_response') {
                showResult(data.result);
            }
            else if (data.type === 'error') {
                log(`Error: ${data.message}`, 'log-error');
            }
        }
        
        function resetEpisode() {
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({
                    action: 'reset',
                    task: state.currentTask
                }));
            }
        }
        
        function sendAction(actionData) {
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({
                    action: 'step',
                    data: actionData
                }));
            }
        }
        
        function getResult() {
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({
                    action: 'get_result'
                }));
            }
        }
        
        // Event Listeners
        document.querySelectorAll('.task-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.task-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentTask = btn.dataset.task;
                
                if (state.started) {
                    resetEpisode();
                }
            });
        });
        
        document.getElementById('startBtn').addEventListener('click', resetEpisode);
        
        document.getElementById('resetBtn').addEventListener('click', () => {
            state.started = false;
            state.completed = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('resetBtn').disabled = true;
            document.getElementById('identifyBtn').disabled = true;
            document.getElementById('hintBtn').disabled = true;
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('codeDisplay').innerHTML = '<span style="color: #94a3b8;">Select a task and click Start Episode</span>';
            document.getElementById('issueList').innerHTML = '<p style="color: #94a3b8;">No issues identified yet</p>';
            document.getElementById('logArea').innerHTML = '<div class="log-entry" style="color: #94a3b8;">Ready to start...</div>';
            resetEpisode();
        });
        
        document.getElementById('identifyBtn').addEventListener('click', () => {
            const lineNum = parseInt(document.getElementById('lineNum').value) || 1;
            const issueType = document.getElementById('issueType').value;
            const severity = document.getElementById('severity').value;
            const desc = document.getElementById('issueDesc').value || 'Issue identified';
            
            sendAction({
                action_type: 'identify_issue',
                issue: {
                    line_number: lineNum,
                    issue_type: issueType,
                    severity: severity,
                    description: desc
                },
                confidence: 0.9
            });
            
            log(`Identify issue: Line ${lineNum}, ${issueType}`, 'log-step');
        });
        
        document.getElementById('hintBtn').addEventListener('click', () => {
            sendAction({ action_type: 'request_hint' });
            log('Request hint', 'log-step');
        });
        
        document.getElementById('submitBtn').addEventListener('click', () => {
            sendAction({ action_type: 'submit_review' });
            log('Submit review', 'log-step');
            
            setTimeout(getResult, 500);
        });
        
        // Connect on load
        connectWS();
    </script>
</body>
</html>
    """


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "running",
        "environment": "code-reviewer-env",
        "version": "1.0.0",
        "available_tasks": get_task_names(),
        "active_sessions": len(env_store),
    }


@app.get("/state")
async def get_state():
    """Get current server state."""
    return {
        "active_sessions": len(env_store),
        "environment": "code-reviewer-env",
        "tasks": {
            "syntax_check": {"difficulty": "easy", "description": "Find syntax errors"},
            "logic_bug_detection": {
                "difficulty": "medium",
                "description": "Find logic bugs",
            },
            "security_audit": {
                "difficulty": "hard",
                "description": "Find security vulnerabilities",
            },
        },
    }


@app.post("/reset")
async def reset_endpoint(request: Dict[str, Any]):
    """Reset endpoint for HTTP API compatibility."""
    try:
        task_name = request.get("task", "syntax_check")
        session_id = request.get("session_id", "default")

        env = CodeReviewerEnv(task_name=task_name)
        observation = env.reset(task_name)

        env_store[session_id] = env

        return JSONResponse(
            content={
                "observation": observation.model_dump(),
                "session_id": session_id,
                "status": "success",
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"error": str(e), "status": "error"}
        )


@app.post("/step")
async def step_endpoint(request: Dict[str, Any]):
    """Step endpoint for HTTP API compatibility."""
    try:
        session_id = request.get("session_id", "default")
        action_data = request.get("action", {})

        if session_id not in env_store:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Session not found. Call /reset first.",
                    "status": "error",
                },
            )

        env = env_store[session_id]
        action = CodeReviewerAction(**action_data)
        observation, reward, done, info = env.step(action)

        return JSONResponse(
            content={
                "observation": observation.model_dump(),
                "reward": reward.model_dump(),
                "done": done,
                "info": info,
                "status": "success",
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=400, content={"error": str(e), "status": "error"}
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time environment interaction."""
    await websocket.accept()
    session_id = str(id(websocket))
    env: Optional[CodeReviewerEnv] = None

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "reset":
                task_name = data.get("task", "syntax_check")
                env = CodeReviewerEnv(task_name=task_name)
                observation = env.reset(task_name)
                env_store[session_id] = env

                await websocket.send_json(
                    {
                        "type": "reset_response",
                        "observation": observation.model_dump(),
                        "session_id": session_id,
                    }
                )

            elif action == "step":
                if env is None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Environment not initialized. Send reset first.",
                        }
                    )
                    continue

                action_data = data.get("data", {})
                action_obj = CodeReviewerAction(**action_data)
                observation, reward, done, info = env.step(action_obj)

                await websocket.send_json(
                    {
                        "type": "step_response",
                        "observation": observation.model_dump(),
                        "reward": reward.model_dump(),
                        "done": done,
                        "info": info,
                    }
                )

            elif action == "state":
                if env is None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Environment not initialized.",
                        }
                    )
                    continue

                state = env.state()
                await websocket.send_json(
                    {
                        "type": "state_response",
                        "state": state,
                    }
                )

            elif action == "get_result":
                if env is None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Environment not initialized.",
                        }
                    )
                    continue

                try:
                    result = env.get_review_result()
                    await websocket.send_json(
                        {
                            "type": "result_response",
                            "result": result.model_dump(),
                        }
                    )
                except RuntimeError as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    }
                )

    except WebSocketDisconnect:
        if session_id in env_store:
            del env_store[session_id]

    except Exception as e:
        if session_id in env_store:
            del env_store[session_id]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

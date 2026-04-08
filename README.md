# &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ``Code Reviewer Environment``

<div align="center">

![OpenEnv](https://img.shields.io/badge/OpenEnv-Hackathon-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![License](https://img.shields.io/badge/License-MIT-orange)

**An RL environment for training AI agents to perform code review tasks**

[Features](#features) • [Quick Start](#quick-start) • [API](#environment-api) • [Deployment](#deployment) • [GitHub Setup](#github-setup)

</div>

---

## Demo 
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/d52f65c7-cbc6-47d2-8fcd-804056762289" />


## Overview

The Code Reviewer Environment is an OpenEnv-compatible RL environment that trains AI agents to perform code review tasks. Agents learn to identify:

- **Syntax Errors** (Easy) - Missing colons, unclosed brackets, indentation issues
- **Logic Bugs** (Medium) - Off-by-one errors, incorrect comparisons
- **Security Vulnerabilities** (Hard) - SQL injection, XSS, command injection 

```
┌─────────────────────────────────────────────────────────────┐
│                    CODE REVIEWER AGENT                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐    Action    ┌──────────────────────┐   │
│   │   Python     │ ──────────► │   Identify Issue     │   │
│   │   Code       │              │   Submit Review      │   │
│   │   Snippet    │ ◄────────── │   Request Hint       │   │
│   └──────────────┘   Obs/Reward └──────────────────────┘   │
│                                                             │
│   Task: Find 7 syntax errors → Score: 0.85/1.0            │
└─────────────────────────────────────────────────────────────┘
```

## Interface Preview

| Desktop | Mobile |
|---------|--------|
| ![Desktop UI](assets/screenshots/ui-desktop.png) | ![Mobile UI](assets/screenshots/ui-mobile.png) |

## Features

| Feature | Description |
|---------|-------------|
| **3 Difficulty Levels** | Easy → Medium → Hard progression |
| **Typed Models** | Full Pydantic v2 type safety |
| **Meaningful Rewards** | Partial credit, penalties for false positives |
| **Comprehensive Grading** | Deterministic evaluation |
| **API + WebSocket** | HTTP REST and WebSocket support |
| **Docker Ready** | One-command deployment to HF Spaces |

---

## Quick Start

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/openenv-code-reviewer.git
cd openenv-code-reviewer

# Install dependencies
pip install -r requirements.txt
```

### 2. Test Locally

```bash
# Run the test suite
python test_environment.py

# Output should show: Passed: 8/8 ✓
```

### 3. Start the Server

```bash
# Start API server on port 7860 with interactive web UI
python server.py

# Or run the app module directly
cd server
python app.py

# Server is now running at http://localhost:7860
```

### 4. Try the Environment

```python
from environment import CodeReviewerEnv
from models import CodeReviewerAction, CodeIssue, IssueType, Severity

# Create environment
env = CodeReviewerEnv(task_name="syntax_check")
observation = env.reset()

print(f"Task: {observation.task_description}")
print(f"Code to review:\n{observation.code_snippet.code}")

# Identify an issue
action = CodeReviewerAction(
    action_type="identify_issue",
    issue=CodeIssue(
        line_number=5,
        issue_type=IssueType.SYNTAX_ERROR,
        severity=Severity.HIGH,
        description="Missing colon after function definition",
        suggested_fix="Add colon at end of line"
    ),
    confidence=0.9
)

# Take step
observation, reward, done, info = env.step(action)
print(f"Reward: {reward.step_reward}")

# Submit review when done
if done:
    result = env.get_review_result()
    print(f"Score: {result.completion_score}")
```

---

## Tasks

### Task 1: Syntax Check (Easy)

Find syntax errors in Python code.

```
Expected Issues: 7 syntax errors
Max Steps: 15
Success Threshold: 70%
```

### Task 2: Logic Bug Detection (Medium)

Identify logic bugs causing incorrect behavior.

```
Expected Issues: 3 logic bugs
Max Steps: 18
Success Threshold: 70%
```

### Task 3: Security Audit (Hard)

Find security vulnerabilities in code.

```
Expected Issues: 9 security vulnerabilities
Max Steps: 25
Success Threshold: 70%
```

---

## Observation Space

Each step returns a `CodeReviewerObservation` with the following fields:

| Field | Type | Purpose |
|-------|------|---------|
| `code_snippet` | `CodeSnippet` | Source code under review, including language and optional context |
| `task_description` | `str` | The current review objective |
| `task_difficulty` | `str` | Difficulty label: `easy`, `medium`, or `hard` |
| `step_number` | `int` | Current step in the episode |
| `max_steps` | `int` | Total step budget for the task |
| `previous_issues` | `List[CodeIssue]` | Issues already reported by the agent |
| `hint_available` | `bool` | Whether the agent can still request a hint |
| `hint_text` | `Optional[str]` | Latest hint returned by the environment |
| `done` | `bool` | Whether the episode has ended |
| `info` | `Dict[str, Any]` | Extra metadata such as expected issue count |

## Action Space

Agents send a `CodeReviewerAction` using one of three actions:

| Action | Required fields | Purpose |
|--------|-----------------|---------|
| `identify_issue` | `issue` | Report a suspected syntax error, logic bug, or vulnerability |
| `request_hint` | none | Ask for a hint with a small reward penalty |
| `submit_review` | none | End the episode and score the review |

When `action_type` is `identify_issue`, the nested `issue` payload includes:

| Field | Type | Purpose |
|-------|------|---------|
| `line_number` | `int` | 1-indexed line number of the issue |
| `issue_type` | `IssueType` | Category such as `syntax_error` or `security_vulnerability` |
| `severity` | `Severity` | Impact level for the issue |
| `description` | `str` | Human-readable explanation of the finding |
| `suggested_fix` | `Optional[str]` | Suggested repair |

---

## Environment API

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Interactive browser UI |
| `/health` | GET | Health check for local or HF deployment |
| `/state` | GET | Get environment state |
| `/reset` | POST | Reset environment with task |
| `/step` | POST | Execute an action |

### Example API Usage

```bash
# Reset environment
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "syntax_check", "session_id": "demo"}'

# Identify an issue
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo",
    "action": {
      "action_type": "identify_issue",
      "issue": {
        "line_number": 5,
        "issue_type": "syntax_error",
        "severity": "high",
        "description": "Missing colon"
      }
    }
  }'

# Submit review
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "action": {"action_type": "submit_review"}}'
```

### WebSocket API

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:7860/ws");

// Reset environment
ws.send(JSON.stringify({action: "reset", task: "syntax_check"}));

// Take step
ws.send(JSON.stringify({
  action: "step",
  data: {
    action_type: "identify_issue",
    issue: {line_number: 5, issue_type: "syntax_error", ...}
  }
}));

// Get state
ws.send(JSON.stringify({action: "state"}));

// Get result
ws.send(JSON.stringify({action: "get_result"}));
```

---

## Reward Structure

| Action | Reward |
|--------|--------|
| Correct issue identified | +0.2 to +0.5 (based on severity) |
| False positive reported | -0.15 |
| Hint requested | -0.05 |
| Completeness bonus | Up to +0.5 |
| Efficiency bonus | +0.02 per step saved |

---

## Deployment

### Hugging Face Spaces

1. **Create a new Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Select **Docker** as the SDK
   - Choose **CPU** hardware (free tier)

2. **Deploy**
   ```bash
   # Clone your new Space
   git clone https://huggingface.co/spaces/YOUR_USERNAME/code-reviewer-env
   cd code-reviewer-env
   
   # Copy project files
   cp -r /path/to/openenv-code-reviewer/* .
   
   # Push to Hugging Face
   git add .
   git commit -m "Deploy Code Reviewer Environment"
   git push
   ```

3. **Verify Deployment**
   ```bash
   curl https://YOUR_USERNAME-code-reviewer-env.hf.space/health
   # Should return JSON with status="running"
   ```

### Local Docker

```bash
# Build
docker build -t code-reviewer-env .

# Run
docker run -p 7860:7860 code-reviewer-env

# Test
curl http://localhost:7860/health
```

---

## GitHub Setup

### 1. Create GitHub Repository

```bash
# Initialize git
git init

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/openenv-code-reviewer.git

# Create .gitignore
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo "*.egg-info/" >> .gitignore

# Add and commit
git add .
git commit -m "Initial commit: Code Reviewer Environment for OpenEnv Hackathon"

# Push
git branch -M main
git push -u origin main
```

### 2. Link to Hugging Face Spaces

1. Go to your Hugging Face Space Settings
2. Under "Linked Accounts", connect GitHub
3. Enable "Auto-redeploy on push"

### 3. GitHub Actions CI/CD (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to HF Spaces

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Push to HF Spaces
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git clone https://huggingface.co/spaces/${{ secrets.HF_SPACE_NAME }}
          cp -r . hf_space/
          cd hf_space
          git add .
          git commit -m "Auto-deploy from GitHub"
          git push
```

### 4. Set GitHub Secrets

1. Go to GitHub → Settings → Secrets and variables → Actions
2. Add:
   - `HF_TOKEN`: Your Hugging Face write token
   - `HF_SPACE_NAME`: Your space name (e.g., `username/code-reviewer-env`)

---

## Running Inference

### Set Environment Variables

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your-hf-token-here"
```

### Run for Each Task

```bash
# Task 1: Syntax Check
export CODE_REVIEWER_TASK="syntax_check"
python inference.py

# Task 2: Logic Bug Detection
export CODE_REVIEWER_TASK="logic_bug_detection"
python inference.py

# Task 3: Security Audit
export CODE_REVIEWER_TASK="security_audit"
python inference.py
```

### Expected Output Format

```
[START] task=syntax_check env=code-reviewer-env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=identify_issue(line=5,type=syntax_error) reward=0.40 done=false error=null
[STEP] step=2 action=identify_issue(line=10,type=syntax_error) reward=0.40 done=false error=null
...
[END] success=true steps=12 rewards=0.40,0.40,0.30,0.55
```

---

## Project Structure

```
openenv-code-reviewer/
├── .github/
│   └── workflows/
│       └── test.yml          # GitHub Actions CI/CD
├── server.py                 # Root compatibility server entrypoint
├── server/
│   ├── app.py               # FastAPI + WebSocket server (with Web UI)
│   ├── environment.py       # Core RL environment logic
│   ├── Dockerfile           # Container definition
│   └── __init__.py
├── models.py                 # Pydantic data models
├── tasks.py                  # Task definitions (3 tasks)
├── client.py                 # OpenEnv HTTP/WebSocket client
├── inference.py              # Baseline LLM agent
├── validate.py               # Pre-submission validation
├── test_environment.py       # Test suite
├── openenv.yaml              # OpenEnv specification
├── pyproject.toml            # pip-installable package config
├── requirements.txt          # Python dependencies
├── quickstart.sh             # Quick start script
├── README.md                 # This file
├── DEPLOYMENT.md             # Deployment guide
└── LICENSE                   # MIT License
```

---

## Validation

Run the pre-submission validation:

```bash
python test_environment.py

# All tests should pass: Passed: 8/8 ✓
```

### Validation Checklist

- [x] All 8 tests pass
- [x] API endpoints respond correctly
- [x] WebSocket connections work
- [x] All 3 difficulty levels functional
- [x] Reward system in valid range
- [x] Inference script has required format
- [x] Dockerfile builds successfully
- [x] README documentation complete

---

## Baseline Scores

| Task | Difficulty | Expected Score | Target Steps |
|------|------------|----------------|--------------|
| syntax_check | Easy | 0.85 - 1.00 | 8 - 12 |
| logic_bug_detection | Medium | 0.70 - 0.90 | 10 - 15 |
| security_audit | Hard | 0.60 - 0.80 | 15 - 22 |

---

## Troubleshooting

### Server Won't Start

```bash
# Check port availability
lsof -i :7860

# Kill existing process
pkill -f "python server.py"
```

### Tests Failing

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run with verbose output
python -v test_environment.py
```

### HF Space Deployment Issues

1. Check Space logs in HF dashboard
2. Verify Dockerfile syntax
3. Ensure port 7860 is exposed
4. Check requirements.txt has all dependencies

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built for the OpenEnv Hackathon**

</div>

# Deployment Guide

<div align="center">

**Step-by-step guide to deploy Code Reviewer Environment to Hugging Face Spaces**

</div>

---

## Prerequisites

Before starting, ensure you have:

- [ ] GitHub account
- [ ] Hugging Face account
- [ ] Hugging Face token with **write** access
- [ ] Git installed locally

---

## Step 1: Set Up GitHub Repository

### Option A: From Scratch

```bash
# Create directory and initialize git
mkdir openenv-code-reviewer
cd openenv-code-reviewer

# Initialize git
git init

# Add all project files
git add .

# Create initial commit
git commit -m "Initial commit: Code Reviewer Environment for OpenEnv Hackathon"
```

### Option B: Clone and Modify

```bash
# If you already have the project locally
cd /path/to/your/project

# Initialize git (if not already)
git init

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/openenv-code-reviewer.git
```

### Push to GitHub

```bash
# Create main branch
git branch -M main

# Add .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
*.egg-info/
.pytest_cache/
EOF

# Commit and push
git add .gitignore
git commit -m "Add .gitignore"
git push -u origin main
```

---

## Step 2: Create Hugging Face Space

### Via Web Interface

1. **Go to Hugging Face Spaces**
   ```
   https://huggingface.co/new-space
   ```

2. **Configure your Space**
   ```
   Owner: Your username
   Space Name: code-reviewer-env
   SDK: Docker
   Hardware: CPU (free tier)
   License: MIT
   ```

3. **Click "Create Space"**

### Get Your HF Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New Token"
3. Name it `HF_DEPLOY`
4. Select role: **Write**
5. Copy the token

---

## Step 3: Deploy to Hugging Face

### Option A: Git Clone and Push (Recommended)

```bash
# Install Hugging Face CLI
pip install huggingface-hub

# Login
huggingface-cli login
# Enter your HF token when prompted

# Clone your new Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/code-reviewer-env
cd code-reviewer-env

# Copy all project files
cp -r /path/to/openenv-code-reviewer/* .
cp -r /path/to/openenv-code-reviewer/.* . 2>/dev/null || true

# Verify files
ls -la

# Commit and push
git add .
git commit -m "Deploy Code Reviewer Environment"
git push
```

### Option B: Manual Upload

1. Go to your Space's Files tab
2. Click "Add file" → "Upload files"
3. Drag and drop all project files
4. Commit changes

### Option C: GitHub Integration

1. Go to your Space Settings
2. Find "Linked Accounts"
3. Connect your GitHub account
4. Select repository: `YOUR_USERNAME/openenv-code-reviewer`
5. Enable "Auto-redeploy on push"

---

## Step 4: Verify Deployment

### Wait for Build

Hugging Face Spaces with Docker typically take **2-5 minutes** to build.

### Test Your Deployment

```bash
# Test health endpoint
curl https://YOUR_USERNAME-code-reviewer-env.hf.space/

# Expected response:
{
  "status": "running",
  "environment": "code-reviewer-env",
  "version": "1.0.0",
  "available_tasks": [...]
}
```

### Test Reset Endpoint

```bash
curl -X POST https://YOUR_USERNAME-code-reviewer-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "syntax_check", "session_id": "test"}'

# Expected response:
{
  "observation": {...},
  "session_id": "test",
  "status": "success"
}
```

### Test Step Endpoint

```bash
curl -X POST https://YOUR_USERNAME-code-reviewer-env.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "action": {"action_type": "submit_review"}
  }'
```

---

## Step 5: Run Baseline Inference

### Set Environment Variables

```bash
# SSH into your Space (if needed) or run locally
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_your_token_here"
```

### Run for Each Task

```bash
# Task 1: Syntax Check (Easy)
export CODE_REVIEWER_TASK="syntax_check"
python inference.py

# Expected output:
# [START] task=syntax_check env=code-reviewer-env ...
# [STEP] step=1 action=identify_issue ...
# ...
# [END] success=true steps=12 score=0.857
```

```bash
# Task 2: Logic Bug Detection (Medium)
export CODE_REVIEWER_TASK="logic_bug_detection"
python inference.py
```

```bash
# Task 3: Security Audit (Hard)
export CODE_REVIEWER_TASK="security_audit"
python inference.py
```

---

## Step 6: CI/CD with GitHub Actions

### Create Workflow File

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Hugging Face Spaces

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Push to HF Spaces
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          # Install git lfs
          git lfs install
          
          # Clone HF Space
          git clone https://huggingface.co/spaces/${{ vars.HF_SPACE_NAME }} hf_space
          
          # Copy files
          cp -r . hf_space/
          cd hf_space
          
          # Configure git
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          
          # Commit and push
          git add .
          git commit -m "Auto-deploy from GitHub Actions"
          git push
```

### Set GitHub Secrets

1. Go to: `https://github.com/YOUR_USERNAME/openenv-code-reviewer/settings/secrets/actions`
2. Click "New repository secret"
3. Add:
   - **Name**: `HF_TOKEN`
   - **Secret**: Your Hugging Face write token

4. Go to: `https://github.com/YOUR_USERNAME/openenv-code-reviewer/settings/variables/actions`
5. Add:
   - **Name**: `HF_SPACE_NAME`
   - **Value**: `YOUR_USERNAME/code-reviewer-env`

---

## Step 7: Submit to Hackathon

### Pre-Submission Checklist

```bash
# 1. Run tests
python test_environment.py
# Expected: Passed: 8/8 ✓

# 2. Test server
python server.py &
# Test endpoints...
pkill -f server.py

# 3. Verify deployment
curl https://YOUR_SPACE.hf.space/
```

### Submit

1. Go to the hackathon submission page
2. Fill in:
   - **GitHub Repository**: `https://github.com/YOUR_USERNAME/openenv-code-reviewer`
   - **Hugging Face Space**: `https://YOUR_USERNAME-code-reviewer-env.hf.space`
   - **Demo Video** (optional): Record a quick demo
   - **Description**: Brief explanation of your project

---

## Troubleshooting

### Common Issues

#### 1. HF Space Won't Build

**Error**: Container fails to start

**Solution**:
```bash
# Check Dockerfile syntax
docker build -t test-build .

# Look for errors in local build
docker run test-build
```

#### 2. Port Not Exposed

**Error**: `Connection refused` on HF Space URL

**Solution**: Ensure Dockerfile has:
```dockerfile
EXPOSE 7860
CMD ["python", "server.py"]
```

#### 3. Missing Dependencies

**Error**: `ModuleNotFoundError`

**Solution**: Check `requirements.txt` includes all dependencies:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
websockets>=12.0
python-multipart>=0.0.6
openai>=1.6.0
pyyaml>=6.0
```

#### 4. Cold Start Issues

**Error**: First request times out

**Solution**: This is normal. HF Spaces have 30-60s cold starts. Subsequent requests are faster.

### View Space Logs

1. Go to your Space: `https://huggingface.co/spaces/YOUR_USERNAME/code-reviewer-env`
2. Click "Files and versions"
3. Click "Logs"
4. View `container.log`

### Rebuild Space

If changes don't appear:

1. Go to Space Settings
2. Click "Factory Rebuild"
3. Wait for rebuild to complete

---

## Useful Commands

```bash
# Local testing
python test_environment.py              # Run all tests
python server.py                       # Start server
curl http://localhost:7860/            # Test local server

# Docker
docker build -t code-reviewer .        # Build image
docker run -p 7860:7860 code-reviewer # Run container
docker logs <container_id>            # View logs

# Hugging Face
huggingface-cli login                  # Login to HF
git clone https://huggingface.co/spaces/USERNAME/SPACE_NAME  # Clone Space

# GitHub
git add . && git commit -m "message"  # Commit
git push                               # Push to remote
```

---

## Resources

| Resource | Link |
|----------|------|
| Hugging Face Spaces Docs | https://huggingface.co/docs/hub/spaces |
| Docker Deployment Guide | https://huggingface.co/docs/hub/spaces-sdks-docker |
| OpenEnv Repository | https://github.com/meta-pytorch/OpenEnv |
| Hackathon Discord | Check your hackathon dashboard |

---

<div align="center">

**Good luck with your submission! 🚀**

</div>

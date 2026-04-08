#!/bin/bash
# Quick start script for Code Reviewer Environment

set -e

echo "=========================================="
echo "  Code Reviewer Environment - Quick Start"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q pydantic fastapi uvicorn websockets python-multipart openai pyyaml

# Run validation
echo ""
echo "🔍 Running validation..."
python3 validate.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Set environment variables:"
    echo "     export API_BASE_URL='https://router.huggingface.co/v1'"
    echo "     export MODEL_NAME='Qwen/Qwen2.5-72B-Instruct'"
    echo "     export HF_TOKEN='your-hf-token'"
    echo ""
    echo "  2. Run inference:"
    echo "     export CODE_REVIEWER_TASK='syntax_check'"
    echo "     python3 inference.py"
    echo ""
    echo "  3. Deploy to Hugging Face Spaces (see DEPLOYMENT.md)"
    echo ""
    echo "  4. Submit your entry!"
else
    echo ""
    echo -e "${YELLOW}⚠️  Some checks failed. Please fix issues before submitting.${NC}"
    exit 1
fi

#!/bin/bash
# Local Development Environment Setup Script
# For AI Collab Online

set -e  # Exit on error

echo "🚀 Setting up local development environment for AI Collab Online"
echo "=================================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}❌ Python 3.8+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $PYTHON_VERSION detected${NC}"
echo ""

# Create virtual environment
echo "🐍 Setting up virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment 'venv' already exists${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✅ Virtual environment recreated${NC}"
    else
        echo -e "${GREEN}✅ Using existing virtual environment${NC}"
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✅ pip upgraded${NC}"
echo ""

# Install dependencies
echo "📚 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    # Check Python version for click compatibility
    if [ "$PYTHON_MINOR" -lt 10 ]; then
        echo -e "${YELLOW}⚠️  Python 3.9 detected - adjusting click version for compatibility${NC}"
        # Create temporary requirements with compatible click version
        sed 's/click==8\.2\.1/click==8.1.8/' requirements.txt > requirements_temp.txt
        pip install -r requirements_temp.txt || {
            echo -e "${RED}❌ Failed to install dependencies${NC}"
            rm -f requirements_temp.txt
            exit 1
        }
        rm requirements_temp.txt
    else
        pip install -r requirements.txt || {
            echo -e "${RED}❌ Failed to install dependencies${NC}"
            exit 1
        }
    fi
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Create instance directory for SQLite database
echo "📁 Creating instance directory..."
mkdir -p instance
echo -e "${GREEN}✅ Instance directory created${NC}"
echo ""

# Setup .env file
echo "⚙️  Setting up environment variables..."
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp env_template.txt .env
        echo -e "${GREEN}✅ .env file created from template${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env file and add your API keys!${NC}"
    else
        echo -e "${GREEN}✅ Using existing .env file${NC}"
    fi
else
    cp env_template.txt .env
    echo -e "${GREEN}✅ .env file created from template${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env file and add your API keys!${NC}"
fi
echo ""

# Generate SECRET_KEY if not present
if ! grep -q "SECRET_KEY=your_secret_key_here" .env 2>/dev/null; then
    echo -e "${GREEN}✅ SECRET_KEY already configured${NC}"
else
    echo "🔑 Generating SECRET_KEY..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/SECRET_KEY=your_secret_key_here/SECRET_KEY=$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/SECRET_KEY=your_secret_key_here/SECRET_KEY=$SECRET_KEY/" .env
    fi
    echo -e "${GREEN}✅ SECRET_KEY generated and added to .env${NC}"
fi
echo ""

# Set FLASK_ENV to development
if ! grep -q "^FLASK_ENV=" .env 2>/dev/null; then
    echo "FLASK_ENV=development" >> .env
    echo -e "${GREEN}✅ FLASK_ENV set to development${NC}"
fi
echo ""

# Initialize database
echo "🗃️  Initializing database..."
export FLASK_ENV=development
python3 -c "
from src.main import app
from src.app import db
with app.app_context():
    db.create_all()
    print('✅ Database tables created')
" 2>&1 | grep -v "^⚠️\|^🚀\|^📁\|^🔧\|^🔒\|^⏳\|^✅\|^❌\|^ℹ️\|^Creating\|^Starting\|^Loaded\|^Testing\|^Flask\|^Database\|^Migration" || true
echo ""

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head 2>&1 | grep -v "^INFO\|^WARN" || echo -e "${GREEN}✅ Migrations complete${NC}"
echo ""

echo "=================================================================="
echo -e "${GREEN}✅ Local development environment setup complete!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env file and add your ANTHROPIC_API_KEY"
echo "   2. (Optional) Configure other environment variables"
echo "   3. Run the application with: python run.py"
echo ""
echo "🚀 To start the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "🌐 Application will be available at: http://localhost:5001"
echo "🏥 Health check: http://localhost:5001/health"
echo ""


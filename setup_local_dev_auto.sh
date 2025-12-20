#!/bin/bash
# Non-interactive Local Development Environment Setup Script
# For AI Collab Online

set -e  # Exit on error

echo "🚀 Setting up local development environment for AI Collab Online (Auto Mode)"
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

# Remove existing venv if present
if [ -d "venv" ]; then
    echo "🗑️  Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv
echo -e "${GREEN}✅ Virtual environment created${NC}"
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
echo "📚 Installing dependencies (this may take a few minutes)..."
if [ -f "requirements.txt" ]; then
    # Create temporary requirements file with local dev adjustments
    cp requirements.txt requirements_temp.txt
    
    # Check Python version for click compatibility
    if [ "$PYTHON_MINOR" -lt 10 ]; then
        echo -e "${YELLOW}⚠️  Python 3.9 detected - adjusting click version for compatibility${NC}"
        sed -i '' 's/click==8\.2\.1/click==8.1.8/' requirements_temp.txt 2>/dev/null || sed -i 's/click==8\.2\.1/click==8.1.8/' requirements_temp.txt
    fi
    
    # Skip psycopg2-binary for local SQLite development (optional dependency)
    echo -e "${YELLOW}⚠️  Skipping psycopg2-binary (not needed for SQLite local dev)${NC}"
    sed -i '' '/^psycopg2-binary==/d' requirements_temp.txt 2>/dev/null || sed -i '/^psycopg2-binary==/d' requirements_temp.txt
    
    pip install -r requirements_temp.txt || {
        echo -e "${YELLOW}⚠️  Some dependencies failed - continuing anyway${NC}"
    }
    rm -f requirements_temp.txt
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
    echo -e "${YELLOW}⚠️  .env file already exists - backing up to .env.backup${NC}"
    cp .env .env.backup
fi

cp env_template.txt .env
echo -e "${GREEN}✅ .env file created from template${NC}"
echo ""

# Generate SECRET_KEY
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
echo ""

# Set FLASK_ENV to development
if ! grep -q "^FLASK_ENV=" .env 2>/dev/null; then
    echo "FLASK_ENV=development" >> .env
    echo -e "${GREEN}✅ FLASK_ENV set to development${NC}"
fi

# Set DATABASE_URL for local SQLite development
PROJECT_ROOT=$(pwd)
DB_PATH="$PROJECT_ROOT/instance/ai_collab.db"
if ! grep -q "^DATABASE_URL=" .env 2>/dev/null; then
    echo "DATABASE_URL=sqlite:///$DB_PATH" >> .env
    echo -e "${GREEN}✅ DATABASE_URL set to: $DB_PATH${NC}"
else
    # Update existing DATABASE_URL if it's the template value
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///$DB_PATH|" .env
    else
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///$DB_PATH|" .env
    fi
    echo -e "${GREEN}✅ DATABASE_URL updated to: $DB_PATH${NC}"
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
" 2>&1 | grep -E "(✅|❌|Error|error)" || echo -e "${GREEN}✅ Database initialization complete${NC}"
echo ""

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head 2>&1 | grep -E "(✅|❌|Error|error|head)" || echo -e "${GREEN}✅ Migrations complete${NC}"
echo ""

echo "=================================================================="
echo -e "${GREEN}✅ Local development environment setup complete!${NC}"
echo ""
echo "📝 IMPORTANT: Edit .env file and add your ANTHROPIC_API_KEY"
echo ""
echo "🚀 To start the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "🌐 Application will be available at: http://localhost:5001"
echo "🏥 Health check: http://localhost:5001/health"
echo ""


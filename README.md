# AI Collab Online

**Intelligent collaborative learning platform with adaptive AI assistance and cross-chat learning progression.**

A modern educational platform that combines structured learning environments, AI-powered assistance, and intelligent context management to create personalized learning experiences that build upon previous discussions.

[![GitHub](https://img.shields.io/badge/GitHub-Open%20Source-green?style=for-the-badge)](https://github.com/writeian/Collab_AI_Online)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.1-red?style=for-the-badge)](https://flask.palletsprojects.com/)

## 🌐 Live

- Production: https://collab.up.railway.app
- Healthcheck: https://collab.up.railway.app/health

## 🚀 Quick Start (Local)

```bash
git clone https://github.com/writeian/Collab_AI_Online.git
cd Collab_AI_Online
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp env_template.txt .env  # add your keys (see Environment Variables)
alembic upgrade head
python run.py
```

**View on GitHub**: https://github.com/writeian/Collab_AI_Online

---

## 📋 Branches

- Production (Railway tracked branch): `feature/railway-deployment`
- Development: `dev`

### How to deploy to Railway
- Ensure you are on the tracked branch:
  ```bash
  git checkout feature/railway-deployment && git pull --ff-only
  ```
- Commit your changes and push to trigger a deploy:
  ```bash
  git commit -m "deploy: landing updates" # or --allow-empty to force
  git push origin feature/railway-deployment
  ```
- After deploy, hard refresh the browser to bypass cached assets.

---

## 🎯 What It Does

AI Collab Online is an **intelligent learning platform** that creates adaptive, contextual learning experiences through AI-powered assistance and cross-chat learning progression.

### 🏔️ **Mountain Learning Journey**
- **Visual learning progression** with beautiful mountain climbing interface and curvy SVG trails
- **Step-by-step navigation** with markers, progress tracking, and deep linking to specific learning stages
- **Social learning indicators** showing team member participation with avatar groups and activity badges
- **Responsive design** with mobile-friendly collapsible details and accessibility features

### 🧠 **Intelligent Learning Progression**
- **Automatic note generation** from completed discussions (5+ message milestones)
- **Cross-chat learning context** that builds on previous insights across multiple conversations
- **AI-generated welcome messages** that integrate room goals, learning objectives, and previous discussion context
- **Progressive learning paths** that remember and build upon entire learning journeys

### **For Educators:**
- **Create learning environments** with pre-built templates (Study Groups, Academic Essays, Writing Workshops)
- **Guide students** through structured 10-step writing processes
- **Track progress** with comprehensive analytics and achievement systems
- **Customize AI prompts** for different learning stages and subjects

### **For Writing Teams:**
- **Collaborate in dedicated rooms** with real-time messaging and AI assistance
- **Use specialized templates** for different project types (Business Hub, Creative Studio)
- **Organize goals** with collapsible categories to reduce cognitive overload
- **Toggle AI responses** on/off per conversation for flexible collaboration

### **For Content Creators:**
- **Import Google Docs** for AI analysis and feedback
- **Use contextual AI** that adapts responses based on your current writing stage
- **Manage multiple projects** with organized room-based workspaces
- **Get instant feedback** on writing quality and structure

### **Key Benefits:**
- 🧠 **Intelligent Learning Progression** - AI remembers and builds on previous discussions across multiple chats
- 📝 **Automatic Note Generation** - Creates contextual summaries at 5-message milestones for seamless learning continuity
- 🎯 **Adaptive Welcome Messages** - AI-generated introductions that integrate room goals, learning objectives, and previous insights
- 🚀 **Get started in minutes** with 7 pre-built learning templates
- 🤖 **Context-aware AI** - Responses adapt to your learning stage and previous discussions
- 👥 **Built for collaboration** - Real-time messaging with intelligent learning progression
- 📱 **Works everywhere** - Mobile-responsive design with modern glass morphism UI

---

## ✨ Core Features

### 🧠 **Intelligent Learning Progression**
- **Automatic Note Generation**: Creates contextual summaries at 5, 10, 15... message milestones
- **Cross-Chat Learning Context**: New chats automatically reference insights from previous discussions
- **AI-Generated Welcome Messages**: Contextual introductions that integrate room goals + learning objectives + previous work
- **Progressive Learning Paths**: Flexible, non-linear progression that remembers entire learning journey
- **Learning Context Management**: Dedicated module for note storage, retrieval, and context enhancement
- **Pin-Seeded Chats**: Create focused conversations from shared pins with 9 synthesis options (explore, study, essay, presentation, etc.) and pin-aware AI responses

### 📝 **Document Generation & Export**
- **Chat-to-Document Export**: Transform discussions into structured notes, outlines, or raw transcripts
- **Multiple Formats**: Export as .txt or .docx files
- **Progressive Messaging**: Export options unlock based on conversation depth
- **Sidebar Integration**: Convenient dropdown interface for document generation

### 🎯 **Template System & Room Management**
- **7 Pre-built templates** for different learning contexts (Study Group, Learning Lab, Academic Essay, etc.)
- **Custom room creation** with user-defined goals and flexible learning progression
- **Unified create/edit interface** with goals → proposal → refine → create workflow
- **Mobile-responsive design** with modern glass morphism UI

### 🤖 **AI-Powered Collaboration**
- **Adaptive archetype prompts** - Cognitive style matching (divergent, analytical, technical, etc.) for mode-appropriate AI expression
- **Anthropic Claude integration** with contextual, learning-aware responses
- **Learning step progression** with mode-specific AI guidance
- **AI response toggle** with persistent per-chat preferences
- **Google Docs integration** for document analysis and import
- **Pin-aware AI responses** - Pin-seeded chats maintain full pin context throughout the conversation

### 🎓 **Educational Tools**
- **In-chat tool launcher**: Quiz, Flashcards, Mind Map, and Narrative are available directly from the chat composer `+` menu
- **Context-aware generation**: Tools can use `chat`, `library`, or `both` context modes (with room-level access controls)

#### ✅ **Quiz Tool**
- **Configurable assessments**: Generate quizzes with 1-20 questions
- **Difficulty controls**: `easy`, `average`, `hard`, or `mixed`
- **Auto-grading + explanations**: Instant score and per-question rationale
- **Chat integration**: Send quiz results back to the conversation for discussion

#### 🗂️ **Flashcards Tool**
- **Two study modes**: `grid` and `single card`
- **Grid layouts**: `1x2`, `2x2`, `2x3`, `3x3`
- **Generate-more flow**: Produces additional cards with duplicate-avoidance logic
- **Library-backed study**: Supports document-based flashcard generation

#### 🧠 **Mind Map Tool**
- **Hierarchical concept maps**: Generates root, branches, and sub-branches from learning context
- **Size controls**: `small`, `medium`, `large`
- **Node explanations**: Each node includes concise explanatory content
- **Export + share**: Export maps and send outputs back into chat

#### 📖 **Narrative Tool**
- **Narrative modes**: `linear` and `interactive`
- **Interactive complexity levels**: `explanation`, `simulation`, `challenge`
- **Reflection workflow**: Built-in reflection and formative feedback stages
- **Chat handoff**: Send completed narrative outcomes into the room conversation

### 📊 **Analytics & Administration**
- **Learning progression tracking** with automatic note generation analytics
- **Comprehensive user analytics** with CSV export capabilities
- **System instructions management** for custom AI prompts and learning modes
- **Member management** with role-based permissions
- **Achievement system** with gamification elements

### 💬 **Enhanced Chat Experience**
- **Focus mode toggle** to maximize learning space
- **Rubric-aware progress assessment** with structured recommendations
- **Liquid glass UI** with iOS 18-inspired translucent effects and multi-layered shadows
- **Modular component architecture** with 70% template size reduction
- **External JavaScript files** with data attribute integration
- **Auto-dismiss flash messages** with close buttons
- **Mobile-optimized sidebar** with responsive design

### 🏧 **Architecture & Performance**
- **Modular Flask blueprint architecture** with comprehensive type coverage
- **SQLAlchemy 2.0** with Alembic migrations and manual fallbacks
- **Template modularization** with reusable components
- **External asset management** with cache-busting
- **Production-ready** with Railway and Digital Ocean deployment
- **Comprehensive error handling** and graceful fallbacks

---

## 🆕 **Recent Major Updates**

### 📌 **Pin-Seeded Chats (v3.2)** - *December 2025*
- **Shared pins as chat seeds**: Create focused conversations from ≥3 shared pins
- **9 synthesis options**: Explore, Study, Research Essay, Presentation, Learning Exercise, Startup, Artistic, Social Impact, Analyze
- **Pin-aware AI responses**: System prompts include full pin context for contextual conversations
- **Pin snapshot persistence**: `PinChatMetadata` stores pin content at creation time (immune to source changes)
- **Room view integration**: "Pin-based Chats" section in mountain view and pin badges on chat cards
- **Chat sidebar grouping**: Pin chats grouped under "Pin-based Chats" divider with pin count badges
- **Option picker modal**: Glass-effect modal with icons, descriptions, and loading states
- **Prompt length monitoring**: 15K char limit with truncation and logging for large pin sets

### 🏔️ **Mountain Learning Journey (v3.0)** - *September 2025*
- **Visual learning progression** with beautiful mountain climbing interface as the default room experience
- **Curvy SVG trail system** connecting learning steps with dynamic progress visualization
- **Social learning features** with avatar groups, participant tracking, and activity indicators
- **Responsive design** with mobile-friendly collapsible details and accessibility features
- **Deep linking support** to specific learning steps with auto-expand functionality
- **Room statistics integration** with collapsible team stats and progress metrics

### 🎚️ **AI Critique Control System (v3.1)** - *September 2025*
- **5-level feedback control** from Very Supportive to Very Critical
- **Real-time AI tone adaptation** based on user preference
- **Session-based storage** for personalized learning experiences
- **Contextual prompt enhancement** without database complexity

### 🧠 **Learning Progression System (v2.0)**
- **Automatic note generation** at 5-message milestones with iterative refinement
- **Cross-chat learning context** that builds comprehensive learning history
- **AI-generated welcome messages** integrating room goals + learning objectives + previous insights
- **Flexible learning paths** supporting non-linear, skippable, and reversible progression

### 📝 **Document Generation & Export**
- **Chat-to-document transformation** with notes, outlines, and raw export options
- **Progressive unlock system** based on conversation depth
- **Multiple format support** (.txt, .docx) with professional formatting
- **Sidebar integration** with intuitive dropdown interface

### 🔗 **Enhanced User Experience (v3.1)** - *September 2025*
- **Continue message functionality** for expanding AI responses inline
- **Improved button accessibility** with high-contrast design
- **Password visibility toggle** with intuitive icon states
- **Mobile-optimized interactions** with proper focus management

### 🎨 **UI/UX Modernization**
- **70% template size reduction** through JavaScript extraction and component modularization
- **Learning Green color scheme** with industry-standard design tokens
- **Liquid glass chat input** with iOS 18-inspired translucent gradients and blur effects
- **Auto-dismiss flash messages** with close buttons and smooth animations

### 🏧 **Architecture Improvements**
- **Modular template components** preventing corruption and improving maintainability
- **External JavaScript files** with data attribute integration
- **Enhanced error handling** with comprehensive fallback systems
- **Database migration fallbacks** for robust deployment reliability

---

## 🛠️ Technology Stack

### Backend
- **Flask 3.1.1** with modular blueprint architecture
- **SQLAlchemy 2.0.41** with Alembic migrations
- **SQLite** (development) / **PostgreSQL** (production)
- **Custom session-based authentication** with Google OAuth support

### Frontend
- **Tailwind CSS** with responsive design
- **Jinja2 templates** with modern component structure
- **Vanilla JavaScript** with ES6+ features
- **Mobile-optimized** with progressive enhancement

### AI Services
- **Anthropic Claude API** for intelligent, context-aware responses
- **Learning progression AI** that generates notes and contextual welcome messages
- **Cross-chat context integration** that maintains learning continuity
- **Adaptive learning modes** based on educational stages and previous discussions
- **Error handling** with graceful fallbacks
  - Provider failover via `AI_FAILOVER_ORDER` (e.g., `anthropic,openai,templates`)
  - Model overrides: `ANTHROPIC_MODEL` (e.g., `claude-3-5-sonnet-20241022`), `OPENAI_MODEL` (e.g., `gpt-4o-mini`)
- **Document generation AI** for creating structured notes and outlines from conversations

### Deployment
- **Railway** with automatic deployments
- **Digital Ocean** with Nginx + Gunicorn
- **Built-in health checks** and monitoring
- **SSL certificates** and security headers

---

## ⚙️ Environment Variables

Create `.env` (or set Railway Variables):

Required
```
SECRET_KEY=your_secret
FLASK_ENV=development
DATABASE_URL=postgresql+psycopg2://...  # or omit to use SQLite locally
ANTHROPIC_API_KEY=sk-ant-...
```

Email (SendGrid)
```
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.***
EMAIL_FROM=your_verified_sender@example.com
EMAIL_FROM_NAME=AI Collab Online
EMAIL_REPLY_TO=support@example.com
```

Admin allowlist
```
ADMIN_EMAILS=you@example.com,other@example.org
```

Refinement & AI
```
# Enable new refinement flow
REFINE_V2_ENABLED=true
# Adaptive AI expression with cognitive archetypes (default: true)
ENABLE_ARCHETYPE_PROMPTS=true
# Provider order and model overrides (optional)
AI_FAILOVER_ORDER=anthropic,openai,templates
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
OPENAI_MODEL=gpt-4o-mini
# Response configuration (defaults: 400 tokens, 8 turns)
AI_MAX_TOKENS=400
AI_MAX_HISTORY=8
# Per-mode overrides (optional): AI_MAX_TOKENS_DRAFT=500, AI_MAX_TOKENS_POLISH=350
```

Limits
```
# Per-room chat cap (default 25)
ROOM_MAX_CHATS=25
# Minimum shared pins required for pin-seeded chats (default 3)
# PIN_CHAT_MIN_PINS=3  # (hardcoded, configurable in future)
```

### Prerequisites
- Python 3.8+
- Anthropic API key
- Google Cloud Project (for Google Docs integration)

### Installation
```bash
# Clone the repository
git clone https://github.com/writeian/Collab_AI_Online.git
cd AI_Collab_Online

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your Anthropic API key

# Run the application
python run.py
```

### Environment Variables
Create a `.env` file in the root directory:

```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database (optional - defaults to SQLite)
DATABASE_URL=sqlite:///instance/ai_collab.db

# Flask settings
FLASK_ENV=development
SECRET_KEY=your_secret_key_here

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

---

## 🔧 Development

### Code Quality
```bash
# Run all tests
python -m pytest

# Type checking with mypy
python -m mypy src/app/ --ignore-missing-imports

# Linting with flake8
python -m flake8 src/ --max-line-length=120
```

### macOS Case Sensitivity Note
**For macOS developers**: Due to the default case-insensitive filesystem, the `templates/` directory may appear in your IDE or terminal as both `templates/` and `Templates/`. These are the same directory. Always reference `templates/` (lowercase) in code and documentation, as that's what Git tracks and what production uses.

### Project Structure
```
AI_Collab_Online/
├── src/                    # Main application
│   ├── app/               # Flask blueprints
│   ├── models/            # Database models
│   ├── utils/             # Utilities & AI integration
│   └── config/            # Configuration
├── templates/             # HTML templates
├── tests/                 # Test suite
├── scripts/               # Development utilities
└── deployment/            # Deployment configs
```

**Full structure**: [See detailed breakdown](#detailed-project-structure)

---

## 🚀 Deployment

### Railway Deployment
1. **Connect Repository**: Link this GitHub repo to your Railway project
2. **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` (already in `railway.toml`)
3. **Healthcheck**: `/health` (already in `railway.toml`)
4. **Environment Variables**: Set `SECRET_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `REFINE_V2_ENABLED`, `AI_FAILOVER_ORDER`, `ANTHROPIC_MODEL/OPENAI_MODEL` as needed
5. **Database**: Use PostgreSQL for production. Run migrations: `alembic upgrade head`
6. **Endpoint Name**: Set a friendly slug in Service → Networking (globally unique)
7. **Deploy**: Deploy from the UI or by pushing to your deployment branch

**📖 [Complete Railway Deployment Guide](RAILWAY_DEPLOYMENT.md)**

### Digital Ocean Deployment
```bash
# Run automated deployment script
bash deployment/deploy.sh
```

### Manual Deployment
```bash
# Install production dependencies
pip install -r requirements_production.txt

# Set production environment variables
export FLASK_ENV=production
export DATABASE_URL=your_postgresql_url

# Run migrations
alembic upgrade head

# Start production server
gunicorn src.wsgi:app
```

### Custom Domains (Railway)
- Recommended: add a subdomain like `app.yourdomain.com`
- Create a CNAME to your `*.up.railway.app` endpoint, verify in Railway Networking
- If verification fails, ensure DNS is set to DNS-only during initial verification and try again

---

## 🧪 Trial Mode (Optional/Future)

Offer limited, server-enforced guest trials (e.g., 1 room, 1 chat, 6 messages) without registration, with a clean upgrade path to a full account.

- Design doc: `docs/trial_sessions_option_2.md`
- Highlights: DB-backed counters, expiry/cleanup, adoption on signup, and abuse safeguards

---

## 🛟 Troubleshooting

- Anthropic 529 (service overloaded):
  - The app retries briefly and falls back to goal‑aware templates. Check Anthropic status and org limits.
  - Ensure `ANTHROPIC_API_KEY` is set on the correct service and org.

- Endpoint slug errors (Railway): endpoint names are globally unique. Try a different slug (Service → Networking → Endpoint name)
- Custom domains: add CNAME to your service’s `*.up.railway.app`; if using Cloudflare, set DNS-only during verification
- Static asset 404s on Linux: ensure case-sensitive paths (e.g., `Static/` vs `static/`)
- JSON POSTs and CSRF: app includes a global fetch wrapper that sends `X-CSRFToken` automatically

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for detailed information and check our [GitHub Issues](https://github.com/writeian/Collab_AI_Online/issues) for current needs.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Code Style & Quality
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for all functions
- **Include type hints for all new functions**
- Run mypy for type checking: `python -m mypy src/ --ignore-missing-imports`
- Run flake8 for linting: `python -m flake8 src/ --max-line-length=120`

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/writeian/Collab_AI_Online/issues)
- **Discussions**: [GitHub Discussions](https://github.com/writeian/Collab_AI_Online/discussions)

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Anthropic** for providing the Claude API
- **Flask** community for the excellent web framework
- **Tailwind CSS** for the beautiful styling system
- **All contributors** who have helped improve this platform

---

**Made with ❤️ for educators and writers everywhere**

---

## 📁 Project Structure (high level)

```
Collab_AI_Online/
├── src/                          # Main application source
│   ├── app/                      # Flask blueprints
│   │   ├── room/                # Room routes (create/edit flow, services, utils)
│   │   ├── chat.py              # Chat functionality with learning progression
│   │   ├── documents.py         # Document generation and export
│   │   ├── auth.py              # Authentication
│   │   ├── admin.py             # Admin dashboard & reports
│   │   ├── analytics.py         # Analytics endpoints
│   │   ├── achievements.py      # Gamification
│   │   └── access_control.py    # Permission & guards
│   ├── models/                   # Database models
│   │   ├── learning.py          # Learning progression models (ChatNotes)
│   │   ├── chat.py              # Chat and Message models
│   │   └── room.py              # Room and membership models
│   ├── utils/                    # Utility functions
│   │   ├── learning/            # Learning progression utilities
│   │   │   ├── context_manager.py   # Note generation and retrieval
│   │   │   └── triggers.py          # Auto-generation triggers
│   │   ├── openai_utils.py      # AI integration and welcome generation
│   │   └── progression.py       # Learning progression logic
│   └── config/                   # Configuration
├── templates/                    # HTML templates
│   ├── components/              # Modular template components
│   │   └── chat/                # Chat-specific components
│   └── room/                     # Room templates and wizards
├── static/                       # CSS, JavaScript, images
│   ├── css/                     # Modular CSS with design tokens
│   └── js/                      # External JavaScript files
├── tests/                        # Test suite
├── migrations/                   # Database migrations
├── docs/                         # Documentation and lessons learned
└── requirements.txt              # Python dependencies
```

**Type Coverage**: 85% of functions have comprehensive type hints for better code quality and IDE support.
 # Force redeploy to fix import issue - Wed Sep 17 05:56:01 PDT 2025

---

## Recent Updates (Oct-Nov 2025)

### Sidebar Overhaul (Phases 1-3)
- **Collapsible sections**: Tools, Participants, Other Chats with smart defaults
- **Unified tool cards**: Learning Progress, Tone & Critique, Document Generation
- **Dynamic dashboard**: Tools summary shows current tone and progress status at a glance
- **Professional polish**: Lucide icons, 8pt spacing rhythm, accessible ARIA patterns
- **Mobile optimized**: Scrollable drawer, 44px tap targets, responsive spacing

### Performance & UX
- **Adaptive polling**: 5s when active, 90s when idle; auto-wake on new messages
- **iPhone scroll fixed**: Native iOS behavior, no scroll traps
- **External JS architecture**: -815 lines of inline code removed
- **Clean console**: All accessibility and integration issues resolved

See `docs/SESSION-SUMMARY-2025-10-28.md` and `docs/PHASE3-tool-header-alignment.md` for complete details.

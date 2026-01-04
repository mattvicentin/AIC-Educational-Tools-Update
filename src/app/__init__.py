"""
Application package for AI Collab Online
Contains core Flask application and blueprints
"""

from flask import Flask, request
import os as _os
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import FlaskForm
import re

# Create SQLAlchemy instance for app package
db = SQLAlchemy()
# Create CSRF protection instance
csrf = CSRFProtect()
# Custom key function that exempts static files
def rate_limit_key_func():
    """Rate limit key function that exempts static files."""
    from flask import request
    # Exempt static files from rate limiting
    if request.endpoint == 'static' or request.path.startswith('/static/') or request.path.startswith('/assets/'):
        return None  # None key means no rate limiting
    return get_remote_address()

# Create rate limiter instance
limiter = Limiter(
    key_func=rate_limit_key_func,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=None  # Will be configured per environment
)


def markdown_filter(text):
    """Convert basic markdown to HTML."""
    if not text:
        return text
    
    # Convert line breaks to <br> tags
    text = text.replace('\n', '<br>')
    
    # Convert **text** to <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert *text* to <em>text</em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    return text


def create_app(config_name=None):
    """Application factory pattern for Flask app creation."""
    from src.config.settings import config

    # Note: Use lowercase `templates/` as the single source of truth.
    _here = _os.path.dirname(__file__)
    _root = _os.path.abspath(_os.path.join(_here, '..', '..'))
    _static_abs = _os.path.join(_here, 'static')
    _templates_abs = _os.path.join(_root, 'templates')
    if not _os.path.isdir(_templates_abs):
        raise RuntimeError(f"templates/ folder not found at {_templates_abs}; ensure lowercase templates are deployed")

    app = Flask(
        __name__,
        static_folder=_static_abs,
        static_url_path="/static",
        template_folder=_templates_abs,
    )

    # Get configuration
    if config_name is None:
        import os

        config_name = os.getenv("FLASK_ENV", "development")

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize database
    db.init_app(app)

    # Eagerly import models and ensure tables exist
    from src import models as _models
    with app.app_context():
        try:
            db.create_all()
            
            # Manually create document tables if they don't exist (SQLite compatibility)
            try:
                from src.models import Document, DocumentChunk
                Document.query.first()  # Test if table exists
            except Exception:
                # Table doesn't exist, create it manually
                try:
                    is_postgres = 'postgresql' in str(db.engine.url)
                    with db.engine.connect() as conn:
                        # Create document table
                        if is_postgres:
                            conn.execute(db.text("""
                                CREATE TABLE IF NOT EXISTS document (
                                    id SERIAL PRIMARY KEY,
                                    file_id VARCHAR(255) NOT NULL,
                                    name VARCHAR(500) NOT NULL,
                                    full_text TEXT,
                                    file_size INTEGER NOT NULL DEFAULT 0,
                                    room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE CASCADE,
                                    uploaded_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                                    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    summary TEXT
                                )
                            """))
                        else:
                            conn.execute(db.text("""
                                CREATE TABLE IF NOT EXISTS document (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    file_id VARCHAR(255) NOT NULL,
                                    name VARCHAR(500) NOT NULL,
                                    full_text TEXT,
                                    file_size INTEGER NOT NULL DEFAULT 0,
                                    room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE CASCADE,
                                    uploaded_by INTEGER REFERENCES user(id) ON DELETE SET NULL,
                                    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    summary TEXT
                                )
                            """))
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_document_file_id ON document(file_id)"))
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_document_room_id ON document(room_id)"))
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_document_uploaded_at ON document(uploaded_at)"))
                        conn.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_document_room_file_unique ON document(room_id, file_id)"))
                        conn.commit()
                    
                    # Create document_chunk table
                    try:
                        DocumentChunk.query.first()
                    except Exception:
                        with db.engine.connect() as conn:
                            if is_postgres:
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS document_chunk (
                                        id SERIAL PRIMARY KEY,
                                        document_id INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
                                        chunk_index INTEGER NOT NULL,
                                        chunk_text TEXT NOT NULL,
                                        start_char INTEGER,
                                        end_char INTEGER,
                                        token_count INTEGER,
                                        search_vector TSVECTOR,
                                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        UNIQUE(document_id, chunk_index)
                                    )
                                """))
                                try:
                                    conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_chunk_search_vector ON document_chunk USING gin(search_vector)"))
                                except:
                                    pass
                            else:
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS document_chunk (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        document_id INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
                                        chunk_index INTEGER NOT NULL,
                                        chunk_text TEXT NOT NULL,
                                        start_char INTEGER,
                                        end_char INTEGER,
                                        token_count INTEGER,
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        UNIQUE(document_id, chunk_index)
                                    )
                                """))
                            conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_document_chunk_document_id ON document_chunk(document_id)"))
                            conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_document_chunk_doc_created_at ON document_chunk(document_id, created_at)"))
                            conn.commit()
                except Exception as doc_error:
                    app.logger.warning(f"Could not create document tables: {doc_error}")
            
            app.config["DB_INIT_STATUS"] = "success"
            app.logger.info("✅ Database tables initialized successfully")
        except Exception as e:
            app.logger.error(f"❌ Database initialization failed: {e}")
            app.config["DB_INIT_ERROR"] = str(e)
            # Don't crash - let app continue to start so /health can report the error
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Disable CSRF for development
    if app.debug:
        app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize rate limiting with environment-specific storage
    if app.config.get('FLASK_ENV') == 'production':
        # Production: Use Redis if available, otherwise database
        redis_url = app.config.get('REDIS_URL')
        if redis_url:
            limiter.init_app(app, storage_uri=redis_url)
        else:
            # Fallback to database storage
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
            if db_url and 'postgresql' in db_url:
                # Use PostgreSQL for rate limiting
                limiter.init_app(app, storage_uri=f"{db_url}?sslmode=disable")
            else:
                # Use SQLite for rate limiting
                limiter.init_app(app, storage_uri="sqlite:///instance/rate_limits.db")
    else:
        # Development: Use in-memory storage (faster for development)
        limiter.init_app(app)
    
    
    # Add security headers
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # CSP configuration that allows CDN resources

        # Set CSRF cookie for JS fetch
        try:
            token = generate_csrf()
            response.set_cookie('csrf_token', token, secure=not app.debug, httponly=False, samesite='Lax', path='/')
        except Exception:
            pass

        # CSP configuration that allows CDN resources
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; img-src 'self' data:; connect-src 'self' https://cdn.tailwindcss.com https://unpkg.com;"
        if not app.config.get('TESTING', False) and not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Register custom template filters
    app.jinja_env.filters['markdown'] = markdown_filter

    # Expose is_admin to templates
    try:
        from src.app.access_control import get_current_user, is_admin as _is_admin
        from src.app.room.utils.room_utils import get_invitation_count as _get_inv_count

        @app.context_processor
        def inject_globals():
            user = get_current_user()
            try:
                inv_count = _get_inv_count(user) if user else 0
            except Exception:
                inv_count = 0
            return {
                'is_admin': _is_admin(user) if user else False,
                'user': user,
                'invitation_count': inv_count,
            }
    except Exception:
        # If anything fails, still return a minimal context processor
        @app.context_processor
        def inject_minimal():
            return {'is_admin': False, 'user': None, 'invitation_count': 0}

    # Debug: Log static/template paths and CSS existence at startup
    try:
        import os as __os
        css_paths = [
            __os.path.join(app.static_folder or '', 'css', 'globals.css'),
            __os.path.join(app.static_folder or '', 'css', 'components.css'),
            __os.path.join(app.static_folder or '', 'css', 'style.css'),
        ]
        print(f"[static] static_folder={app.static_folder}")
        print(f"[static] template_folder={app.template_folder}")
        for p in css_paths:
            print(f"[static] exists({p})={__os.path.exists(p)}")
    except Exception as _e:
        print(f"[static] startup static check failed: {_e}")

    # Register blueprints
    from src.app.auth import auth
    from src.app.chat import chat
    from src.app.room import room
    from src.app.dashboard import dashboard
    from src.app.admin import admin
    from src.app.admin_password_reset import admin_reset_bp
    from src.app.google_auth import google_auth
    from src.app.analytics import analytics
    from src.app.documents import documents
    
    # Dev API (Card View experiment)
    from src.app.api.card_view import card_view_api
    
    # Card Comments API (for Card View)
    from src.app.api.card_comments import card_comments_api
    
    # V2 Enhanced Room Dashboard (Clean Implementation)
    from src.app.room_v2 import room_v2
    
    # Library Tool integration (document upload and search)
    from src.app.library import library
    
    # Quiz Tool integration
    from src.app.quiz import quiz
    
    # Flashcards Tool integration
    from src.app.flashcards import flashcards
    
    # Mind Map Tool integration
    from src.app.mindmap import mindmap

    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(chat, url_prefix="/chat")
    app.register_blueprint(room, url_prefix="/room")
    app.register_blueprint(dashboard, url_prefix="/dashboard")
    app.register_blueprint(admin, url_prefix="")
    app.register_blueprint(admin_reset_bp, url_prefix="")
    app.register_blueprint(google_auth, url_prefix="/auth/google")
    
    # V2 Enhanced Dashboard (Independent)
    app.register_blueprint(room_v2, url_prefix="/room/v2")
    app.register_blueprint(analytics, url_prefix="/analytics")
    app.register_blueprint(documents, url_prefix="/documents")
    
    # Library Tool endpoints
    app.register_blueprint(library, url_prefix="/api/library")
    
    # Quiz Tool endpoints
    app.register_blueprint(quiz, url_prefix="/api/quiz")
    
    # Flashcards Tool endpoints
    app.register_blueprint(flashcards, url_prefix="/api/flashcards")
    
    # Mind Map Tool endpoints
    app.register_blueprint(mindmap, url_prefix="/api/mindmap")
    
    # Dev API (experimental endpoints)
    app.register_blueprint(card_view_api)  # url_prefix set in blueprint
    
    # Card Comments API (no prefix - routes defined with full paths)
    app.register_blueprint(card_comments_api)

    # Diagnostics: template folder + which room template is found
    @app.route("/__tpl")
    def __tpl():
        import os as __os
        info = {
            "template_folder": app.template_folder,
            "cwd": __os.getcwd(),
            "exists_lowercase": __os.path.exists(__os.path.join(app.template_folder or '', 'room', 'view.html')),
            "exists_capitalized": __os.path.exists(__os.path.abspath(__os.path.join(__os.getcwd(), 'Templates', 'room', 'view.html'))),
        }
        return info

    # Diagnostics: inspect base.html to see linked CSS versions
    @app.route("/__tpl_base")
    def __tpl_base():
        import os as __os
        import re as __re
        base_path = __os.path.join(app.template_folder or '', 'base.html')
        result = {
            "template_folder": app.template_folder,
            "base_path": base_path,
            "exists": __os.path.exists(base_path),
            "globals_v": None,
            "components_v": None,
            "hrefs": [],
        }
        try:
            if __os.path.exists(base_path):
                with open(base_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                m1 = __re.search(r"globals\.css\?v=([\d\.]+)", content)
                m2 = __re.search(r"components\.css\?v=([\d\.]+)", content)
                result["globals_v"] = m1.group(1) if m1 else None
                result["components_v"] = m2.group(1) if m2 else None
                # collect href lines
                for line in content.splitlines():
                    if 'globals.css' in line or 'components.css' in line:
                        result["hrefs"].append(line.strip())
        except Exception as e:
            result["error"] = str(e)
        return result

    # Add main routes
    @app.route("/")
    def index():
        """Root endpoint - redirect to rooms page."""
        from flask import redirect, url_for

        return redirect(url_for("room.room_crud.index"))

    @app.route("/about")
    def about():
        """About page."""
        from flask import render_template

        return render_template("about.html")

    @app.route("/landing")
    def landing():
        """Landing page."""
        from flask import render_template

        return render_template("landing.html")
    
    @app.route("/metrics")
    def metrics():
        """Application metrics endpoint for monitoring."""
        from flask import jsonify
        from datetime import datetime, timedelta
        
        try:
            # Import models only when needed to avoid conflicts
            from src.models import User, Room, Chat, Message
            
            # Basic metrics
            total_users = User.query.count()
            total_rooms = Room.query.count()
            total_chats = Chat.query.count()
            total_messages = Message.query.count()
            
            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_users = User.query.filter(User.created_at >= yesterday).count()
            recent_rooms = Room.query.filter(Room.created_at >= yesterday).count()
            recent_messages = Message.query.filter(Message.timestamp >= yesterday).count()
            
            return jsonify({
                "status": "healthy",
                "metrics": {
                    "total_users": total_users,
                    "total_rooms": total_rooms,
                    "total_chats": total_chats,
                    "total_messages": total_messages,
                    "recent_activity": {
                        "new_users_24h": recent_users,
                        "new_rooms_24h": recent_rooms,
                        "new_messages_24h": recent_messages
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500

    # Lightweight endpoint to verify static file availability in prod
    @app.route("/__static_check")
    def __static_check():
        import os as __os
        try:
            base = app.static_folder or ''
            files = {
                'static_folder': base,
                'globals_css': __os.path.join(base, 'css', 'globals.css'),
                'components_css': __os.path.join(base, 'css', 'components.css'),
                'style_css': __os.path.join(base, 'css', 'style.css'),
            }
            exists = {k + '_exists': __os.path.exists(v) if k != 'static_folder' else True for k, v in files.items()}
            return {
                'ok': True,
                **files,
                **exists
            }
        except Exception as e:
            return { 'ok': False, 'error': str(e) }, 500

    # Targeted fallback route to serve CSS from the configured Static/css directory
    # This guards against case/path mismatches causing 404s on /static/css/* in production
    @app.route("/static/css/<path:filename>")
    @limiter.exempt
    def __static_css_fallback(filename: str):
        try:
            from flask import send_from_directory
            import os as __os
            _abs_css = __os.path.join(app.static_folder or '', 'css')
            return send_from_directory(_abs_css, filename, mimetype='text/css')
        except Exception as e:
            return (f"CSS not found: {filename}", 404)

    # Non-conflicting assets route we fully control (bypasses Flask's built-in static rule)
    @app.route("/assets/css/<path:filename>")
    @limiter.exempt
    def assets_css(filename: str):
        try:
            from flask import send_from_directory
            import os as __os
            _abs_css = __os.path.join(app.static_folder or '', 'css')
            return send_from_directory(_abs_css, filename, mimetype='text/css')
        except Exception:
            return ("Not found", 404)

    # Serve legacy assets from capitalized 'Static/' folder (images/css/js for landing page)
    try:
        import os as __os
        # Detect project root Static directory robustly
        _candidate_static_dirs = [
            __os.path.abspath(__os.path.join(_here, '..', '..', '..', 'Static')),
            __os.path.abspath(__os.path.join(_here, '..', '..', 'Static')),
            __os.path.abspath(__os.path.join(_root, '..', 'Static')),
            __os.path.abspath(__os.path.join(_root, 'Static')),
            __os.path.abspath(__os.path.join(__os.getcwd(), 'Static')),
            '/app/Static',
        ]
        _root_static_abs = None
        for _cand in _candidate_static_dirs:
            if __os.path.isdir(_cand):
                _root_static_abs = _cand
                break
        if not _root_static_abs:
            # Default guess; will 404 but diagnostics will show base
            _root_static_abs = __os.path.abspath(__os.path.join(_here, '..', '..', '..', 'Static'))
        print(f"[landing-assets] resolved base='{_root_static_abs}' candidates={_candidate_static_dirs}")

        @app.route('/landing-assets/<path:filename>')
        def landing_assets(filename: str):
            from flask import send_file
            import os as __os
            # Explicit MIME types for stricter browsers
            _mimetype = None
            if filename.endswith('.css'):
                _mimetype = 'text/css'
            elif filename.endswith('.js'):
                _mimetype = 'application/javascript'
            elif filename.lower().endswith('.png'):
                _mimetype = 'image/png'

            # Special-case CSS/JS to serve from Flask static if present
            try:
                _static_base = app.static_folder or ''
                if filename in ('landing.css', 'landing.js'):
                    _static_path = __os.path.join(_static_base, filename)
                    if __os.path.exists(_static_path):
                        print(f"[landing-assets] special-case serving '{filename}' from static '{_static_path}'")
                        return send_file(_static_path, mimetype=_mimetype)
            except Exception as _e:
                print(f"[landing-assets] special-case error: {_e}")

            _candidate_dirs = [_root_static_abs]
            for _base in _candidate_dirs:
                _abs_path = __os.path.join(_base, filename)
                if __os.path.exists(_abs_path):
                    print(f"[landing-assets] serving '{filename}' from '{_abs_path}' mimetype={_mimetype}")
                    try:
                        return send_file(_abs_path, mimetype=_mimetype)
                    except Exception as _e:
                        print(f"[landing-assets] send_file error for {_abs_path}: {_e}")
                        break
            # Not found: include diagnostics
            try:
                _base = _root_static_abs
                _listing = []
                if __os.path.isdir(_base):
                    _listing = sorted(__os.listdir(_base))
                print(f"[landing-assets] NOT FOUND filename='{filename}' base='{_base}' items={_listing[:20]}")
            except Exception as _e:
                print(f"[landing-assets] listing error: {_e}")
            return ("Not found", 404)

        @app.route('/__landing_assets_check')
        def __landing_assets_check():
            import os as __os
            try:
                _base = _root_static_abs
                _ok = __os.path.isdir(_base)
                _landing_css = __os.path.join(_base, 'landing.css')
                _landing_js = __os.path.join(_base, 'landing.js')
                _img1 = __os.path.join(_base, 'Landing page image no text 1.png')
                _img2 = __os.path.join(_base, 'Landing page image no text 2.png')
                _img3 = __os.path.join(_base, 'Landing page image no text 3.png')
                _img4 = __os.path.join(_base, 'Landing page image no text 4.png')
                _img5 = __os.path.join(_base, 'Landing page image no text 5.png')
                _img6 = __os.path.join(_base, 'Landing page image no text 6.png')
                _listing = []
                try:
                    _listing = sorted(__os.listdir(_base)) if _ok else []
                except Exception:
                    _listing = []
                return {
                    'base': _base,
                    'base_exists': _ok,
                    'cwd': __os.getcwd(),
                    'here': _here,
                    'root': _root,
                    'landing_css_exists': __os.path.exists(_landing_css),
                    'landing_js_exists': __os.path.exists(_landing_js),
                    'img1_exists': __os.path.exists(_img1),
                    'img2_exists': __os.path.exists(_img2),
                    'img3_exists': __os.path.exists(_img3),
                    'img4_exists': __os.path.exists(_img4),
                    'img5_exists': __os.path.exists(_img5),
                    'img6_exists': __os.path.exists(_img6),
                    'listing_sample': _listing[:20],
                }
            except Exception as _e:
                return {'ok': False, 'error': str(_e)}, 500
    except Exception as _e:
        print(f"[static] landing-assets route setup failed: {_e}")

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        from flask import render_template
        import logging
        
        logging.warning(f"404 error: {request.url} from {request.remote_addr}")
        return (
            render_template(
                "error.html",
                error_code=404,
                error_title="Page Not Found",
                error_message="The page you are looking for does not exist.",
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        from flask import render_template, request
        from src.app import db
        import logging
        
        logging.error(f"500 error: {error} from {request.remote_addr} at {request.url}")
        db.session.rollback()
        return (
            render_template(
                "error.html",
                error_code=500,
                error_title="Internal Server Error",
                error_message="Something went wrong on our end. Please try again later.",
            ),
            500,
        )

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        from flask import render_template, request
        import logging
        
        logging.warning(f"403 error: {request.url} from {request.remote_addr}")
        return (
            render_template(
                "error.html",
                error_code=403,
                error_title="Access Forbidden",
                error_message="You do not have permission to access this resource.",
            ),
            403,
        )

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 errors."""
        from flask import render_template, request
        import logging
        
        logging.warning(f"400 error: {request.url} from {request.remote_addr}")
        return (
            render_template(
                "error.html",
                error_code=400,
                error_title="Bad Request",
                error_message="The request could not be processed. Please check your input and try again.",
            ),
            400,
        )

    return app

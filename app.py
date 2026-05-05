"""
FocusLens Lite — Application Entry Point
"""

import logging
import sys
import os

# Ensure the project root is on sys.path regardless of how the script is invoked
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask

from config import config
from session_routes import session_bp


# ── Logging ────────────────────────────────────────────────────────────────────

def _configure_logging() -> None:
    level = logging.DEBUG if config.DEBUG else logging.INFO
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    logging.basicConfig(stream=sys.stdout, level=level, format=fmt)
    # Quieten noisy third-party loggers
    for noisy in ("urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Factory ────────────────────────────────────────────────────────────────────

def create_app() -> Flask:
    _configure_logging()
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG

    # Register blueprints
    app.register_blueprint(session_bp)

    logger.info("FocusLens Lite started (env=%s, debug=%s)", config.FLASK_ENV, config.DEBUG)
    return app


# ── Entry point ────────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)
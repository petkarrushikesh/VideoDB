"""
FocusLens Lite — Configuration
Loads all settings from environment variables. No hardcoded values.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # VideoDB
    VIDEODB_API_KEY: str = os.environ["VIDEODB_API_KEY"]
    VIDEODB_COLLECTION_ID: str | None = os.getenv("VIDEODB_COLLECTION_ID")  # optional; uses default if absent

    # Flask
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(32).hex())

    # Upload limits
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024  # default 500 MB
    ALLOWED_EXTENSIONS: set[str] = {"mp4", "mov", "avi", "mkv", "webm"}

    # Scene indexing
    SCENE_PROMPT: str = os.getenv(
        "SCENE_PROMPT",
        (
            "Describe whether the person appears focused (looking at screen, reading, writing, "
            "typing) or distracted (on phone, looking away, talking to someone, yawning, "
            "leaning back) or idle (not present, seat empty, lights off). "
            "Be concise and specific."
        ),
    )
    SCENE_EXTRACTION_TYPE: str = os.getenv("SCENE_EXTRACTION_TYPE", "time")  # "time" | "shot"
    SCENE_INTERVAL_SECONDS: int = int(os.getenv("SCENE_INTERVAL_SECONDS", "10"))
    SCENE_FRAME_COUNT: int = int(os.getenv("SCENE_FRAME_COUNT", "2"))


config = Config()

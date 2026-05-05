"""
FocusLens Lite — Session Routes
Exposes:
  POST /upload-session   — upload a video and receive a focus analysis report
  GET  /health           — health check
"""

import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import config
from videodb_service import upload_video, create_scene_index, fetch_scene_index, index_spoken_words
from analyzer import analyze_scenes
from summary import build_summary

logger = logging.getLogger(__name__)

session_bp = Blueprint("session", __name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


def _error(message: str, status: int = 400) -> tuple:
    logger.warning("Returning %d: %s", status, message)
    return jsonify({"error": message}), status


# ── Routes ─────────────────────────────────────────────────────────────────────

@session_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "FocusLens Lite"})


@session_bp.route("/upload-session", methods=["POST"])
def upload_session():
    """
    Accepts a multipart/form-data video upload, runs it through
    VideoDB scene indexing, and returns a structured focus report.

    Form fields:
      file          — required, video file
      language_code — optional, BCP-47 code for spoken word indexing (e.g. "en")
      index_audio   — optional, "true" to also index spoken words

    Returns 200 JSON on success, 4xx/5xx on error.
    """

    # ── 1. Validate request ────────────────────────────────────────────────────
    if "file" not in request.files:
        return _error("No 'file' field in the request.")

    file = request.files["file"]
    if not file or file.filename == "":
        return _error("No file selected.")

    if not _allowed_file(file.filename):
        exts = ", ".join(config.ALLOWED_EXTENSIONS)
        return _error(f"Unsupported file type. Allowed: {exts}")

    language_code: str | None = request.form.get("language_code") or None
    index_audio: bool = request.form.get("index_audio", "false").lower() == "true"

    # ── 2. Save to a temp file ─────────────────────────────────────────────────
    suffix = Path(file.filename).suffix
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    try:
        logger.info("Saving upload to temp file: %s", tmp_file.name)
        file.save(tmp_file.name)

        # ── 3. Upload to VideoDB ───────────────────────────────────────────────
        video = upload_video(tmp_file.name)

        if index_audio:
            index_spoken_words(video, language_code=language_code)

        scene_index_id = create_scene_index(video)

        raw_scenes = fetch_scene_index(video, scene_index_id)

        # ── 7. Classify events ────────────────────────────────────────────────
        events = analyze_scenes(raw_scenes)

        # ── 8. Build summary ──────────────────────────────────────────────────
        summary = build_summary(events)

        response_payload = {
            "video_id": video.id,
            "scene_index_id": scene_index_id,
            **summary.to_dict(),
        }

        return jsonify(response_payload), 200

    except FileNotFoundError as exc:
        return _error(str(exc), 400)

    except ValueError as exc:
        return _error(str(exc), 422)

    except RuntimeError as exc:
        logger.exception("VideoDB processing error")
        return _error(f"Processing failed: {exc}", 502)

    except Exception as exc:
        logger.exception("Unexpected error in /upload-session")
        return _error(f"Internal error: {exc}", 500)

    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_file.name)
        except OSError:
            pass
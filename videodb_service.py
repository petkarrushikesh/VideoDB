"""
FocusLens Lite — VideoDB Service
Handles all interaction with the VideoDB SDK:
  - Connecting and resolving the collection
  - Uploading a video file
  - Creating a visual (scene) index
  - Fetching indexed scene data
"""

import logging
from pathlib import Path
from typing import Optional

import videodb
from videodb import SceneExtractionType

from config import config

logger = logging.getLogger(__name__)


def _get_collection():
    """Connect to VideoDB and return the target collection."""
    conn = videodb.connect(api_key=config.VIDEODB_API_KEY)

    if config.VIDEODB_COLLECTION_ID:
        logger.debug("Using configured collection: %s", config.VIDEODB_COLLECTION_ID)
        return conn.get_collection(config.VIDEODB_COLLECTION_ID)

    logger.debug("No collection ID configured — using default collection.")
    return conn.get_collection()


def upload_video(file_path: str | Path):
    """
    Upload a local video file to VideoDB.

    Args:
        file_path: Absolute path to the video file on disk.

    Returns:
        A VideoDB Video object.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: On any VideoDB SDK error.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    logger.info("Uploading video: %s (%.1f MB)", path.name, path.stat().st_size / 1_048_576)

    try:
        coll = _get_collection()
        video = coll.upload(file_path=str(path))
        logger.info("Upload complete — video ID: %s", video.id)
        return video
    except Exception as exc:
        logger.exception("VideoDB upload failed")
        raise RuntimeError(f"VideoDB upload error: {exc}") from exc


def create_scene_index(video) -> str:
    """
    Create a visual scene index on the uploaded video.

    Uses the configured extraction strategy and prompt so the model
    annotates every segment with focus/distraction/idle observations.

    Args:
        video: A VideoDB Video object returned by upload_video().

    Returns:
        The scene_index_id string.

    Raises:
        RuntimeError: On any VideoDB SDK error.
    """
    extraction_type_map = {
        "time": SceneExtractionType.time_based,
        "shot": SceneExtractionType.shot_based,
    }
    extraction_type = extraction_type_map.get(
        config.SCENE_EXTRACTION_TYPE, SceneExtractionType.time_based
    )

    if extraction_type == SceneExtractionType.time_based:
        extraction_config = {
            "time": config.SCENE_INTERVAL_SECONDS,
            "frame_count": config.SCENE_FRAME_COUNT,
        }
    else:  # shot_based
        extraction_config = {
            "threshold": 20,
            "frame_count": config.SCENE_FRAME_COUNT,
        }

    logger.info(
        "Creating scene index | type=%s | config=%s | prompt=%s…",
        config.SCENE_EXTRACTION_TYPE,
        extraction_config,
        config.SCENE_PROMPT[:60],
    )

    try:
        scene_index_id = video.index_scenes(
            extraction_type=extraction_type,
            extraction_config=extraction_config,
            prompt=config.SCENE_PROMPT,
        )
        logger.info("Scene index created: %s", scene_index_id)
        return scene_index_id
    except Exception as exc:
        logger.exception("Scene indexing failed")
        raise RuntimeError(f"VideoDB scene indexing error: {exc}") from exc


def fetch_scene_index(video, scene_index_id: str) -> list[dict]:
    """
    Retrieve all annotated scenes from a scene index.

    Args:
        video: The VideoDB Video object.
        scene_index_id: ID returned by create_scene_index().

    Returns:
        A list of raw scene dicts, each containing at least:
          { "start": float, "end": float, "description": str }

    Raises:
        RuntimeError: On any VideoDB SDK error or empty index.
    """
    logger.info("Fetching scenes for index: %s", scene_index_id)
    try:
        raw_scenes = video.get_scene_index(scene_index_id)
    except Exception as exc:
        logger.exception("Failed to fetch scene index")
        raise RuntimeError(f"VideoDB fetch error: {exc}") from exc

    if not raw_scenes:
        raise RuntimeError("VideoDB returned an empty scene index — video may be too short or silent.")

    scenes: list[dict] = []
    for scene in raw_scenes:
        scenes.append(
            {
                "start": float(scene.start),
                "end": float(scene.end),
                "description": scene.description or "",
            }
        )

    logger.info("Retrieved %d scenes from index %s", len(scenes), scene_index_id)
    return scenes


def index_spoken_words(video, language_code: Optional[str] = None) -> None:
    """
    Optionally index spoken audio content.
    Useful for detecting conversations / background distractions.

    Args:
        video: The VideoDB Video object.
        language_code: BCP-47 language code (e.g. "en", "hi"). None = auto-detect.
    """
    logger.info("Indexing spoken words (language=%s)", language_code or "auto")
    try:
        if language_code:
            video.index_spoken_words(language_code=language_code)
        else:
            video.index_spoken_words()
        logger.info("Spoken word index created for video %s", video.id)
    except Exception as exc:
        # Non-fatal — spoken word indexing is optional
        logger.warning("Spoken word indexing skipped: %s", exc)
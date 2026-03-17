from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["DEBUG"] = "false"

from app.config import Settings, build_cors_headers_for_origin, resolve_allowed_cors_origins


def _production_settings() -> Settings:
    settings = Settings()
    settings.ENVIRONMENT = "production"
    settings.CORS_ALLOW_ORIGINS = [
        "https://trdrhub.com",
        "https://www.trdrhub.com",
    ]
    settings.FRONTEND_URL = "https://app.trdrhub.com"
    return settings


def test_production_cors_resolution_includes_app_frontend_origin():
    settings = _production_settings()

    allowed = resolve_allowed_cors_origins(settings)

    assert "https://trdrhub.com" in allowed
    assert "https://www.trdrhub.com" in allowed
    assert "https://app.trdrhub.com" in allowed
    assert "*" not in allowed


def test_request_cors_headers_allow_app_frontend_origin():
    settings = _production_settings()

    headers = build_cors_headers_for_origin(settings, "https://app.trdrhub.com")

    assert headers["Access-Control-Allow-Origin"] == "https://app.trdrhub.com"
    assert headers["Access-Control-Allow-Credentials"] == "true"

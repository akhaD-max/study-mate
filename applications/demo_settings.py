"""Explicit opt-in integration sandbox; shared config remains unchanged."""

from copy import deepcopy
from pathlib import Path

from config import settings as base_settings

for _name in dir(base_settings):
    if _name.isupper():
        globals()[_name] = getattr(base_settings, _name)

ROOT_URLCONF = "applications.demo_urls"
INSTALLED_APPS = base_settings.INSTALLED_APPS
TEMPLATES = deepcopy(base_settings.TEMPLATES)
TEMPLATES[0]["DIRS"].append(Path(__file__).parent / "demo_templates")

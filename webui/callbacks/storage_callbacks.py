"""
Storage callbacks - DEPRECATED

Settings persistence has been moved to control_callbacks.py which uses
SQLite database storage via webui/utils/local_storage.py instead of
browser localStorage.

This file is kept for backwards compatibility but registers no callbacks.
"""


def register_storage_callbacks(app):
    """No-op - callbacks moved to control_callbacks.py for database persistence"""
    pass

"""
Trading Agents Framework - Web UI Package
"""
from webui.app_dash import run_app

__all__ = ["run_app", "main"]


def main():
    """Entry point for the web UI when installed as a package."""
    run_app()

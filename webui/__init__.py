"""
Trading Agents Framework - Web UI Package
"""
from webui.app_dash import run_app

# Explicitly import submodules for patch compatibility in Python 3.10
from webui import utils
from webui import callbacks
from webui import components

__all__ = ["run_app", "main", "utils", "callbacks", "components"]


def main():
    """Entry point for the web UI when installed as a package."""
    run_app()

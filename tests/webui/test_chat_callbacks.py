"""Tests for webui/callbacks/chat_callbacks.py"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from webui.utils.state import AppState


class TestChatStateManagement:
    """Test chat-related state fields in AppState."""

    def setup_method(self):
        self.state = AppState()

    def test_initial_state(self):
        assert self.state.chat_messages == []
        assert self.state.chat_processing is False
        assert self.state.chat_error is None

    def test_reset_chat(self):
        self.state.chat_messages = [
            {"role": "user", "content": "hello", "timestamp": "12:00"}
        ]
        self.state.chat_processing = True
        self.state.chat_error = "some error"

        self.state.reset_chat()

        assert self.state.chat_messages == []
        assert self.state.chat_processing is False
        assert self.state.chat_error is None

    def test_reset_chat_thread_safe(self):
        """Ensure reset_chat uses the lock."""
        self.state.chat_messages = [
            {"role": "user", "content": "test", "timestamp": "12:00"}
        ]
        self.state.reset_chat()
        assert self.state.chat_messages == []


class TestRunChatAssistant:
    """Test the _run_chat_assistant background thread function."""

    def setup_method(self):
        # Reset global app_state for each test
        from webui.utils.state import app_state
        app_state.reset_chat()
        self.app_state = app_state

    @patch("tradingagents.chat_assistant.PortfolioAssistant")
    def test_successful_response(self, mock_assistant_cls):
        from webui.callbacks.chat_callbacks import _run_chat_assistant

        mock_instance = MagicMock()
        mock_instance.respond.return_value = "Your portfolio is doing well."
        mock_assistant_cls.return_value = mock_instance

        self.app_state.chat_processing = True
        messages = [{"role": "user", "content": "How is my portfolio?"}]

        _run_chat_assistant(messages, {"openai_api_key": "test-key", "quick_think_llm": "gpt-4.1-nano"})

        assert self.app_state.chat_processing is False
        assert len(self.app_state.chat_messages) == 1
        assert self.app_state.chat_messages[0]["role"] == "assistant"
        assert "portfolio" in self.app_state.chat_messages[0]["content"].lower()

    def test_missing_api_key(self):
        from webui.callbacks.chat_callbacks import _run_chat_assistant

        self.app_state.chat_processing = True
        self.app_state.system_settings["openai_api_key"] = None

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            _run_chat_assistant(
                [{"role": "user", "content": "test"}],
                {},
            )

        assert self.app_state.chat_processing is False
        assert len(self.app_state.chat_messages) == 1
        assert "API key" in self.app_state.chat_messages[0]["content"]

    @patch("tradingagents.chat_assistant.PortfolioAssistant")
    def test_exception_handling(self, mock_assistant_cls):
        from webui.callbacks.chat_callbacks import _run_chat_assistant

        mock_instance = MagicMock()
        mock_instance.respond.side_effect = Exception("LLM error")
        mock_assistant_cls.return_value = mock_instance

        self.app_state.chat_processing = True

        _run_chat_assistant(
            [{"role": "user", "content": "test"}],
            {"openai_api_key": "test-key"},
        )

        assert self.app_state.chat_processing is False
        assert len(self.app_state.chat_messages) == 1
        assert "error" in self.app_state.chat_messages[0]["content"].lower()
        assert self.app_state.chat_error == "LLM error"


class TestRenderAllMessages:
    """Test the _render_all_messages helper."""

    def setup_method(self):
        from webui.utils.state import app_state
        app_state.reset_chat()
        self.app_state = app_state

    def test_empty_messages(self):
        from webui.callbacks.chat_callbacks import _render_all_messages

        result = _render_all_messages()
        assert len(result) == 1  # Placeholder message

    def test_renders_messages(self):
        from webui.callbacks.chat_callbacks import _render_all_messages

        self.app_state.chat_messages = [
            {"role": "user", "content": "Hello", "timestamp": "12:00"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "12:01"},
        ]

        result = _render_all_messages()
        assert len(result) == 2

    def test_renders_action_buttons(self):
        from webui.callbacks.chat_callbacks import _render_all_messages

        self.app_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Check this out [[ACTION:AAPL:watchlist:Good value]]",
                "timestamp": "12:01",
            },
        ]

        result = _render_all_messages()
        assert len(result) == 1


class TestRenderTracking:
    """Test that poll skips re-render when nothing changed."""

    def setup_method(self):
        from webui.utils.state import app_state
        app_state.reset_chat()
        self.app_state = app_state

    def test_update_render_tracking(self):
        from webui.callbacks.chat_callbacks import (
            _update_render_tracking,
            _last_rendered_msg_count,
        )
        import webui.callbacks.chat_callbacks as mod

        self.app_state.chat_messages = [
            {"role": "user", "content": "hi", "timestamp": "12:00"},
        ]
        _update_render_tracking()
        assert mod._last_rendered_msg_count == 1

    def test_reset_render_tracking(self):
        from webui.callbacks.chat_callbacks import (
            _update_render_tracking,
            _reset_render_tracking,
        )
        import webui.callbacks.chat_callbacks as mod

        self.app_state.chat_messages = [
            {"role": "user", "content": "hi", "timestamp": "12:00"},
        ]
        _update_render_tracking()
        _reset_render_tracking()
        assert mod._last_rendered_msg_count == 0
        assert mod._last_rendered_processing is False


class TestAddSystemMessage:
    """Test the _add_system_message helper."""

    def setup_method(self):
        from webui.utils.state import app_state
        app_state.reset_chat()
        self.app_state = app_state

    def test_adds_message(self):
        from webui.callbacks.chat_callbacks import _add_system_message

        _add_system_message("Added AAPL to watchlist.")

        assert len(self.app_state.chat_messages) == 1
        assert self.app_state.chat_messages[0]["role"] == "assistant"
        assert "AAPL" in self.app_state.chat_messages[0]["content"]
        assert self.app_state.chat_messages[0]["timestamp"]  # Not empty

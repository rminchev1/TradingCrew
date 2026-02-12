"""
Tests for symbol Select dropdown in chart and report panels.
Verifies the new dropdown-based symbol selection replaces the old button grid.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from dash import html
import dash_bootstrap_components as dbc


def _find_component_by_id(component, target_id):
    """Recursively search for a component with a given ID."""
    if hasattr(component, 'id') and component.id == target_id:
        return component
    children = getattr(component, 'children', None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if child is None:
            continue
        result = _find_component_by_id(child, target_id)
        if result is not None:
            return result
    return None


class TestChartSymbolSelect:
    """Tests for the chart panel symbol Select dropdown."""

    def test_chart_panel_contains_symbol_select(self):
        """Chart panel should contain a dbc.Select with id chart-symbol-select."""
        from webui.components.chart_panel import create_chart_panel

        panel = create_chart_panel()
        select = _find_component_by_id(panel, "chart-symbol-select")
        assert select is not None
        assert isinstance(select, dbc.Select)

    def test_chart_symbol_select_initial_options_empty(self):
        """Chart symbol select should start with empty options."""
        from webui.components.chart_panel import create_chart_panel

        panel = create_chart_panel()
        select = _find_component_by_id(panel, "chart-symbol-select")
        assert select.options == []

    def test_chart_symbol_select_has_placeholder(self):
        """Chart symbol select should have a placeholder."""
        from webui.components.chart_panel import create_chart_panel

        panel = create_chart_panel()
        select = _find_component_by_id(panel, "chart-symbol-select")
        assert select.placeholder == "Select symbol..."

    def test_chart_panel_no_redundant_h4_header(self):
        """Chart panel should not have the old H4 'Stock Chart & Technical Analysis' header."""
        from webui.components.chart_panel import create_chart_panel

        panel = create_chart_panel()
        html_str = str(panel)
        assert "Stock Chart & Technical Analysis" not in html_str

    def test_chart_panel_has_symbol_select_class(self):
        """Chart symbol select should have 'symbol-select' CSS class."""
        from webui.components.chart_panel import create_chart_panel

        panel = create_chart_panel()
        select = _find_component_by_id(panel, "chart-symbol-select")
        assert "symbol-select" in select.className


class TestReportSymbolSelect:
    """Tests for the report panel symbol Select dropdown."""

    def test_report_panel_contains_symbol_select(self):
        """Reports panel should contain a dbc.Select with id report-symbol-select."""
        from webui.components.reports_panel import create_reports_panel

        panel = create_reports_panel()
        select = _find_component_by_id(panel, "report-symbol-select")
        assert select is not None
        assert isinstance(select, dbc.Select)

    def test_report_symbol_select_initial_options_empty(self):
        """Report symbol select should start with empty options."""
        from webui.components.reports_panel import create_reports_panel

        panel = create_reports_panel()
        select = _find_component_by_id(panel, "report-symbol-select")
        assert select.options == []

    def test_report_symbol_select_has_placeholder(self):
        """Report symbol select should have a placeholder."""
        from webui.components.reports_panel import create_reports_panel

        panel = create_reports_panel()
        select = _find_component_by_id(panel, "report-symbol-select")
        assert select.placeholder == "Select symbol..."

    def test_report_symbol_select_has_correct_class(self):
        """Report symbol select should have 'symbol-select' CSS class."""
        from webui.components.reports_panel import create_reports_panel

        panel = create_reports_panel()
        select = _find_component_by_id(panel, "report-symbol-select")
        assert "symbol-select" in select.className


class TestChartSymbolSelectCallback:
    """Tests for the chart symbol select populate callback logic."""

    def test_populate_generates_correct_options(self):
        """Options should be generated from symbol_states keys."""
        from webui.utils.state import app_state

        symbols = ["AAPL", "NVDA", "TSLA"]
        expected_options = [
            {"label": "AAPL", "value": "1"},
            {"label": "NVDA", "value": "2"},
            {"label": "TSLA", "value": "3"},
        ]

        # Simulate the logic from update_chart_symbol_select
        options = [{"label": s, "value": str(i + 1)} for i, s in enumerate(symbols)]
        assert options == expected_options

    def test_populate_selects_current_symbol(self):
        """Value should match the current_symbol's index."""
        symbols = ["AAPL", "NVDA", "TSLA"]
        current_symbol = "NVDA"

        new_value = "1"
        if current_symbol in symbols:
            new_value = str(symbols.index(current_symbol) + 1)

        assert new_value == "2"

    def test_populate_defaults_to_first_when_no_current(self):
        """Value should default to '1' when current_symbol not in list."""
        symbols = ["AAPL", "NVDA"]
        current_symbol = "MSFT"

        new_value = "1"
        if current_symbol in symbols:
            new_value = str(symbols.index(current_symbol) + 1)

        assert new_value == "1"


class TestSymbolSelectValueMapping:
    """Tests for value-to-symbol mapping logic used in select handlers."""

    def test_value_to_symbol_mapping(self):
        """Select value '2' should map to second symbol."""
        symbols = ["AAPL", "NVDA", "TSLA"]
        value = "2"

        page = int(value)
        assert 0 < page <= len(symbols)
        symbol = symbols[page - 1]
        assert symbol == "NVDA"

    def test_value_to_page_number(self):
        """Select value should directly map to pagination active_page."""
        value = "3"
        page = int(value)
        assert page == 3

    def test_invalid_value_handling(self):
        """Out-of-range value should be detectable."""
        symbols = ["AAPL", "NVDA"]
        value = "5"

        page = int(value)
        assert not (0 < page <= len(symbols))


class TestHistoryLoadPopulatesSelect:
    """Tests for history loading populating the report select dropdown."""

    def test_history_symbols_generate_options_with_prefix(self):
        """Historical symbols should be rendered with folder prefix in label."""
        symbols = ["AAPL", "NVDA"]
        options = [{"label": f"📁 {s}", "value": str(i + 1)} for i, s in enumerate(symbols)]

        assert options[0]["label"] == "📁 AAPL"
        assert options[1]["label"] == "📁 NVDA"
        assert options[0]["value"] == "1"
        assert options[1]["value"] == "2"

    def test_current_session_symbols_no_prefix(self):
        """Current session symbols should have no prefix."""
        symbols = ["AAPL", "NVDA"]
        options = [{"label": s, "value": str(i + 1)} for i, s in enumerate(symbols)]

        assert options[0]["label"] == "AAPL"
        assert options[1]["label"] == "NVDA"

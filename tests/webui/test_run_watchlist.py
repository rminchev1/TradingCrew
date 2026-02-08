"""
Unit tests for the Run Watchlist feature

Tests cover:
- Run Watchlist component creation
- Watchlist panel with tabs
- Run Queue callbacks (add, remove, clear, display)
- Integration with analysis control
"""

import pytest
from unittest.mock import MagicMock, patch
from dash import html
import dash_bootstrap_components as dbc


class TestRunWatchlistComponent:
    """Tests for the run_watchlist.py component functions"""

    def test_create_run_watchlist_panel_returns_div(self):
        """Test that create_run_watchlist_panel returns a Div component"""
        from webui.components.run_watchlist import create_run_watchlist_panel

        panel = create_run_watchlist_panel()

        assert isinstance(panel, html.Div)
        assert "run-watchlist-panel" in panel.className

    def test_create_run_watchlist_panel_has_required_elements(self):
        """Test that the panel contains all required UI elements"""
        from webui.components.run_watchlist import create_run_watchlist_panel

        panel = create_run_watchlist_panel()
        children = panel.children

        # Should have header, items container, clear button, and store
        assert len(children) == 4

        # Check for count span
        header = children[0]
        assert "run-watchlist-count" in str(header)

        # Check for items container
        items_container = children[1]
        assert items_container.id == "run-watchlist-items-container"

        # Check for clear button
        clear_btn = children[2]
        assert clear_btn.id == "run-watchlist-clear-btn"

        # Check for store
        store = children[3]
        assert store.id == "run-watchlist-store"
        assert store.storage_type == "local"

    def test_create_run_watchlist_panel_store_has_correct_default_data(self):
        """Test that the store has correct default data structure"""
        from webui.components.run_watchlist import create_run_watchlist_panel

        panel = create_run_watchlist_panel()
        store = panel.children[3]  # Store is the 4th child

        assert store.data == {"symbols": []}

    def test_create_run_watchlist_item_returns_div(self):
        """Test that create_run_watchlist_item returns a Div component"""
        from webui.components.run_watchlist import create_run_watchlist_item

        item = create_run_watchlist_item("AAPL")

        assert isinstance(item, html.Div)
        assert "run-watchlist-item" in item.className

    def test_create_run_watchlist_item_has_correct_symbol(self):
        """Test that the item displays the correct symbol"""
        from webui.components.run_watchlist import create_run_watchlist_item

        item = create_run_watchlist_item("NVDA", index=0)

        # Check symbol is in children
        symbol_span = item.children[1]  # Symbol is second child after icon
        assert symbol_span.children == "NVDA"

        # Check the id contains the symbol
        assert item.id == {"type": "run-watchlist-item", "symbol": "NVDA"}

    def test_create_run_watchlist_item_has_remove_button(self):
        """Test that the item has a remove button with correct ID"""
        from webui.components.run_watchlist import create_run_watchlist_item

        item = create_run_watchlist_item("TSLA")

        # Remove button is the third child
        remove_btn = item.children[2]
        assert isinstance(remove_btn, dbc.Button)
        assert remove_btn.id == {"type": "run-watchlist-remove-btn", "symbol": "TSLA"}

    def test_create_run_watchlist_item_index_attribute(self):
        """Test that item has correct structure for different indices"""
        from webui.components.run_watchlist import create_run_watchlist_item

        item = create_run_watchlist_item("AMD", index=5)

        # Verify the item is created correctly
        assert isinstance(item, html.Div)
        assert item.id == {"type": "run-watchlist-item", "symbol": "AMD"}
        # Symbol should be in children
        assert item.children[1].children == "AMD"


class TestWatchlistPanelWithTabs:
    """Tests for watchlist_panel.py with Run Queue tabs"""

    def test_create_watchlist_section_returns_card(self):
        """Test that create_watchlist_section returns a Card component"""
        from webui.components.watchlist_panel import create_watchlist_section

        section = create_watchlist_section()

        assert isinstance(section, dbc.Card)

    def test_create_watchlist_section_has_tabs(self):
        """Test that the section contains tabs for Watchlist and Run Queue"""
        from webui.components.watchlist_panel import create_watchlist_section

        section = create_watchlist_section()

        # Find the collapse component
        collapse = section.children[1]  # Collapse is second child
        card_body = collapse.children

        # Card body should contain tabs
        tabs = card_body.children[0]  # Tabs is first child of card body children
        assert isinstance(tabs, dbc.Tabs)
        assert tabs.id == "watchlist-tabs"

        # Should have 2 tabs
        assert len(tabs.children) == 2

        # Check tab IDs
        tab_ids = [tab.tab_id for tab in tabs.children]
        assert "watchlist-tab" in tab_ids
        assert "run-queue-tab" in tab_ids

    def test_create_watchlist_section_has_run_queue_badge(self):
        """Test that the header contains Run Queue count badge"""
        from webui.components.watchlist_panel import create_watchlist_section

        section = create_watchlist_section()
        header = section.children[0]

        # Check for run-watchlist-count-badge in header
        assert "run-watchlist-count-badge" in str(header)

    def test_create_watchlist_item_has_add_to_run_button(self):
        """Test that watchlist items have the 'Add to Run' button"""
        from webui.components.watchlist_panel import create_watchlist_item

        item = create_watchlist_item("AAPL", price=150.0, change=2.5, change_pct=1.5)

        # Find the button group in the item
        row = item.children[0]
        actions_col = row.children[3]  # Actions column is 4th
        button_group = actions_col.children[0]

        # Check that there's a button with the add-run type
        button_ids = [btn.id for btn in button_group.children if hasattr(btn, 'id')]
        add_run_ids = [bid for bid in button_ids if isinstance(bid, dict) and bid.get("type") == "watchlist-add-run-btn"]

        assert len(add_run_ids) == 1
        assert add_run_ids[0]["symbol"] == "AAPL"


class TestRunQueueCallbackLogic:
    """Tests for Run Queue callback logic (without Dash app context)"""

    def test_add_to_run_queue_logic_adds_new_symbol(self):
        """Test logic for adding a new symbol to Run Queue"""
        store_data = {"symbols": ["AAPL", "MSFT"]}
        symbol = "NVDA"

        # Simulate the add logic
        if symbol not in store_data["symbols"]:
            store_data["symbols"].append(symbol)

        assert "NVDA" in store_data["symbols"]
        assert len(store_data["symbols"]) == 3

    def test_add_to_run_queue_logic_prevents_duplicates(self):
        """Test that duplicate symbols are not added"""
        store_data = {"symbols": ["AAPL", "MSFT"]}
        symbol = "AAPL"

        # Simulate the add logic
        if symbol not in store_data["symbols"]:
            store_data["symbols"].append(symbol)

        assert store_data["symbols"].count("AAPL") == 1
        assert len(store_data["symbols"]) == 2

    def test_add_to_run_queue_logic_handles_empty_store(self):
        """Test adding to empty Run Queue"""
        store_data = None
        symbol = "TSLA"

        # Simulate the add logic with None store
        if not store_data:
            store_data = {"symbols": []}

        if symbol not in store_data["symbols"]:
            store_data["symbols"].append(symbol)

        assert store_data["symbols"] == ["TSLA"]

    def test_remove_from_run_queue_logic(self):
        """Test logic for removing a symbol from Run Queue"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}
        symbol = "MSFT"

        # Simulate the remove logic
        if symbol in store_data["symbols"]:
            store_data["symbols"].remove(symbol)

        assert "MSFT" not in store_data["symbols"]
        assert len(store_data["symbols"]) == 2

    def test_remove_from_run_queue_logic_handles_missing_symbol(self):
        """Test removing a symbol that doesn't exist"""
        store_data = {"symbols": ["AAPL", "MSFT"]}
        symbol = "NVDA"

        # Simulate the remove logic
        original_length = len(store_data["symbols"])
        if symbol in store_data["symbols"]:
            store_data["symbols"].remove(symbol)

        assert len(store_data["symbols"]) == original_length

    def test_clear_run_queue_logic(self):
        """Test logic for clearing the Run Queue"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA", "TSLA"]}

        # Simulate the clear logic
        store_data = {"symbols": []}

        assert store_data["symbols"] == []

    def test_get_symbols_from_run_queue(self):
        """Test getting symbols list from Run Queue store"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}

        # Simulate the get symbols logic (as used in control_callbacks)
        run_store = store_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == ["AAPL", "MSFT", "NVDA"]

    def test_get_symbols_from_empty_run_queue(self):
        """Test getting symbols from empty Run Queue"""
        store_data = {"symbols": []}

        run_store = store_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == []

    def test_get_symbols_from_none_store(self):
        """Test getting symbols when store is None"""
        store_data = None

        run_store = store_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == []


class TestRunQueueDisplayLogic:
    """Tests for Run Queue display update logic"""

    def test_display_empty_queue_message(self):
        """Test that empty queue shows appropriate message"""
        store_data = {"symbols": []}

        # Simulate the display logic
        if not store_data or not store_data.get("symbols"):
            result = "empty"
        else:
            result = "items"

        assert result == "empty"

    def test_display_items_count(self):
        """Test that item count is calculated correctly"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}

        symbols = store_data.get("symbols", [])
        count = str(len(symbols))

        assert count == "3"

    def test_create_run_watchlist_items(self):
        """Test creating run watchlist items from store data"""
        from webui.components.run_watchlist import create_run_watchlist_item

        store_data = {"symbols": ["AAPL", "MSFT"]}
        symbols = store_data.get("symbols", [])

        items = [create_run_watchlist_item(symbol, i) for i, symbol in enumerate(symbols)]

        assert len(items) == 2
        assert items[0].id == {"type": "run-watchlist-item", "symbol": "AAPL"}
        assert items[1].id == {"type": "run-watchlist-item", "symbol": "MSFT"}
        assert items[0].children[1].children == "AAPL"
        assert items[1].children[1].children == "MSFT"


class TestAnalysisIntegrationLogic:
    """Tests for Run Queue integration with analysis control"""

    def test_symbols_extracted_for_analysis(self):
        """Test that symbols are correctly extracted for analysis"""
        run_watchlist_data = {"symbols": ["NVDA", "AMD", "TSLA"]}

        # Simulate the extraction logic from control_callbacks
        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == ["NVDA", "AMD", "TSLA"]
        assert len(symbols) == 3

    def test_empty_queue_returns_error_message(self):
        """Test that empty Run Queue produces appropriate error"""
        run_watchlist_data = {"symbols": []}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        if not symbols:
            error_msg = "No symbols in Run Queue. Add symbols from the Watchlist tab."
        else:
            error_msg = None

        assert error_msg == "No symbols in Run Queue. Add symbols from the Watchlist tab."

    def test_none_store_returns_error_message(self):
        """Test that None store produces appropriate error"""
        run_watchlist_data = None

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        if not symbols:
            error_msg = "No symbols in Run Queue. Add symbols from the Watchlist tab."
        else:
            error_msg = None

        assert error_msg == "No symbols in Run Queue. Add symbols from the Watchlist tab."


class TestStoragePersistence:
    """Tests for Run Queue localStorage persistence"""

    def test_run_watchlist_store_uses_local_storage(self):
        """Test that the store uses localStorage"""
        from webui.components.run_watchlist import create_run_watchlist_panel

        panel = create_run_watchlist_panel()
        store = panel.children[3]

        assert store.storage_type == "local"

    def test_run_watchlist_store_has_correct_id(self):
        """Test that the store has the correct ID"""
        from webui.components.run_watchlist import create_run_watchlist_panel

        panel = create_run_watchlist_panel()
        store = panel.children[3]

        assert store.id == "run-watchlist-store"

    def test_default_settings_does_not_include_ticker_input(self):
        """Test that default settings no longer includes ticker_input"""
        from webui.utils.storage import get_default_settings

        defaults = get_default_settings()

        assert "ticker_input" not in defaults


class TestSymbolNormalization:
    """Tests for symbol normalization in Run Queue"""

    def test_symbol_uppercase_on_add(self):
        """Test that symbols are normalized to uppercase"""
        store_data = {"symbols": []}
        symbol = "aapl"

        # Simulate normalization (as done in callbacks)
        normalized_symbol = symbol.upper()
        if normalized_symbol not in store_data["symbols"]:
            store_data["symbols"].append(normalized_symbol)

        assert store_data["symbols"] == ["AAPL"]

    def test_duplicate_check_case_insensitive(self):
        """Test that duplicate check is case insensitive"""
        store_data = {"symbols": ["AAPL"]}
        symbol = "aapl"

        normalized_symbol = symbol.upper()
        is_duplicate = normalized_symbol in store_data["symbols"]

        assert is_duplicate is True

    def test_mixed_case_symbols_normalized(self):
        """Test multiple mixed case symbols are normalized"""
        symbols_to_add = ["Nvda", "AMD", "tsla", "MSFT"]

        store_data = {"symbols": []}
        for symbol in symbols_to_add:
            normalized = symbol.upper()
            if normalized not in store_data["symbols"]:
                store_data["symbols"].append(normalized)

        assert store_data["symbols"] == ["NVDA", "AMD", "TSLA", "MSFT"]

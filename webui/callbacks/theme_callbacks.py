"""
Theme-related callbacks for TradingAgents WebUI
"""

from dash import Input, Output, State, callback_context, html, clientside_callback


def register_theme_callbacks(app):
    """Register theme toggle callbacks"""

    # Clientside callback to toggle theme class on body
    app.clientside_callback(
        """
        function(n_clicks, stored_data) {
            // Get current theme from store or default to 'dark'
            let currentTheme = (stored_data && stored_data.theme) ? stored_data.theme : 'dark';

            // If button was clicked, toggle theme
            if (n_clicks && n_clicks > 0) {
                currentTheme = currentTheme === 'dark' ? 'bw' : 'dark';
            }

            // Apply theme class to body
            if (currentTheme === 'bw') {
                document.body.classList.add('theme-bw');
            } else {
                document.body.classList.remove('theme-bw');
            }

            // Return updated store data
            return {'theme': currentTheme};
        }
        """,
        Output("theme-store", "data"),
        Input("theme-toggle-btn", "n_clicks"),
        State("theme-store", "data")
    )

    # Update button text/icon based on current theme
    app.clientside_callback(
        """
        function(stored_data) {
            let theme = (stored_data && stored_data.theme) ? stored_data.theme : 'dark';

            // Apply theme class on initial load
            if (theme === 'bw') {
                document.body.classList.add('theme-bw');
            } else {
                document.body.classList.remove('theme-bw');
            }

            // Return button content based on theme
            if (theme === 'bw') {
                return ['B&W'];
            } else {
                return ['Dark'];
            }
        }
        """,
        Output("theme-toggle-btn", "children"),
        Input("theme-store", "data")
    )

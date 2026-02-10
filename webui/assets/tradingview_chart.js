/**
 * TradingView Lightweight Charts Manager
 * Handles chart initialization, updates, and theme switching
 * Supports multiple panes for RSI, MACD, and OBV indicators
 */
(function() {
    'use strict';

    // Chart instances storage
    const charts = {};
    const series = {};

    // Theme configurations
    const themes = {
        dark: {
            layout: {
                background: { type: 'solid', color: '#1E293B' },
                textColor: '#F1F5F9',
            },
            grid: {
                vertLines: { color: 'rgba(51, 65, 85, 0.5)' },
                horzLines: { color: 'rgba(51, 65, 85, 0.5)' },
            },
            crosshair: {
                vertLine: {
                    color: '#3B82F6',
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#3B82F6',
                },
                horzLine: {
                    color: '#3B82F6',
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#3B82F6',
                },
            },
            timeScale: {
                borderColor: '#334155',
                timeVisible: true,
                secondsVisible: false,
            },
            rightPriceScale: {
                borderColor: '#334155',
            },
        },
        light: {
            layout: {
                background: { type: 'solid', color: '#FFFFFF' },
                textColor: '#1E293B',
            },
            grid: {
                vertLines: { color: 'rgba(203, 213, 225, 0.5)' },
                horzLines: { color: 'rgba(203, 213, 225, 0.5)' },
            },
            crosshair: {
                vertLine: {
                    color: '#3B82F6',
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#3B82F6',
                },
                horzLine: {
                    color: '#3B82F6',
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#3B82F6',
                },
            },
            timeScale: {
                borderColor: '#CBD5E1',
                timeVisible: true,
                secondsVisible: false,
            },
            rightPriceScale: {
                borderColor: '#CBD5E1',
            },
        }
    };

    // Line colors for indicators
    const lineColors = {
        sma20: '#2196f3',
        sma50: '#ff9800',
        ema12: '#9c27b0',
        ema26: '#e91e63',
        bbUpper: 'rgba(128, 128, 128, 0.7)',
        bbLower: 'rgba(128, 128, 128, 0.7)',
        rsi: '#7c4dff',
        macd: '#2196f3',
        macdSignal: '#ff9800',
        obv: '#06b6d4',
    };

    /**
     * Get current theme based on body class
     */
    function getCurrentTheme() {
        return document.body.classList.contains('theme-bw') ? 'light' : 'dark';
    }

    /**
     * Create indicator pane theme config (smaller, no time axis labels)
     */
    function getIndicatorPaneConfig(theme) {
        const baseConfig = themes[theme];
        return {
            ...baseConfig,
            timeScale: {
                ...baseConfig.timeScale,
                visible: true,
                timeVisible: false,
            },
            rightPriceScale: {
                ...baseConfig.rightPriceScale,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
        };
    }

    /**
     * Initialize a chart in the specified container
     */
    function init(containerId, isIndicatorPane = false) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn('[TradingViewChart] Container not found:', containerId);
            return null;
        }

        // Destroy existing chart if any
        if (charts[containerId]) {
            destroy(containerId);
        }

        const theme = getCurrentTheme();
        const themeConfig = isIndicatorPane ? getIndicatorPaneConfig(theme) : themes[theme];

        // Create the chart
        const chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight || (isIndicatorPane ? 120 : 400),
            ...themeConfig,
            handleScroll: {
                mouseWheel: true,
                pressedMouseMove: true,
                horzTouchDrag: true,
                vertTouchDrag: true,
            },
            handleScale: {
                axisPressedMouseMove: true,
                mouseWheel: true,
                pinch: true,
            },
        });

        charts[containerId] = chart;
        series[containerId] = {};

        // Setup resize observer
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                if (charts[containerId] && width > 0 && height > 0) {
                    charts[containerId].resize(width, height);
                }
            }
        });
        resizeObserver.observe(container);

        // Store resize observer for cleanup
        chart._resizeObserver = resizeObserver;

        return chart;
    }

    /**
     * Sync time scales between main chart and indicator panes
     */
    function syncTimeScales(mainChartId, indicatorChartIds) {
        const mainChart = charts[mainChartId];
        if (!mainChart) return;

        const mainTimeScale = mainChart.timeScale();

        // Subscribe to main chart time scale changes
        mainTimeScale.subscribeVisibleLogicalRangeChange((logicalRange) => {
            if (logicalRange) {
                indicatorChartIds.forEach(id => {
                    const chart = charts[id];
                    if (chart) {
                        chart.timeScale().setVisibleLogicalRange(logicalRange);
                    }
                });
            }
        });

        // Also sync scrolling
        mainTimeScale.subscribeVisibleTimeRangeChange((timeRange) => {
            if (timeRange) {
                indicatorChartIds.forEach(id => {
                    const chart = charts[id];
                    if (chart) {
                        try {
                            chart.timeScale().setVisibleRange(timeRange);
                        } catch (e) {
                            // Ignore if range is invalid for this chart
                        }
                    }
                });
            }
        });
    }

    /**
     * Update main chart with new data
     */
    function update(containerId, data, config) {
        if (!data || !data.candlestick || data.candlestick.length === 0) {
            console.warn('[TradingViewChart] No data to display');
            return;
        }

        let chart = charts[containerId];
        if (!chart) {
            chart = init(containerId);
            if (!chart) return;
        }

        const chartSeries = series[containerId];

        // Clear existing series
        Object.keys(chartSeries).forEach(key => {
            try {
                chart.removeSeries(chartSeries[key]);
            } catch (e) {
                // Series might already be removed
            }
        });
        series[containerId] = {};

        // Create candlestick series
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        candlestickSeries.setData(data.candlestick);
        series[containerId].candlestick = candlestickSeries;

        // Create volume series
        if (data.volume && data.volume.length > 0) {
            const volumeSeries = chart.addHistogramSeries({
                color: '#26a69a',
                priceFormat: {
                    type: 'volume',
                },
                priceScaleId: 'volume',
            });
            chart.priceScale('volume').applyOptions({
                scaleMargins: {
                    top: 0.85,
                    bottom: 0,
                },
            });
            volumeSeries.setData(data.volume);
            series[containerId].volume = volumeSeries;
        }

        // Add SMA lines
        if (data.sma20 && data.sma20.length > 0) {
            const sma20Series = chart.addLineSeries({
                color: lineColors.sma20,
                lineWidth: 1,
                title: 'SMA 20',
            });
            sma20Series.setData(data.sma20);
            series[containerId].sma20 = sma20Series;
        }

        if (data.sma50 && data.sma50.length > 0) {
            const sma50Series = chart.addLineSeries({
                color: lineColors.sma50,
                lineWidth: 1,
                title: 'SMA 50',
            });
            sma50Series.setData(data.sma50);
            series[containerId].sma50 = sma50Series;
        }

        // Add EMA lines
        if (data.ema12 && data.ema12.length > 0) {
            const ema12Series = chart.addLineSeries({
                color: lineColors.ema12,
                lineWidth: 1,
                lineStyle: 1,
                title: 'EMA 12',
            });
            ema12Series.setData(data.ema12);
            series[containerId].ema12 = ema12Series;
        }

        if (data.ema26 && data.ema26.length > 0) {
            const ema26Series = chart.addLineSeries({
                color: lineColors.ema26,
                lineWidth: 1,
                lineStyle: 1,
                title: 'EMA 26',
            });
            ema26Series.setData(data.ema26);
            series[containerId].ema26 = ema26Series;
        }

        // Add Bollinger Bands
        if (data.bbUpper && data.bbUpper.length > 0) {
            const bbUpperSeries = chart.addLineSeries({
                color: lineColors.bbUpper,
                lineWidth: 1,
                lineStyle: 2,
                title: 'BB Upper',
            });
            bbUpperSeries.setData(data.bbUpper);
            series[containerId].bbUpper = bbUpperSeries;
        }

        if (data.bbLower && data.bbLower.length > 0) {
            const bbLowerSeries = chart.addLineSeries({
                color: lineColors.bbLower,
                lineWidth: 1,
                lineStyle: 2,
                title: 'BB Lower',
            });
            bbLowerSeries.setData(data.bbLower);
            series[containerId].bbLower = bbLowerSeries;
        }

        // Fit content to view
        chart.timeScale().fitContent();

        // Handle indicator panes
        const indicatorPanes = [];

        // RSI Pane
        if (data.rsi && data.rsi.length > 0) {
            updateRsiPane(data.rsi);
            indicatorPanes.push('tv-rsi-container');
        } else {
            hideIndicatorPane('tv-rsi-container');
        }

        // MACD Pane
        if ((data.macd && data.macd.length > 0) || (data.macdHist && data.macdHist.length > 0)) {
            updateMacdPane(data);
            indicatorPanes.push('tv-macd-container');
        } else {
            hideIndicatorPane('tv-macd-container');
        }

        // OBV Pane
        if (data.obv && data.obv.length > 0) {
            updateObvPane(data.obv);
            indicatorPanes.push('tv-obv-container');
        } else {
            hideIndicatorPane('tv-obv-container');
        }

        // Sync time scales
        if (indicatorPanes.length > 0) {
            syncTimeScales(containerId, indicatorPanes);
        }
    }

    /**
     * Update RSI indicator pane
     */
    function updateRsiPane(rsiData) {
        const containerId = 'tv-rsi-container';
        const container = document.getElementById(containerId);
        if (!container) return;

        // Show the container
        container.style.display = 'block';

        let chart = charts[containerId];
        if (!chart) {
            chart = init(containerId, true);
            if (!chart) return;
        }

        // Clear existing series
        const chartSeries = series[containerId] || {};
        Object.keys(chartSeries).forEach(key => {
            try {
                chart.removeSeries(chartSeries[key]);
            } catch (e) {}
        });
        series[containerId] = {};

        // Add RSI line
        const rsiSeries = chart.addLineSeries({
            color: lineColors.rsi,
            lineWidth: 2,
            title: 'RSI (14)',
            priceFormat: {
                type: 'custom',
                formatter: (price) => price.toFixed(1),
            },
        });
        rsiSeries.setData(rsiData);
        series[containerId].rsi = rsiSeries;

        // Add overbought/oversold lines
        const lastTime = rsiData[rsiData.length - 1].time;
        const firstTime = rsiData[0].time;

        // Create horizontal lines using line series with constant values
        const overboughtData = rsiData.map(d => ({ time: d.time, value: 70 }));
        const oversoldData = rsiData.map(d => ({ time: d.time, value: 30 }));
        const midlineData = rsiData.map(d => ({ time: d.time, value: 50 }));

        const overboughtSeries = chart.addLineSeries({
            color: 'rgba(239, 68, 68, 0.5)',
            lineWidth: 1,
            lineStyle: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        overboughtSeries.setData(overboughtData);

        const oversoldSeries = chart.addLineSeries({
            color: 'rgba(34, 197, 94, 0.5)',
            lineWidth: 1,
            lineStyle: 2,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        oversoldSeries.setData(oversoldData);

        const midlineSeries = chart.addLineSeries({
            color: 'rgba(128, 128, 128, 0.3)',
            lineWidth: 1,
            lineStyle: 1,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        midlineSeries.setData(midlineData);

        // Set price scale range for RSI (0-100)
        chart.priceScale('right').applyOptions({
            autoScale: false,
            scaleMargins: {
                top: 0.05,
                bottom: 0.05,
            },
        });

        chart.timeScale().fitContent();
    }

    /**
     * Update MACD indicator pane
     */
    function updateMacdPane(data) {
        const containerId = 'tv-macd-container';
        const container = document.getElementById(containerId);
        if (!container) return;

        // Show the container
        container.style.display = 'block';

        let chart = charts[containerId];
        if (!chart) {
            chart = init(containerId, true);
            if (!chart) return;
        }

        // Clear existing series
        const chartSeries = series[containerId] || {};
        Object.keys(chartSeries).forEach(key => {
            try {
                chart.removeSeries(chartSeries[key]);
            } catch (e) {}
        });
        series[containerId] = {};

        // Add MACD histogram
        if (data.macdHist && data.macdHist.length > 0) {
            const histSeries = chart.addHistogramSeries({
                color: '#26a69a',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(4),
                },
            });
            histSeries.setData(data.macdHist);
            series[containerId].macdHist = histSeries;
        }

        // Add MACD line
        if (data.macd && data.macd.length > 0) {
            const macdSeries = chart.addLineSeries({
                color: lineColors.macd,
                lineWidth: 2,
                title: 'MACD',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(4),
                },
            });
            macdSeries.setData(data.macd);
            series[containerId].macd = macdSeries;
        }

        // Add Signal line
        if (data.macdSignal && data.macdSignal.length > 0) {
            const signalSeries = chart.addLineSeries({
                color: lineColors.macdSignal,
                lineWidth: 2,
                title: 'Signal',
                priceFormat: {
                    type: 'custom',
                    formatter: (price) => price.toFixed(4),
                },
            });
            signalSeries.setData(data.macdSignal);
            series[containerId].macdSignal = signalSeries;
        }

        // Add zero line
        if (data.macd && data.macd.length > 0) {
            const zeroLineData = data.macd.map(d => ({ time: d.time, value: 0 }));
            const zeroSeries = chart.addLineSeries({
                color: 'rgba(128, 128, 128, 0.5)',
                lineWidth: 1,
                lineStyle: 1,
                crosshairMarkerVisible: false,
                lastValueVisible: false,
                priceLineVisible: false,
            });
            zeroSeries.setData(zeroLineData);
        }

        chart.timeScale().fitContent();
    }

    /**
     * Update OBV indicator pane
     */
    function updateObvPane(obvData) {
        const containerId = 'tv-obv-container';
        const container = document.getElementById(containerId);
        if (!container) return;

        // Show the container
        container.style.display = 'block';

        let chart = charts[containerId];
        if (!chart) {
            chart = init(containerId, true);
            if (!chart) return;
        }

        // Clear existing series
        const chartSeries = series[containerId] || {};
        Object.keys(chartSeries).forEach(key => {
            try {
                chart.removeSeries(chartSeries[key]);
            } catch (e) {}
        });
        series[containerId] = {};

        // Add OBV line
        const obvSeries = chart.addLineSeries({
            color: lineColors.obv,
            lineWidth: 2,
            title: 'OBV',
            priceFormat: {
                type: 'volume',
            },
        });
        obvSeries.setData(obvData);
        series[containerId].obv = obvSeries;

        // Add zero line
        const zeroLineData = obvData.map(d => ({ time: d.time, value: 0 }));
        const zeroSeries = chart.addLineSeries({
            color: 'rgba(128, 128, 128, 0.3)',
            lineWidth: 1,
            lineStyle: 1,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });
        zeroSeries.setData(zeroLineData);

        chart.timeScale().fitContent();
    }

    /**
     * Hide an indicator pane
     */
    function hideIndicatorPane(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.style.display = 'none';
        }
        // Destroy the chart to free resources
        if (charts[containerId]) {
            destroy(containerId);
        }
    }

    /**
     * Apply theme to chart
     */
    function applyTheme(containerId, themeName) {
        const chart = charts[containerId];
        if (!chart) return;

        const themeConfig = themes[themeName] || themes.dark;
        chart.applyOptions(themeConfig);
    }

    /**
     * Apply theme to all charts
     */
    function applyThemeToAll(themeName) {
        Object.keys(charts).forEach(containerId => {
            const isIndicator = containerId.includes('rsi') ||
                               containerId.includes('macd') ||
                               containerId.includes('obv');
            const themeConfig = isIndicator ? getIndicatorPaneConfig(themeName) : themes[themeName];
            if (charts[containerId]) {
                charts[containerId].applyOptions(themeConfig);
            }
        });
    }

    /**
     * Destroy a chart instance
     */
    function destroy(containerId) {
        const chart = charts[containerId];
        if (chart) {
            if (chart._resizeObserver) {
                chart._resizeObserver.disconnect();
            }
            chart.remove();
            delete charts[containerId];
            delete series[containerId];
        }
    }

    /**
     * Destroy all chart instances
     */
    function destroyAll() {
        Object.keys(charts).forEach(containerId => {
            destroy(containerId);
        });
    }

    /**
     * Watch for theme changes
     */
    function setupThemeObserver() {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                if (mutation.attributeName === 'class') {
                    const theme = getCurrentTheme();
                    applyThemeToAll(theme);
                }
            });
        });

        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['class']
        });
    }

    // Initialize theme observer when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupThemeObserver);
    } else {
        setupThemeObserver();
    }

    /**
     * Toggle fullscreen mode for the chart
     */
    function toggleFullscreen() {
        const wrapper = document.getElementById('chart-fullscreen-wrapper');
        if (!wrapper) return;

        const isFullscreen = wrapper.classList.contains('is-fullscreen');

        if (isFullscreen) {
            exitFullscreen();
        } else {
            enterFullscreen();
        }
    }

    /**
     * Enter fullscreen mode
     */
    function enterFullscreen() {
        const wrapper = document.getElementById('chart-fullscreen-wrapper');
        if (!wrapper) return;

        // Add fullscreen class
        wrapper.classList.add('is-fullscreen');
        document.body.classList.add('chart-fullscreen-active');

        // Update symbol display in fullscreen header
        const symbolDisplay = document.getElementById('current-symbol-display');
        const fullscreenSymbol = document.getElementById('fullscreen-symbol-display');
        if (symbolDisplay && fullscreenSymbol) {
            fullscreenSymbol.textContent = symbolDisplay.textContent || '';
        }

        // Resize all charts after a short delay
        setTimeout(() => {
            resizeAllCharts();
        }, 100);

        // Try native fullscreen API
        if (wrapper.requestFullscreen) {
            wrapper.requestFullscreen().catch(err => {
                // Fullscreen API failed, but CSS fullscreen still works
                console.log('[TradingView] Native fullscreen not available, using CSS fullscreen');
            });
        }
    }

    /**
     * Exit fullscreen mode
     */
    function exitFullscreen() {
        const wrapper = document.getElementById('chart-fullscreen-wrapper');
        if (!wrapper) return;

        // Remove fullscreen class
        wrapper.classList.remove('is-fullscreen');
        document.body.classList.remove('chart-fullscreen-active');

        // Exit native fullscreen if active
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(err => {});
        }

        // Resize all charts after a short delay
        setTimeout(() => {
            resizeAllCharts();
        }, 100);
    }

    /**
     * Resize all active charts
     */
    function resizeAllCharts() {
        Object.keys(charts).forEach(containerId => {
            const container = document.getElementById(containerId);
            const chart = charts[containerId];
            if (container && chart) {
                const { width, height } = container.getBoundingClientRect();
                if (width > 0 && height > 0) {
                    chart.resize(width, height);
                    chart.timeScale().fitContent();
                }
            }
        });
    }

    /**
     * Setup fullscreen button handlers
     */
    function setupFullscreenHandlers() {
        // Main fullscreen button
        document.addEventListener('click', function(e) {
            if (e.target.id === 'chart-fullscreen-btn' || e.target.closest('#chart-fullscreen-btn')) {
                toggleFullscreen();
            }
            if (e.target.id === 'exit-fullscreen-btn' || e.target.closest('#exit-fullscreen-btn')) {
                exitFullscreen();
            }
        });

        // ESC key to exit fullscreen
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const wrapper = document.getElementById('chart-fullscreen-wrapper');
                if (wrapper && wrapper.classList.contains('is-fullscreen')) {
                    exitFullscreen();
                }
            }
        });

        // Handle native fullscreen change events
        document.addEventListener('fullscreenchange', function() {
            const wrapper = document.getElementById('chart-fullscreen-wrapper');
            if (!document.fullscreenElement && wrapper && wrapper.classList.contains('is-fullscreen')) {
                // User exited fullscreen via browser controls
                wrapper.classList.remove('is-fullscreen');
                document.body.classList.remove('chart-fullscreen-active');
                setTimeout(resizeAllCharts, 100);
            }
        });
    }

    // Initialize fullscreen handlers when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupFullscreenHandlers);
    } else {
        setupFullscreenHandlers();
    }

    // Export the manager globally
    window.TradingViewChartManager = {
        init: init,
        update: update,
        applyTheme: applyTheme,
        applyThemeToAll: applyThemeToAll,
        destroy: destroy,
        destroyAll: destroyAll,
        getCurrentTheme: getCurrentTheme,
        hideIndicatorPane: hideIndicatorPane,
        toggleFullscreen: toggleFullscreen,
        enterFullscreen: enterFullscreen,
        exitFullscreen: exitFullscreen,
    };

})();

/**
 * TradingView Lightweight Charts Manager
 * Handles chart initialization, updates, and theme switching
 * Supports multiple panes for RSI, MACD, and OBV indicators
 * Features: OHLC legend, indicator value labels, crosshair sync, live bar updates
 */
(function() {
    'use strict';

    // Chart instances storage
    const charts = {};
    const series = {};

    // Store last data for crosshair lookups and live updates
    const chartData = {};

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
     * Format a number with appropriate precision for price display
     */
    function formatPrice(value) {
        if (value == null || isNaN(value)) return '-';
        if (Math.abs(value) >= 1000) return value.toFixed(2);
        if (Math.abs(value) >= 1) return value.toFixed(2);
        return value.toFixed(4);
    }

    /**
     * Format volume with K/M/B suffixes
     */
    function formatVolume(value) {
        if (value == null || isNaN(value)) return '-';
        const abs = Math.abs(value);
        if (abs >= 1e9) return (value / 1e9).toFixed(2) + 'B';
        if (abs >= 1e6) return (value / 1e6).toFixed(2) + 'M';
        if (abs >= 1e3) return (value / 1e3).toFixed(1) + 'K';
        return value.toFixed(0);
    }

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

    // =========================================================================
    // OHLC Legend + Indicator Labels (crosshair-driven)
    // =========================================================================

    /**
     * Update the OHLC legend bar with values from the crosshair position or latest bar
     */
    function updateOhlcLegend(param, data) {
        const elOpen = document.getElementById('ohlc-open');
        const elHigh = document.getElementById('ohlc-high');
        const elLow = document.getElementById('ohlc-low');
        const elClose = document.getElementById('ohlc-close');
        const elChange = document.getElementById('ohlc-change');
        const elVolume = document.getElementById('ohlc-volume');
        if (!elOpen) return; // legend not in DOM

        let bar = null;
        let vol = null;

        // Try to get data from crosshair position
        if (param && param.seriesData) {
            const mainSeries = series['tv-chart-container'];
            if (mainSeries && mainSeries.candlestick) {
                const candleData = param.seriesData.get(mainSeries.candlestick);
                if (candleData) {
                    bar = candleData;
                }
            }
            if (mainSeries && mainSeries.volume) {
                const volData = param.seriesData.get(mainSeries.volume);
                if (volData) {
                    vol = volData.value;
                }
            }
        }

        // Fall back to latest bar if crosshair is off chart
        if (!bar && data && data.candlestick && data.candlestick.length > 0) {
            bar = data.candlestick[data.candlestick.length - 1];
            if (data.volume && data.volume.length > 0) {
                vol = data.volume[data.volume.length - 1].value;
            }
        }

        if (!bar) return;

        const o = bar.open, h = bar.high, l = bar.low, c = bar.close;
        const isUp = c >= o;
        const colorClass = isUp ? 'ohlc-up' : 'ohlc-down';

        elOpen.textContent = formatPrice(o);
        elOpen.className = 'ohlc-value ' + colorClass;
        elHigh.textContent = formatPrice(h);
        elHigh.className = 'ohlc-value ' + colorClass;
        elLow.textContent = formatPrice(l);
        elLow.className = 'ohlc-value ' + colorClass;
        elClose.textContent = formatPrice(c);
        elClose.className = 'ohlc-value ' + colorClass;

        // Calculate change from previous bar's close
        let prevClose = null;
        if (data && data.candlestick && bar.time) {
            const candles = data.candlestick;
            for (let i = 1; i < candles.length; i++) {
                if (candles[i].time === bar.time) {
                    prevClose = candles[i - 1].close;
                    break;
                }
            }
        }
        if (prevClose != null && prevClose !== 0) {
            const change = c - prevClose;
            const changePct = (change / prevClose) * 100;
            const sign = change >= 0 ? '+' : '';
            elChange.textContent = sign + formatPrice(change) + ' (' + sign + changePct.toFixed(2) + '%)';
            elChange.className = 'ohlc-change ' + (change >= 0 ? 'ohlc-up' : 'ohlc-down');
        } else {
            elChange.textContent = '';
        }

        elVolume.textContent = vol != null ? formatVolume(vol) : '-';
    }

    /**
     * Update indicator overlay legend (SMA, EMA, BB values at crosshair position)
     */
    function updateIndicatorLegend(param, data) {
        const el = document.getElementById('chart-indicator-legend');
        if (!el) return;

        const mainSeries = series['tv-chart-container'];
        if (!mainSeries) { el.innerHTML = ''; return; }

        const labels = [];

        // Map of series key -> display config
        const overlayIndicators = [
            { key: 'sma20', name: 'SMA 20', color: lineColors.sma20 },
            { key: 'sma50', name: 'SMA 50', color: lineColors.sma50 },
            { key: 'ema12', name: 'EMA 12', color: lineColors.ema12 },
            { key: 'ema26', name: 'EMA 26', color: lineColors.ema26 },
            { key: 'bbUpper', name: 'BB Upper', color: lineColors.bbUpper },
            { key: 'bbLower', name: 'BB Lower', color: lineColors.bbLower },
        ];

        overlayIndicators.forEach(ind => {
            const s = mainSeries[ind.key];
            if (!s) return;

            let value = null;
            if (param && param.seriesData) {
                const d = param.seriesData.get(s);
                if (d) value = d.value;
            }
            // Fallback to last data point
            if (value == null && data && data[ind.key] && data[ind.key].length > 0) {
                value = data[ind.key][data[ind.key].length - 1].value;
            }
            if (value != null) {
                labels.push(
                    '<span class="indicator-label" style="color:' + ind.color + '">' +
                    ind.name + ' <b>' + formatPrice(value) + '</b></span>'
                );
            }
        });

        el.innerHTML = labels.join('');
    }

    /**
     * Update a specific indicator pane legend (RSI, MACD, OBV)
     */
    function updatePaneLegend(paneId, legendId, indicators, param) {
        const el = document.getElementById(legendId);
        if (!el) return;

        const paneSeries = series[paneId];
        if (!paneSeries) { el.innerHTML = ''; return; }

        const labels = [];
        indicators.forEach(ind => {
            const s = paneSeries[ind.key];
            if (!s) return;

            let value = null;
            if (param && param.seriesData) {
                const d = param.seriesData.get(s);
                if (d) value = d.value != null ? d.value : null;
            }

            if (value != null) {
                let formatted;
                if (ind.formatVolume) {
                    formatted = formatVolume(value);
                } else if (ind.precision != null) {
                    formatted = value.toFixed(ind.precision);
                } else {
                    formatted = formatPrice(value);
                }
                labels.push(
                    '<span class="indicator-label" style="color:' + ind.color + '">' +
                    ind.name + ' <b>' + formatted + '</b></span>'
                );
            }
        });

        el.innerHTML = labels.join('');
    }

    /**
     * Subscribe crosshair move on the main chart to update legends
     */
    function setupCrosshairLegend(containerId, data) {
        const chart = charts[containerId];
        if (!chart) return;

        chart.subscribeCrosshairMove(function(param) {
            updateOhlcLegend(param, data);
            updateIndicatorLegend(param, data);
        });

        // Initialize with latest bar values
        updateOhlcLegend(null, data);
        updateIndicatorLegend(null, data);
    }

    /**
     * Subscribe crosshair on indicator pane charts for their legends
     */
    function setupPaneCrosshairLegend(paneId, legendId, indicators) {
        const chart = charts[paneId];
        if (!chart) return;

        chart.subscribeCrosshairMove(function(param) {
            updatePaneLegend(paneId, legendId, indicators, param);
        });

        // Initialize with no crosshair (will show nothing until hover)
        updatePaneLegend(paneId, legendId, indicators, null);
    }

    // =========================================================================
    // Main chart update
    // =========================================================================

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

        // Store data reference for crosshair lookups and live updates
        chartData[containerId] = data;

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

        // Setup OHLC legend + indicator labels via crosshair
        setupCrosshairLegend(containerId, data);

        // Handle indicator panes
        const indicatorPanes = [];

        // RSI Pane
        if (data.rsi && data.rsi.length > 0) {
            updateRsiPane(data.rsi);
            indicatorPanes.push('tv-rsi-container');
        } else {
            hideIndicatorPane('tv-rsi-container');
            hidePaneLegend('rsi-pane-legend');
        }

        // MACD Pane
        if ((data.macd && data.macd.length > 0) || (data.macdHist && data.macdHist.length > 0)) {
            updateMacdPane(data);
            indicatorPanes.push('tv-macd-container');
        } else {
            hideIndicatorPane('tv-macd-container');
            hidePaneLegend('macd-pane-legend');
        }

        // OBV Pane
        if (data.obv && data.obv.length > 0) {
            updateObvPane(data.obv);
            indicatorPanes.push('tv-obv-container');
        } else {
            hideIndicatorPane('tv-obv-container');
            hidePaneLegend('obv-pane-legend');
        }

        // Sync time scales
        if (indicatorPanes.length > 0) {
            syncTimeScales(containerId, indicatorPanes);
        }
    }

    /**
     * Hide a pane legend
     */
    function hidePaneLegend(legendId) {
        const el = document.getElementById(legendId);
        if (el) el.innerHTML = '';
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

        // Setup RSI pane legend
        setupPaneCrosshairLegend(containerId, 'rsi-pane-legend', [
            { key: 'rsi', name: 'RSI (14)', color: lineColors.rsi, precision: 1 },
        ]);
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

        // Setup MACD pane legend
        setupPaneCrosshairLegend(containerId, 'macd-pane-legend', [
            { key: 'macd', name: 'MACD', color: lineColors.macd, precision: 4 },
            { key: 'macdSignal', name: 'Signal', color: lineColors.macdSignal, precision: 4 },
            { key: 'macdHist', name: 'Hist', color: '#26a69a', precision: 4 },
        ]);
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

        // Setup OBV pane legend
        setupPaneCrosshairLegend(containerId, 'obv-pane-legend', [
            { key: 'obv', name: 'OBV', color: lineColors.obv, formatVolume: true },
        ]);
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

    // =========================================================================
    // Live bar update (Phase 3)
    // =========================================================================

    /**
     * Update the last bar on the chart with a new price (for live updates).
     * Uses lightweight-charts' native .update() for efficient in-place updates.
     */
    function updateLastBar(containerId, price, timestamp) {
        const mainSeries = series[containerId];
        if (!mainSeries || !mainSeries.candlestick) return;

        const data = chartData[containerId];
        if (!data || !data.candlestick || data.candlestick.length === 0) return;

        const lastBar = data.candlestick[data.candlestick.length - 1];

        // Update the last bar's close and adjust high/low
        const updatedBar = {
            time: lastBar.time,
            open: lastBar.open,
            high: Math.max(lastBar.high, price),
            low: Math.min(lastBar.low, price),
            close: price,
        };

        // Update in our stored data
        data.candlestick[data.candlestick.length - 1] = updatedBar;

        // Update the series (lightweight-charts handles in-place update for same time)
        mainSeries.candlestick.update(updatedBar);

        // Update the OHLC legend with new values
        updateOhlcLegend(null, data);
        updateIndicatorLegend(null, data);
    }

    // =========================================================================
    // Theme, fullscreen, destroy
    // =========================================================================

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
            delete chartData[containerId];
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
        updateLastBar: updateLastBar,
        applyTheme: applyTheme,
        applyThemeToAll: applyThemeToAll,
        destroy: destroy,
        destroyAll: destroyAll,
        getCurrentTheme: getCurrentTheme,
        hideIndicatorPane: hideIndicatorPane,
        toggleFullscreen: toggleFullscreen,
        enterFullscreen: enterFullscreen,
        exitFullscreen: exitFullscreen,
        formatVolume: formatVolume,
        formatPrice: formatPrice,
    };

})();

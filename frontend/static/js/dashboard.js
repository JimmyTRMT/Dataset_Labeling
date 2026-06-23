// Analytics dashboard: doughnut chart of label counts via Chart.js.
// Reads its data from #chart-data (JSON) and #datasetChart (canvas),
// both rendered server-side. Re-renders on Light/Dark toggle.

(function () {
    var canvas = document.getElementById("datasetChart");
    var dataNode = document.getElementById("chart-data");
    if (!canvas || !dataNode || typeof window.Chart === "undefined") return;

    var rawData;
    try {
        rawData = JSON.parse(dataNode.textContent || "[]");
    } catch (e) {
        return;
    }
    if (!Array.isArray(rawData) || rawData.length === 0) return;

    var datasetType = canvas.getAttribute("data-dataset-type") || "";

    // Colour-blind friendly palette. Cycles past 8 labels (no project hits that).
    var PALETTE = [
        "#60a5fa", "#34d399", "#fbbf24", "#f87171",
        "#a78bfa", "#22d3ee", "#fb923c", "#f472b6"
    ];

    function paletteAt(index) {
        return PALETTE[index % PALETTE.length];
    }

    var labels = rawData.map(function (item) { return item.label; });
    var counts = rawData.map(function (item) { return item.count; });
    var colors = rawData.map(function (_item, idx) { return paletteAt(idx); });

    // Sync the left-hand list dots with the chart palette.
    document.querySelectorAll("[data-legend-dot]").forEach(function (dot) {
        var idx = parseInt(dot.getAttribute("data-index"), 10);
        if (!isNaN(idx)) {
            dot.style.backgroundColor = paletteAt(idx);
        }
    });

    function isDark() {
        return document.documentElement.classList.contains("dark");
    }

    function themeTokens() {
        return isDark()
            ? { text: "#e2e8f0", border: "#1e293b", tooltipBg: "#0f172a" }
            : { text: "#334155", border: "#ffffff", tooltipBg: "#0f172a" };
    }

    var total = counts.reduce(function (sum, n) { return sum + n; }, 0);

    function buildConfig() {
        var tokens = themeTokens();
        return {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colors,
                    borderColor: tokens.border,
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                // false is required, the parent <div> sets a fixed height.
                // Without it Chart.js grows the canvas unbounded.
                maintainAspectRatio: false,
                cutout: "62%",
                animation: { duration: 600 },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: tokens.text,
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 12,
                            boxWidth: 8
                        }
                    },
                    tooltip: {
                        backgroundColor: tokens.tooltipBg,
                        titleColor: "#f8fafc",
                        bodyColor: "#e2e8f0",
                        borderColor: "rgba(148, 163, 184, 0.25)",
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function (ctx) {
                                var value = ctx.parsed || 0;
                                var pct = total > 0 ? (value * 100 / total).toFixed(1) : "0.0";
                                var noun = value === 1 ? "image" : "images";
                                return " " + ctx.label + ": " + value + " " + noun + " (" + pct + "%)";
                            }
                        }
                    },
                    title: {
                        display: !!datasetType,
                        text: datasetType ? datasetType + " - label distribution" : "",
                        color: tokens.text,
                        font: { size: 13, weight: "600" },
                        padding: { bottom: 12 }
                    }
                }
            }
        };
    }

    var chart = new window.Chart(canvas.getContext("2d"), buildConfig());

    // Watch <html> class instead of the toggle button so programmatic
    // theme changes (or theme.js bootstrap) also trigger a re-render.
    var observer = new MutationObserver(function () {
        var tokens = themeTokens();
        chart.options.plugins.legend.labels.color = tokens.text;
        chart.options.plugins.title.color = tokens.text;
        chart.data.datasets[0].borderColor = tokens.border;
        chart.update("none");
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
})();

// Renders the dataset dashboard doughnut chart with Chart.js.
//
// Data flows in via two safe channels rendered server-side:
//   - <script id="chart-data" type="application/json">[{label, count}, ...]</script>
//   - <canvas id="datasetChart" data-dataset-type="...">
//
// Colors come from a fixed soft palette; the chart re-renders when the
// user toggles Light/Dark so axis/legend text stays readable on both.

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

    // Soft, professional palette. Hand-picked so adjacent slices read well
    // and the set is colour-blind friendly. Cycles when there are more
    // labels than colours - acceptable since each project has <= 5 labels.
    var PALETTE = [
        "#60a5fa", // blue-400
        "#34d399", // emerald-400
        "#fbbf24", // amber-400
        "#f87171", // red-400
        "#a78bfa", // violet-400
        "#22d3ee", // cyan-400
        "#fb923c", // orange-400
        "#f472b6"  // pink-400
    ];

    function paletteAt(index) {
        return PALETTE[index % PALETTE.length];
    }

    var labels = rawData.map(function (item) { return item.label; });
    var counts = rawData.map(function (item) { return item.count; });
    var colors = rawData.map(function (_item, idx) { return paletteAt(idx); });

    // Mirror the dot colours in the left-hand list so the legend matches
    // the chart exactly. Falls back silently if the list isn't rendered.
    document.querySelectorAll("[data-legend-dot]").forEach(function (dot) {
        var idx = parseInt(dot.getAttribute("data-index"), 10);
        if (!isNaN(idx)) {
            dot.style.backgroundColor = paletteAt(idx);
        }
    });

    function isDark() {
        return document.documentElement.classList.contains("dark");
    }

    // Theme-aware text/border colours. Chart.js reads these once per
    // render, so a re-render is needed on theme switch (see below).
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

    // Re-render on theme toggle so legend/title text contrasts correctly.
    // We watch the `class` attribute on <html> rather than listening on
    // the button so we still react if the theme is changed programmatically.
    var observer = new MutationObserver(function () {
        var tokens = themeTokens();
        chart.options.plugins.legend.labels.color = tokens.text;
        chart.options.plugins.title.color = tokens.text;
        chart.data.datasets[0].borderColor = tokens.border;
        chart.update("none");
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
})();

// Read server-rendered JSON datasets
const labels = JSON.parse(document.getElementById("chart-labels-data").textContent);
const values = JSON.parse(document.getElementById("chart-values-data").textContent);
const dayLabels = JSON.parse(document.getElementById("day-labels-data").textContent);
const dayValues = JSON.parse(document.getElementById("day-values-data").textContent);
const cssVars = getComputedStyle(document.documentElement);
const chartPalette = [
    cssVars.getPropertyValue("--bs-success").trim(),
    cssVars.getPropertyValue("--bs-danger").trim(),
    cssVars.getPropertyValue("--bs-secondary").trim(),
];

// Label distribution
const context = document.getElementById("labelsPieChart");
if (context) {
    new Chart(context, {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: chartPalette,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom",
                },
            },
        },
    });
}

// Labeling pace by day
const dayContext = document.getElementById("labelsPerDayChart");
if (dayContext) {
    new Chart(dayContext, {
        type: "bar",
        data: {
            labels: dayLabels,
            datasets: [{
                label: "Labels / day",
                data: dayValues,
                backgroundColor: cssVars.getPropertyValue("--bs-primary").trim(),
                borderRadius: 6,
            }],
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                    },
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
            },
        },
    });
}

const moodCanvas = document.getElementById('moodChart');
const temperatureCanvas = document.getElementById('temperatureChart');
const moodPositiveValue = document.getElementById('mood-positive-value');
const moodNeutralValue = document.getElementById('mood-neutral-value');
const moodNegativeValue = document.getElementById('mood-negative-value');
const co2Value = document.getElementById('co2-value');
const co2ProgressBar = document.getElementById('co2-progress-bar');
const humidityValue = document.getElementById('humidity-value');
const averageTemperatureValue = document.getElementById('average-temperature-value');

let moodChartInstance = null;
let tempChart = null;
let isDashboardRefreshRunning = false;
let dashboardRefreshIntervalId = null;

if (typeof moodChartData !== 'undefined' && moodCanvas) {
    moodChartInstance = new Chart(moodCanvas, {
        type: 'bar',
        data: {
            labels: Array.isArray(moodChartData.labels) ? moodChartData.labels : ['Positiv', 'Neutral', 'Negativ'],
            datasets: [{
                data: Array.isArray(moodChartData.values) ? moodChartData.values : [0, 0, 0],
                backgroundColor: ['#4CAF50', '#FFC107', '#F44336'],
                borderRadius: 10
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

if (
    typeof temperatureChartData !== 'undefined' &&
    temperatureChartData.tag &&
    temperatureCanvas
) {
    tempChart = new Chart(temperatureCanvas, {
        type: 'line',
        data: {
            labels: Array.isArray(temperatureChartData.tag.labels) ? temperatureChartData.tag.labels : [],
            datasets: [{
                data: Array.isArray(temperatureChartData.tag.values) ? temperatureChartData.tag.values : [],
                borderColor: '#ff4d4d',
                backgroundColor: 'rgba(255, 77, 77, 0.2)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

const timeButtons = document.querySelectorAll('.time-box');

timeButtons.forEach(button => {
    button.addEventListener('click', () => {
        timeButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        const selectedRange = button.dataset.range;
        updateTemperatureChart(selectedRange);
    });
});

function updateTemperatureChart(timeRange) {
    if (!tempChart) return;
    if (typeof temperatureChartData === 'undefined') return;
    if (!temperatureChartData[timeRange]) return;

    const rangeData = temperatureChartData[timeRange];

    tempChart.data.labels = Array.isArray(rangeData.labels) ? rangeData.labels : [];
    tempChart.data.datasets[0].data = Array.isArray(rangeData.values) ? rangeData.values : [];
    tempChart.update();
}

function formatMetricValue(value, decimals) {
    return Number(value || 0).toFixed(decimals).replace(/\.?0+$/, '');
}

function applyDashboardData(dashboardData) {
    if (!dashboardData || typeof dashboardData !== 'object') return;

    const moodValues = Array.isArray(dashboardData?.moodData?.values)
        ? dashboardData.moodData.values
        : [0, 0, 0];

    if (moodChartInstance) {
        moodChartInstance.data.datasets[0].data = moodValues;
        moodChartInstance.update();
    }

    if (moodPositiveValue) moodPositiveValue.textContent = String(moodValues[0] ?? 0);
    if (moodNeutralValue) moodNeutralValue.textContent = String(moodValues[1] ?? 0);
    if (moodNegativeValue) moodNegativeValue.textContent = String(moodValues[2] ?? 0);

    const summary = dashboardData.summary || {};
    const co2 = Number(summary.currentCo2 || 0);
    const humidity = Number(summary.currentHumidity || 0);
    const averageTemperature = Number(summary.averageTemperature || 0);
    const co2BarWidth = Number(summary.co2BarWidth || 0);

    if (co2Value) co2Value.textContent = `${co2} ppm`;
    if (co2ProgressBar) co2ProgressBar.style.width = `${Math.min(100, Math.max(0, co2BarWidth))}%`;
    if (humidityValue) humidityValue.textContent = `${formatMetricValue(humidity, 2)}%`;
    if (averageTemperatureValue) averageTemperatureValue.textContent = `${formatMetricValue(averageTemperature, 1)}°C`;

    const temperatureValues = dashboardData.temperatureData;
    if (tempChart && temperatureValues) {
        tempChart.data.labels = Array.isArray(temperatureValues.labels) ? temperatureValues.labels : [];
        tempChart.data.datasets[0].data = Array.isArray(temperatureValues.values) ? temperatureValues.values : [];
        tempChart.update();
    }
}

async function refreshDashboardData() {
    if (typeof dashboardConfig === 'undefined') return;
    if (document.hidden) return;
    if (isDashboardRefreshRunning) return;

    isDashboardRefreshRunning = true;

    try {
        const url = `${dashboardConfig.dataUrl}?location_id=${encodeURIComponent(dashboardConfig.locationId)}&range=${encodeURIComponent(dashboardConfig.range)}`;
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            console.error('Dashboard refresh failed with status', response.status);
            return;
        }

        const dashboardData = await response.json();
        applyDashboardData(dashboardData);
    } catch (error) {
        console.error('Dashboard refresh failed', error);
    } finally {
        isDashboardRefreshRunning = false;
    }
}

if (typeof dashboardConfig !== 'undefined' && dashboardConfig.locationId > 0) {
    const refreshIntervalMs = Number(dashboardConfig.refreshIntervalMs);
    if (!Number.isFinite(refreshIntervalMs) || refreshIntervalMs <= 0) {
        console.error('Invalid dashboard refresh interval configuration');
    } else {
        const startDashboardRefresh = () => {
            if (dashboardRefreshIntervalId !== null) return;
            refreshDashboardData();
            dashboardRefreshIntervalId = window.setInterval(refreshDashboardData, refreshIntervalMs);
        };

        const stopDashboardRefresh = () => {
            if (dashboardRefreshIntervalId === null) return;
            window.clearInterval(dashboardRefreshIntervalId);
            dashboardRefreshIntervalId = null;
        };

        if (!document.hidden) {
            startDashboardRefresh();
        }

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stopDashboardRefresh();
                return;
            }

            startDashboardRefresh();
        });
    }
}
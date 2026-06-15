const moodCanvas = document.getElementById('moodChart');
const temperatureCanvas = document.getElementById('temperatureChart');

let moodChartInstance = null;
let tempChart = null;

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
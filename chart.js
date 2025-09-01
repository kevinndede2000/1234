function renderBarChart(canvasId, labels, data, labelText, bgColor='rgba(54, 162, 235, 0.7)') {
    new Chart(document.getElementById(canvasId), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: labelText,
                data: data,
                backgroundColor: bgColor
            }]
        },
        options: {
            scales: { y: { beginAtZero: true, max: 100 } }
        }
    });
}

// Example usage in template:
// renderBarChart('subjectChart', ['Math','English'], [80,90],'Average Scores');

let analysisData = null;
let metricsData = null;
let airlinesMap = {};
let airportsMap = {};

const chartTheme = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter, sans-serif', color: '#94a3b8', size: 12 },
    margin: { t: 30, r: 20, b: 50, l: 60 },
    xaxis: { gridcolor: '#334155', zerolinecolor: '#334155' },
    yaxis: { gridcolor: '#334155', zerolinecolor: '#334155' },
    colorway: ['#818cf8', '#22c55e', '#f59e0b', '#ef4444', '#0ea5e9', '#a855f7',
               '#f472b6', '#34d399', '#fb923c', '#60a5fa']
};

const chartConfig = { responsive: true, displayModeBar: false };


document.addEventListener('DOMContentLoaded', function() {
    setupNavigation();
    loadDashboardData();
});

function setupNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            const sectionId = this.getAttribute('data-section');
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
        });
    });
}

async function loadDashboardData() {
    try {
        const [analysisRes, metricsRes] = await Promise.all([
            fetch('/api/analysis'), fetch('/api/metrics')
        ]);

        const analysisJson = await analysisRes.json();
        metricsData = await metricsRes.json();
        analysisData = analysisJson.analysis;
        airlinesMap = analysisJson.airlines;
        airportsMap = analysisJson.airports;

        document.getElementById('loading-screen').classList.add('hidden');

        populateDropdowns();
        renderOverview();
        renderAnalysis();
        renderModelInfo();
        setupFilters();
        setupPredictionForm();

    } catch (error) {
        console.error('Error loading data:', error);
        document.querySelector('.loader p').textContent = 'Error loading data. Please refresh.';
    }
}

function populateDropdowns() {
    const filterAirline = document.getElementById('filter-airline');
    const predAirline = document.getElementById('pred-airline');
    const predOrigin = document.getElementById('pred-origin');
    const predHour = document.getElementById('pred-hour');

    Object.entries(airlinesMap).forEach(([code, name]) => {
        filterAirline.add(new Option(`${name} (${code})`, code));
        predAirline.add(new Option(`${name} (${code})`, code));
    });

    Object.entries(airportsMap).forEach(([code, name]) => {
        predOrigin.add(new Option(`${code} - ${name}`, code));
    });

    for (let h = 5; h <= 23; h++) {
        const period = h < 12 ? 'AM' : 'PM';
        const display = h <= 12 ? h : h - 12;
        const opt = new Option(`${display}:00 ${period}`, h);
        if (h === 12) opt.selected = true;
        predHour.add(opt);
    }
}


function renderOverview() {
    const o = analysisData.overall;
    animateValue('total-flights', 0, o.total_flights, 1000);
    animateValue('total-delayed', 0, o.total_delayed, 1000);
    document.getElementById('delay-rate').textContent = o.delay_rate + '%';
    document.getElementById('avg-delay').textContent = o.avg_delay_minutes;
    renderAirlineOverviewChart();
    renderMonthlyOverviewChart();
}

function animateValue(id, start, end, duration) {
    const el = document.getElementById(id);
    const startTime = performance.now();
    function update(t) {
        const p = Math.min((t - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.floor(start + (end - start) * eased).toLocaleString();
        if (p < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function renderAirlineOverviewChart() {
    const d = analysisData.by_airline;
    Plotly.newPlot('chart-airline-overview', [{
        x: d.delay_rates, y: d.labels,
        type: 'bar', orientation: 'h',
        marker: { color: d.delay_rates.map(r => r < 18 ? '#22c55e' : r < 23 ? '#f59e0b' : '#ef4444') },
        text: d.delay_rates.map(r => r + '%'),
        textposition: 'outside',
        textfont: { color: '#94a3b8', size: 11 },
        hovertemplate: '<b>%{y}</b><br>Delay Rate: %{x}%<extra></extra>'
    }], {
        ...chartTheme,
        xaxis: { ...chartTheme.xaxis, title: 'Delay Rate (%)', range: [0, Math.max(...d.delay_rates) + 5] },
        yaxis: { ...chartTheme.yaxis, automargin: true },
        margin: { t: 10, r: 50, b: 40, l: 150 }
    }, chartConfig);
}

function renderMonthlyOverviewChart() {
    const d = analysisData.by_month;
    Plotly.newPlot('chart-monthly-overview', [{
        x: d.labels, y: d.delay_rates, type: 'bar', name: 'Delay Rate',
        marker: { color: d.delay_rates.map(r => {
            const i = (r - 15) / 20;
            return `rgb(${Math.floor(99+i*140)},${Math.floor(102-i*60)},${Math.floor(241-i*100)})`;
        })},
        hovertemplate: '<b>%{x}</b><br>Delay Rate: %{y}%<extra></extra>'
    }, {
        x: d.labels, y: d.avg_delay, type: 'scatter', mode: 'lines+markers',
        name: 'Avg Delay (min)', yaxis: 'y2',
        line: { color: '#f59e0b', width: 2 }, marker: { size: 6 },
        hovertemplate: '<b>%{x}</b><br>Avg Delay: %{y} min<extra></extra>'
    }], {
        ...chartTheme,
        margin: { t: 10, r: 60, b: 40, l: 50 },
        yaxis: { ...chartTheme.yaxis, title: 'Delay Rate (%)' },
        yaxis2: { title: 'Avg Delay (min)', overlaying: 'y', side: 'right',
                  gridcolor: 'transparent', titlefont: { color: '#f59e0b' },
                  tickfont: { color: '#f59e0b' } },
        legend: { orientation: 'h', y: 1.12, x: 0.5, xanchor: 'center', font: { size: 11 } }
    }, chartConfig);
}


function renderAnalysis() {
    renderAirportChart();
    renderHourlyChart();
    renderDailyChart();
}

function renderAirportChart() {
    const d = analysisData.by_airport;
    Plotly.newPlot('chart-airport', [{
        x: d.labels, y: d.delay_rates, type: 'bar',
        marker: { color: d.delay_rates.map(r => r < 18 ? '#22c55e' : r < 22 ? '#0ea5e9' : r < 26 ? '#f59e0b' : '#ef4444') },
        text: d.delay_rates.map(r => r + '%'), textposition: 'outside',
        textfont: { color: '#94a3b8', size: 10 },
        hovertemplate: '<b>%{x}</b><br>Delay: %{y}%<br>Flights: %{customdata}<extra></extra>',
        customdata: d.total_flights
    }], {
        ...chartTheme,
        margin: { t: 10, r: 20, b: 100, l: 50 },
        xaxis: { ...chartTheme.xaxis, tickangle: -45 },
        yaxis: { ...chartTheme.yaxis, title: 'Delay Rate (%)', range: [0, Math.max(...d.delay_rates) + 5] }
    }, chartConfig);
}

function renderHourlyChart() {
    const d = analysisData.by_hour;
    Plotly.newPlot('chart-hourly', [{
        x: d.labels.map(h => h + ':00'), y: d.delay_rates,
        type: 'scatter', mode: 'lines+markers', fill: 'tozeroy',
        fillcolor: 'rgba(129, 140, 248, 0.1)',
        line: { color: '#818cf8', width: 3, shape: 'spline' },
        marker: { size: 8,
            color: d.delay_rates.map(r => r < 18 ? '#22c55e' : r < 24 ? '#f59e0b' : '#ef4444'),
            line: { color: '#1e293b', width: 2 }
        },
        hovertemplate: '<b>%{x}</b><br>Delay Rate: %{y}%<extra></extra>'
    }], {
        ...chartTheme,
        margin: { t: 10, r: 20, b: 40, l: 50 },
        xaxis: { ...chartTheme.xaxis, title: 'Departure Hour' },
        yaxis: { ...chartTheme.yaxis, title: 'Delay Rate (%)' }
    }, chartConfig);
}

function renderDailyChart() {
    const d = analysisData.by_day;
    const colors = d.labels.map(l => ['Sat','Sun'].includes(l) ? '#f59e0b' : '#818cf8');
    Plotly.newPlot('chart-daily', [{
        x: d.labels, y: d.delay_rates, type: 'bar',
        marker: { color: colors },
        text: d.delay_rates.map(r => r + '%'), textposition: 'outside',
        textfont: { color: '#94a3b8', size: 11 },
        hovertemplate: '<b>%{x}</b><br>Delay Rate: %{y}%<extra></extra>'
    }], {
        ...chartTheme,
        margin: { t: 10, r: 20, b: 40, l: 50 },
        yaxis: { ...chartTheme.yaxis, title: 'Delay Rate (%)', range: [0, Math.max(...d.delay_rates) + 5] }
    }, chartConfig);
}


function setupFilters() {
    document.getElementById('filter-airline').addEventListener('change', function() {
        const code = this.value;
        const detail = document.getElementById('airline-detail');
        if (code === 'all') { detail.style.display = 'none'; return; }

        fetch(`/api/airline-analysis/${code}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) return;
                detail.style.display = 'block';
                document.getElementById('airline-detail-title').innerHTML =
                    `<i class="fas fa-info-circle"></i> ${data.airline_name} — Detailed Analysis`;
                document.getElementById('airline-stats').innerHTML = `
                    <div class="airline-stat-item"><div class="value">${data.total_flights.toLocaleString()}</div><div class="label">Total Flights</div></div>
                    <div class="airline-stat-item"><div class="value">${data.delayed_flights.toLocaleString()}</div><div class="label">Delayed</div></div>
                    <div class="airline-stat-item"><div class="value">${data.delay_rate}%</div><div class="label">Delay Rate</div></div>
                    <div class="airline-stat-item"><div class="value">${data.avg_delay} min</div><div class="label">Avg Delay</div></div>`;

                Plotly.newPlot('chart-airline-monthly', [{
                    x: data.monthly.labels, y: data.monthly.delay_rates,
                    type: 'bar', marker: { color: '#818cf8' },
                    text: data.monthly.delay_rates.map(r => r + '%'),
                    textposition: 'outside', textfont: { color: '#94a3b8', size: 11 },
                    hovertemplate: '<b>%{x}</b><br>Delay Rate: %{y}%<extra></extra>'
                }], {
                    ...chartTheme, margin: { t: 10, r: 20, b: 40, l: 50 },
                    yaxis: { ...chartTheme.yaxis, title: 'Delay Rate (%)',
                        range: [0, Math.max(...data.monthly.delay_rates) + 8] }
                }, chartConfig);

                detail.scrollIntoView({ behavior: 'smooth' });
            });
    });
}


function setupPredictionForm() {
    document.getElementById('prediction-form').addEventListener('submit', function(e) {
        e.preventDefault();
        makePrediction();
    });
}

async function makePrediction() {
    const btn = document.getElementById('btn-predict');
    btn.classList.add('loading');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Predicting...';

    try {
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                airline: document.getElementById('pred-airline').value,
                origin: document.getElementById('pred-origin').value,
                month: document.getElementById('pred-month').value,
                day_of_week: document.getElementById('pred-day').value,
                dep_hour: document.getElementById('pred-hour').value,
                distance: document.getElementById('pred-distance').value
            })
        });
        const result = await res.json();
        if (result.error) { alert('Error: ' + result.error); return; }
        displayResult(result);
    } catch (err) {
        alert('Prediction failed. Try again.');
    } finally {
        btn.classList.remove('loading');
        btn.innerHTML = '<i class="fas fa-magic"></i> Predict Delay';
    }
}

function displayResult(result) {
    const card = document.getElementById('prediction-result');
    card.style.display = 'block';

    const badge = document.getElementById('result-badge');
    const icon = document.getElementById('result-icon');
    const text = document.getElementById('result-text');

    if (result.delayed) {
        badge.className = 'result-badge delayed';
        icon.className = 'fas fa-exclamation-triangle';
        text.textContent = 'Likely Delayed';
    } else {
        badge.className = 'result-badge on-time';
        icon.className = 'fas fa-check-circle';
        text.textContent = 'Likely On Time';
    }

    document.getElementById('result-delay-prob').textContent = result.probability_delayed + '%';
    document.getElementById('result-ontime-prob').textContent = result.probability_on_time + '%';
    document.getElementById('result-confidence').textContent = result.confidence + '%';

    const gc = result.probability_delayed > 50 ? '#ef4444' : result.probability_delayed > 30 ? '#f59e0b' : '#22c55e';
    Plotly.newPlot('chart-prediction-gauge', [{
        type: 'indicator', mode: 'gauge+number', value: result.probability_delayed,
        number: { suffix: '%', font: { size: 28, color: '#f1f5f9', family: 'Inter' } },
        gauge: {
            axis: { range: [0, 100], tickcolor: '#334155', tickfont: { color: '#64748b', size: 10 } },
            bar: { color: gc, thickness: 0.75 }, bgcolor: '#1e293b', borderwidth: 0,
            steps: [
                { range: [0, 25], color: 'rgba(34,197,94,0.15)' },
                { range: [25, 50], color: 'rgba(245,158,11,0.15)' },
                { range: [50, 75], color: 'rgba(239,68,68,0.15)' },
                { range: [75, 100], color: 'rgba(239,68,68,0.25)' }
            ],
            threshold: { line: { color: '#f1f5f9', width: 2 }, thickness: 0.75, value: result.probability_delayed }
        }
    }], {
        paper_bgcolor: 'rgba(0,0,0,0)', font: { color: '#94a3b8', family: 'Inter' },
        margin: { t: 25, r: 25, l: 25, b: 10 }, height: 190
    }, chartConfig);

    const months = ['','January','February','March','April','May','June','July','August','September','October','November','December'];
    const days = ['','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
    const h = parseInt(document.getElementById('pred-hour').value);
    const p = h < 12 ? 'AM' : 'PM';
    const dh = h <= 12 ? h : h - 12;

    document.getElementById('result-summary').innerHTML = `
        <strong>Summary:</strong> A <strong>${result.airline_name}</strong> flight
        from <strong>${result.airport_name}</strong> at <strong>${dh}:00 ${p}</strong>
        on a <strong>${days[document.getElementById('pred-day').value]}</strong> in
        <strong>${months[document.getElementById('pred-month').value]}</strong>,
        traveling <strong>${parseInt(document.getElementById('pred-distance').value).toLocaleString()} miles</strong>,
        has a <strong>${result.probability_delayed}%</strong> chance of being delayed.
    `;

    card.scrollIntoView({ behavior: 'smooth' });
}


function renderModelInfo() {
    if (!metricsData) return;

    document.getElementById('model-train-size').textContent = metricsData.train_size.toLocaleString();
    document.getElementById('model-test-size').textContent = metricsData.test_size.toLocaleString();
    document.getElementById('model-features').textContent = metricsData.total_features;

    updateCircle('accuracy', metricsData.accuracy);
    updateCircle('precision', metricsData.precision);
    updateCircle('recall', metricsData.recall);
    updateCircle('f1', metricsData.f1_score);

    renderConfusionMatrix();
    renderFeatureImportance();
    renderDatasetInfo();
}

function updateCircle(metric, value) {
    document.getElementById(`metric-${metric}`).textContent = value + '%';
    const circle = document.getElementById(`metric-${metric}-circle`);
    const offset = 283 - (value / 100) * 283;
    setTimeout(() => {
        circle.style.transition = 'stroke-dashoffset 1.5s ease';
        circle.style.strokeDashoffset = offset;
    }, 300);
}

function renderConfusionMatrix() {
    const cm = metricsData.confusion_matrix;
    Plotly.newPlot('chart-confusion', [{
        z: [[cm[1][1], cm[1][0]], [cm[0][1], cm[0][0]]],
        x: ['Predicted Delayed', 'Predicted On Time'],
        y: ['Actually Delayed', 'Actually On Time'],
        type: 'heatmap',
        colorscale: [[0, '#1e293b'], [0.5, '#4f46e5'], [1, '#818cf8']],
        showscale: false,
        text: [[`TP: ${cm[1][1]}`, `FN: ${cm[1][0]}`], [`FP: ${cm[0][1]}`, `TN: ${cm[0][0]}`]],
        texttemplate: '%{text}', textfont: { color: '#f1f5f9', size: 14 },
        hovertemplate: '%{y} → %{x}<br>Count: %{z}<extra></extra>'
    }], {
        ...chartTheme, margin: { t: 10, r: 20, b: 80, l: 120 },
        xaxis: { ...chartTheme.xaxis, side: 'bottom' },
        yaxis: { ...chartTheme.yaxis, autorange: 'reversed' }
    }, chartConfig);
}

function renderFeatureImportance() {
    const imp = metricsData.feature_importance;
    const sorted = Object.entries(imp)
        .map(([n, v]) => ({ name: n.replace('_ENCODED','').replace(/_/g,' '), value: v, abs: Math.abs(v) }))
        .sort((a, b) => a.abs - b.abs);

    Plotly.newPlot('chart-features', [{
        x: sorted.map(d => d.value), y: sorted.map(d => d.name),
        type: 'bar', orientation: 'h',
        marker: { color: sorted.map(d => d.value >= 0 ? '#ef4444' : '#22c55e') },
        hovertemplate: '<b>%{y}</b><br>Coefficient: %{x:.4f}<extra></extra>'
    }], {
        ...chartTheme, margin: { t: 10, r: 20, b: 40, l: 130 },
        xaxis: { ...chartTheme.xaxis, title: 'Coefficient', zeroline: true,
                 zerolinecolor: '#94a3b8', zerolinewidth: 1 },
        yaxis: { ...chartTheme.yaxis, automargin: true },
        annotations: [{
            x: 0.02, y: 1.05, xref: 'paper', yref: 'paper',
            text: '<span style="color:#ef4444">■</span> Increases delay  <span style="color:#22c55e">■</span> Decreases delay',
            showarrow: false, font: { size: 10, color: '#94a3b8' }
        }]
    }, chartConfig);
}

function renderDatasetInfo() {
    const info = metricsData.dataset_info;
    if (!info) return;

    document.getElementById('dataset-info-content').innerHTML = `
        <div class="dataset-info-item">
            <div class="info-label">Dataset Name</div>
            <div class="info-value">${info.name}</div>
        </div>
        <div class="dataset-info-item">
            <div class="info-label">Source</div>
            <div class="info-value">${info.source}</div>
        </div>
        <div class="dataset-info-item">
            <div class="info-label">Records Used</div>
            <div class="info-value">${info.total_records_used.toLocaleString()}</div>
        </div>
        <div class="dataset-info-item">
            <div class="info-label">Airlines</div>
            <div class="info-value">${info.airlines_count}</div>
        </div>
        <div class="dataset-info-item">
            <div class="info-label">Airports</div>
            <div class="info-value">${info.airports_count}</div>
        </div>
        <div class="dataset-info-item">
            <div class="info-label">Year</div>
            <div class="info-value">2015</div>
        </div>
    `;
}
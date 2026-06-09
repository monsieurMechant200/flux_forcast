// ------------------------------------------
// Live Call Center Dashboard – app.js
// ------------------------------------------

let liveChart = null;
let gaugeChart = null;
let forecastChart = null;  // Pour le graphique de prévisions 24h
let updateTimer = null;
const REFRESH_SEC = 30;                // secondes (données live)
const PREDICTIONS_REFRESH_SEC = 600;   // 10 minutes (prévisions)

// Démarrage
document.addEventListener('DOMContentLoaded', () => {
    updateLiveData();
    loadPredictions();   // première fois
    // Mises à jour périodiques
    setInterval(updateLiveData, REFRESH_SEC * 1000);
    setInterval(loadPredictions, PREDICTIONS_REFRESH_SEC * 1000);
});

// ------------------------------------------
// Fonction principale de mise à jour live (KPI, agents, séries, SLA, jauge)
// ------------------------------------------
async function updateLiveData() {
    if (updateTimer) {
        clearTimeout(updateTimer);
        updateTimer = null;
    }

    try {
        const [kpiRes, seriesRes] = await Promise.all([
            fetch('/api/v1/live/kpis'),
            fetch('/api/v1/live/series'),
        ]);
        if (!kpiRes.ok || !seriesRes.ok) {
            console.warn('API live error, retrying...');
        } else {
            const kpiData = await kpiRes.json();
            const seriesData = await seriesRes.json();

            updateKPICards(kpiData);
            updateLiveChart(seriesData);
            updateGauge(kpiData);
            updateSLA(kpiData);
        }
        // Les agents sont mis à jour indépendamment (en cas d'échec, on continue)
        await updateAgentStatus();
    } catch (err) {
        console.error('Live update failed:', err);
    }
}

// ------------------------------------------
// KPI cards (8)
// ------------------------------------------
function updateKPICards(data) {
    setText('longestWait', data.longest_call_waiting || '--');
    setText('currentWaiting', data.current_call_waiting ?? '--');
    setText('avgTalkTime', data.average_talk_time || '--');
    setText('totalCalls', formatNumber(data.total_calls_today));
    setText('agentReady', data.agent_ready ?? '--');
    setText('agentLogged', data.agent_logged_in ?? '--');
    setText('asaSeconds', data.asa_seconds ?? '--');
    setText('abandoned', data.abandoned_today ?? '--');
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatNumber(num) {
    if (num === undefined || num === null) return '--';
    return Number(num).toLocaleString();
}

// ------------------------------------------
// Statut des agents (pause, retards, etc.)
// ------------------------------------------
async function updateAgentStatus() {
    try {
        const res = await fetch('/api/v1/live/agents');
        if (!res.ok) return;
        const data = await res.json();

        setText('agentActual', data.agents_actual);
        setText('agentBreak15', data.agents_on_break_15);
        setText('agentBreak60', data.agents_on_break_60);
        setText('agentOverAHT', data.agents_over_aht);
        setText('agentLate', data.agents_late);
        setText('agentFinished', data.agents_finished_shift);

        // Temps restant pause 15 min
        const break15El = document.getElementById('break15Return');
        if (data.break_15_remaining_seconds !== null && data.agents_on_break_15 > 0) {
            const mins = Math.floor(data.break_15_remaining_seconds / 60);
            const secs = data.break_15_remaining_seconds % 60;
            break15El.textContent = `Retour dans ${mins}:${secs.toString().padStart(2,'0')}`;
        } else {
            break15El.textContent = '';
        }

        // Temps restant pause 60 min
        const break60El = document.getElementById('break60Return');
        if (data.break_60_remaining_seconds !== null && data.agents_on_break_60 > 0) {
            const mins = Math.floor(data.break_60_remaining_seconds / 60);
            const secs = data.break_60_remaining_seconds % 60;
            break60El.textContent = `Retour dans ${mins}:${secs.toString().padStart(2,'0')}`;
        } else {
            break60El.textContent = '';
        }
    } catch (err) {
        console.error('Agent status fetch failed:', err);
    }
}

// ------------------------------------------
// Graphique temps réel (Active / On Hold)
// ------------------------------------------
function updateLiveChart(series) {
    if (!series || series.length === 0) return;

    const labels = series.map(d =>
        new Date(d.interval_start).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    );
    const activeData = series.map(d => d.active_calls ?? 0);
    const holdData = series.map(d => d.on_hold ?? 0);

    const ctx = document.getElementById('liveChart').getContext('2d');
    ctx.canvas.style.height = '300px';
    ctx.canvas.parentElement.style.height = '300px';

    if (liveChart) {
        liveChart.destroy();
        liveChart = null;
    }

    liveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Active Calls',
                    data: activeData,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    borderWidth: 2.5,
                },
                {
                    label: 'On Hold',
                    data: holdData,
                    borderColor: '#ff3366',
                    borderDash: [5, 5],
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    pointRadius: 2,
                    borderWidth: 2,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: { color: '#90a0a0' },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: '#90a0a0', stepSize: 20 },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#e0f0f0' }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            }
        }
    });
}

// ------------------------------------------
// Jauge d'activité (doughnut semi-circulaire)
// ------------------------------------------
function updateGauge(kpi) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    ctx.canvas.style.height = '180px';
    ctx.canvas.parentElement.style.height = '220px';

    const waiting = kpi.current_call_waiting || 0;
    const totalTodayMod = (kpi.total_calls_today || 0) % 50;
    let active = waiting + totalTodayMod;
    active = Math.min(Math.max(active, 0), 100);
    const remaining = 100 - active;

    if (gaugeChart) {
        gaugeChart.destroy();
        gaugeChart = null;
    }

    gaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [active, remaining],
                backgroundColor: [
                    createNeonGradient(ctx, '#00ff88', '#00f2fe'),
                    'rgba(255, 255, 255, 0.05)'
                ],
                borderWidth: 0,
                circumference: 180,
                rotation: 270,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '80%',
            plugins: {
                tooltip: { enabled: false },
                legend: { display: false }
            }
        }
    });

    setText('gaugeActive', active);
    setText('gaugeWaiting', waiting);
}

function createNeonGradient(ctx, color1, color2) {
    const gradient = ctx.createLinearGradient(0, 0, 200, 0);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);
    return gradient;
}

// ------------------------------------------
// Bloc Service Level
// ------------------------------------------
function updateSLA(kpi) {
    const slaPct = kpi.service_level_pct ?? '--';
    setText('slaScore', typeof slaPct === 'number' ? slaPct.toFixed(1) + '%' : slaPct);
    const occupancy = kpi.occupancy_pct ?? '--';
    const occStr = typeof occupancy === 'number' ? occupancy.toFixed(1) + '%' : occupancy;
    document.getElementById('slaDetail').textContent = `Answered within 20s | Occupancy: ${occStr}`;
}

// ------------------------------------------
// Prévisions (24h et hebdomadaire)
// ------------------------------------------
async function loadPredictions() {
    try {
        const [todayRes, weekRes] = await Promise.all([
            fetch('/api/v1/predict/today'),
            fetch('/api/v1/predict/week'),
        ]);
        if (todayRes.ok) {
            const todayData = await todayRes.json();
            drawForecastChart(todayData);
        }
        if (weekRes.ok) {
            const weekData = await weekRes.json();
            populateWeeklyTable(weekData);
        }
    } catch (err) {
        console.error('Predictions loading failed:', err);
    }
}

function drawForecastChart(data) {
    if (!data || data.length === 0) return;
    const labels = data.map(d => new Date(d.interval_start).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }));
    const volumeData = data.map(d => d.predicted_call_volume);
    const staffingData = data.map(d => d.required_agents_net);

    const ctx = document.getElementById('forecastChart').getContext('2d');
    ctx.canvas.style.height = '300px';
    ctx.canvas.parentElement.style.height = '300px';

    if (forecastChart) forecastChart.destroy();

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Volume prédit',
                    data: volumeData,
                    borderColor: '#00f2fe',
                    backgroundColor: 'rgba(0, 242, 254, 0.05)',
                    tension: 0.3,
                    pointRadius: 1,
                    borderWidth: 2,
                    yAxisID: 'y',
                },
                {
                    label: 'Agents Net requis',
                    data: staffingData,
                    borderColor: '#f355da',
                    borderDash: [5, 5],
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    pointRadius: 1,
                    borderWidth: 2,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { ticks: { color: '#90a0a0' }, grid: { display: false } },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    ticks: { color: '#00f2fe' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#f355da' }
                }
            },
            plugins: {
                legend: { labels: { color: '#e0f0f0' } },
                tooltip: { mode: 'index', intersect: false }
            }
        }
    });
}

function populateWeeklyTable(data) {
    const tbody = document.getElementById('weeklyTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    data.forEach(day => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${day.day_name} <span style="color:#90a0a0;font-size:0.8rem;">${day.date}</span></td>
            <td>${day.total_call_volume.toLocaleString()}</td>
            <td class="highlight">${day.required_agents_net_peak}</td>
            <td>${day.required_agents_gross_peak}</td>
            <td>${day.target_sla}%</td>
        `;
        tbody.appendChild(row);
    });
}
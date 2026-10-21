
from flask import Flask, jsonify, render_template_string
from member2_cache.cache_manager import get_stats
from dashboard_state import get_events

app = Flask(__name__)

PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>HTTP Proxy Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #101827;
            color: #f1f5f9;
            padding: 28px;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }
        .card, .panel {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
        }
        .muted { color: #94a3b8; }
        .value { font-size: 30px; font-weight: bold; margin-top: 12px; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #334155;
        }
        .panel { overflow-x: auto; }
    </style>
</head>
<body>
    <h1>HTTP Proxy Dashboard</h1>
    <p class="muted">Live proxy and cache statistics</p>

    <div class="cards">
        <div class="card">Total Requests<div class="value" id="total">0</div></div>
        <div class="card">Cache Hit Ratio<div class="value" id="ratio">0%</div></div>
        <div class="card">Cache Hits<div class="value" id="hits">0</div></div>
        <div class="card">Cache Misses<div class="value" id="misses">0</div></div>
        <div class="card">Average Response Time<div class="value" id="latency">0 ms</div></div>
    </div>

    <div class="panel">
        <h2>Recent Requests</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th><th>Method</th><th>URL</th>
                    <th>Cache</th><th>Status</th><th>Time (ms)</th>
                </tr>
            </thead>
            <tbody id="events"></tbody>
        </table>
    </div>

    <script>
        async function refreshDashboard() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                const s = data.stats;

                document.getElementById('total').textContent = s.total_requests ?? 0;
                document.getElementById('ratio').textContent =
                    Number(s.cache_hit_ratio ?? 0).toFixed(1) + '%';
                document.getElementById('hits').textContent = s.cache_hits ?? 0;
                document.getElementById('misses').textContent = s.cache_misses ?? 0;
                document.getElementById('latency').textContent =
                    Number(s.average_response_time_ms ?? 0).toFixed(2) + ' ms';

                const tbody = document.getElementById('events');
                tbody.replaceChildren();

                for (const e of data.events) {
                    const tr = document.createElement('tr');

                    for (const value of [
                        e.time, e.method, e.url, e.cache_status,
                        e.status, e.elapsed_ms
                    ]) {
                        const td = document.createElement('td');
                        td.textContent = value ?? '';
                        tr.appendChild(td);
                    }

                    tbody.appendChild(tr);
                }
            } catch (error) {
                console.error('Dashboard refresh failed:', error);
            }
        }

        refreshDashboard();
        setInterval(refreshDashboard, 2000);
    </script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/api/data")
def api_data():
    return jsonify({
        "stats": get_stats(),
        "events": get_events(),
    })

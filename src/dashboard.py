"""
Dashboard - Web UI for Trading Agent
=====================================
"""
from flask import Flask, jsonify, render_template_string
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data.market_data import MarketDataFetcher
from src.strategies.engine import TradingStrategy
from src.execution.executor import BSCExecutor
from config.settings import DASHBOARD_PORT

app = Flask(__name__)
fetcher = MarketDataFetcher()
executor = BSCExecutor()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BSC AI Trading Agent</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0d1117; color:#e6edf3; font-family:'Segoe UI',system-ui,sans-serif; padding:20px; }
  .header { text-align:center; margin-bottom:30px; }
  .header h1 { font-size:2rem; background:linear-gradient(135deg,#f0b90b,#ff6b35); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .header .subtitle { color:#8b949e; margin-top:5px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:20px; margin-bottom:30px; }
  .card { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; }
  .card h3 { color:#f0b90b; margin-bottom:15px; font-size:0.9rem; text-transform:uppercase; letter-spacing:1px; }
  .metric { font-size:2rem; font-weight:700; }
  .metric.up { color:#3fb950; }
  .metric.down { color:#f85149; }
  .metric.neutral { color:#e6edf3; }
  .sub { color:#8b949e; font-size:0.85rem; margin-top:5px; }
  .signal-box { display:inline-block; padding:6px 16px; border-radius:20px; font-weight:600; font-size:0.9rem; }
  .signal-buy { background:#238636; color:#fff; }
  .signal-sell { background:#da3633; color:#fff; }
  .signal-hold { background:#6e7681; color:#fff; }
  table { width:100%; border-collapse:collapse; }
  th, td { text-align:left; padding:10px; border-bottom:1px solid #21262d; }
  th { color:#8b949e; font-weight:500; font-size:0.8rem; text-transform:uppercase; }
  .refresh-btn { background:#f0b90b; color:#000; border:none; padding:10px 24px; border-radius:8px; cursor:pointer; font-weight:600; }
  .refresh-btn:hover { background:#d4a50a; }
  .status-dot { width:10px; height:10px; border-radius:50%; display:inline-block; margin-right:8px; }
  .status-dot.online { background:#3fb950; }
  .status-dot.offline { background:#f85149; }
</style>
</head>
<body>
<div class="header">
  <h1>🤖 BSC AI Trading Agent</h1>
  <p class="subtitle">Autonomous trading on BNB Chain • BNB Hack: AI Trading Agent Edition</p>
</div>

<div class="grid">
  <div class="card">
    <h3>BNB Price</h3>
    <div class="metric neutral" id="price">Loading...</div>
    <div class="sub" id="price-change">--</div>
  </div>
  <div class="card">
    <h3>Signal</h3>
    <div id="signal">Loading...</div>
    <div class="sub" id="signal-reasons">--</div>
  </div>
  <div class="card">
    <h3>Wallet</h3>
    <div class="sub" id="wallet">--</div>
    <div class="metric neutral" id="balance">--</div>
    <div class="sub" id="mode">--</div>
  </div>
  <div class="card">
    <h3>Market Sentiment</h3>
    <div class="metric neutral" id="sentiment">--</div>
    <div class="sub" id="market-cap">--</div>
  </div>
</div>

<div class="card" style="margin-bottom:20px">
  <h3>Latest Analysis</h3>
  <table>
    <thead><tr><th>Indicator</th><th>Value</th><th>Signal</th></tr></thead>
    <tbody id="indicators"><tr><td colspan="3">Loading...</td></tr></tbody>
  </table>
</div>

<div class="card" style="margin-bottom:20px">
  <h3>Trending Coins (CoinGecko)</h3>
  <table>
    <thead><tr><th>Rank</th><th>Symbol</th><th>Name</th><th>Score</th></tr></thead>
    <tbody id="trending"><tr><td colspan="4">Loading...</td></tr></tbody>
  </table>
</div>

<div style="text-align:center">
  <button class="refresh-btn" onclick="refresh()">🔄 Refresh Data</button>
</div>

<script>
async function refresh() {
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();

    // Price
    const price = data.binance?.price;
    const ticker = data.binance?.ticker_24h;
    document.getElementById('price').textContent = price ? `$${parseFloat(price).toFixed(2)}` : 'N/A';
    if (ticker) {
      const pct = parseFloat(ticker.price_change_pct);
      const el = document.getElementById('price-change');
      el.textContent = `24h: ${pct > 0 ? '+' : ''}${pct}% | Vol: $${(ticker.quote_volume/1e6).toFixed(1)}M`;
      el.style.color = pct >= 0 ? '#3fb950' : '#f85149';
    }

    // Signal
    const sig = data.signal;
    if (sig) {
      const cls = sig.signal.includes('BUY') ? 'buy' : sig.signal.includes('SELL') ? 'sell' : 'hold';
      document.getElementById('signal').innerHTML = `<span class="signal-box signal-${cls}">${sig.signal}</span>`;
      document.getElementById('signal-reasons').textContent = `Confidence: ${(sig.confidence*100).toFixed(0)}% | ${sig.reasons.join(' • ')}`;
    }

    // Wallet
    document.getElementById('wallet').textContent = data.wallet || 'Not connected';
    document.getElementById('balance').textContent = data.balance_bnb ? `${parseFloat(data.balance_bnb).toFixed(4)} BNB` : '--';
    document.getElementById('mode').innerHTML = `<span class="status-dot ${data.mode === 'PAPER' ? 'offline' : 'online'}"></span>${data.mode} MODE`;

    // Sentiment
    const cg = data.coingecko;
    if (cg) {
      document.getElementById('sentiment').textContent = `${cg.sentiment_up}% Bullish`;
      document.getElementById('market-cap').textContent = `MCap: $${(cg.market_cap/1e9).toFixed(1)}B | 7d: ${cg.price_change_7d?.toFixed(1)}%`;
    }

    // Indicators
    const tbody = document.getElementById('indicators');
    tbody.innerHTML = '';
    if (sig?.reasons) {
      sig.reasons.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.split('(')[0].trim()}</td><td>${r.match(/\((.+?)\)/)?.[1] || '--'}</td><td><span class="signal-box signal-${sig.signal.includes('BUY')?'buy':sig.signal.includes('SELL')?'sell':'hold'}" style="font-size:0.7rem">${sig.signal}</span></td>`;
        tbody.appendChild(tr);
      });
    }

    // Trending
    const tt = document.getElementById('trending');
    tt.innerHTML = '';
    (data.trending || []).forEach((t, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${i+1}</td><td><strong>${t.symbol}</strong></td><td>${t.name}</td><td>${t.score}</td>`;
      tt.appendChild(tr);
    });
  } catch(e) {
    console.error('Refresh failed:', e);
  }
}
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/status")
def status():
    snapshot = fetcher.get_full_snapshot()
    strategy = TradingStrategy()
    klines = fetcher.get_klines("BNBUSDT", "1h", 100)
    orderbook = fetcher.get_orderbook("BNBUSDT")
    sentiment = snapshot.get("coingecko")

    signal = None
    if klines:
        sig = strategy.analyze(klines, orderbook, sentiment)
        signal = {
            "signal": sig.signal.value,
            "confidence": sig.confidence,
            "reasons": sig.reasons,
            "price": sig.price
        }

    wallet = executor.wallet_address if executor.is_connected else "Not connected"
    balance = executor.get_balance_bnb() if executor.is_connected else 0

    return jsonify({
        "binance": snapshot.get("binance"),
        "coingecko": snapshot.get("coingecko"),
        "trending": snapshot.get("trending"),
        "signal": signal,
        "wallet": wallet,
        "balance_bnb": balance,
        "mode": "PAPER"
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "connected": executor.is_connected})

if __name__ == "__main__":
    print(f"Dashboard running at http://localhost:{DASHBOARD_PORT}")
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=False)

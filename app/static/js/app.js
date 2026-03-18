document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    let botRunning = false;

    // UI Elements
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const mainControlBtn = document.getElementById('main-control-btn');
    const logDisplay = document.getElementById('log-display');

    // Metrics
    const mTrades = document.getElementById('m-trades');
    const mWinrate = document.getElementById('m-winrate');
    const mProfit = document.getElementById('m-profit');
    const mBalance = document.getElementById('m-balance');
    const mMarkets = document.getElementById('m-markets');

    // Tables
    const positionsTable = document.getElementById('positions-table');
    const resolvedTable = document.getElementById('resolved-table');
    const scanTable = document.getElementById('scan-table');
    const newsTable = document.getElementById('news-table');

    // Tab Logic
    const tabs = document.querySelectorAll('.tab-btn');
    const panes = document.querySelectorAll('.tab-pane');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            panes.forEach(p => p.style.display = 'none');

            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).style.display = 'block';
        });
    });

    // Bot Control
    mainControlBtn.addEventListener('click', () => {
        const action = botRunning ? 'stop' : 'start';
        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        })
        .then(res => res.json())
        .then(data => {
            updateBotUI(data.is_trading);
        });
    });

    function updateBotUI(isTrading) {
        botRunning = isTrading;
        if (isTrading) {
            statusDot.classList.add('active');
            statusText.innerText = 'Trading Active';
            mainControlBtn.innerText = 'Stop Trading';
            mainControlBtn.classList.remove('btn-success');
            mainControlBtn.classList.add('btn-danger');
        } else {
            statusDot.classList.remove('active');
            statusText.innerText = 'Scanning Only';
            mainControlBtn.innerText = 'Start Trading';
            mainControlBtn.classList.remove('btn-danger');
            mainControlBtn.classList.add('btn-success');
        }
    }

    let lastStatusJson = '';

    // Socket Updates
    socket.on('bot_status', (data) => {
        const statusJson = JSON.stringify(data);
        if (statusJson === lastStatusJson) return;
        lastStatusJson = statusJson;

        updateBotUI(data.is_trading);

        // Update Metrics
        mTrades.innerText = data.metrics.total_trades;
        mWinrate.innerText = data.metrics.win_rate + '%';
        mProfit.innerText = '$' + data.metrics.total_profit.toFixed(2);
        mBalance.innerText = '$' + data.metrics.balance.toLocaleString();
        if (mMarkets) mMarkets.innerText = data.total_scanned || 0;

        // Update settings inputs with current values if not already focused
        if (data.config) {
            const inputs = {
                's-mode': data.config.paper_mode.toString(),
                's-amount': data.config.trade_amount,
                's-edge': data.config.min_edge,
                's-interval': data.config.scan_interval,
                's-balance': data.config.paper_balance,
                's-max-trades': data.config.max_trades
            };
            for (const [id, val] of Object.entries(inputs)) {
                const el = document.getElementById(id);
                if (el && document.activeElement !== el) {
                    el.value = val;
                }
            }
        }

        // Update Logs
        logDisplay.innerHTML = data.logs.map(log => `<div class="log-entry">${log}</div>`).join('');
        logDisplay.scrollTop = logDisplay.scrollHeight;

        // Update Positions
        positionsTable.innerHTML = data.open_positions.map(p => `
            <tr>
                <td title="${p.question}">${p.question.substring(0, 50)}...</td>
                <td><span class="side-badge ${p.side.toLowerCase()}">${p.side}</span></td>
                <td>$${p.amount}</td>
                <td>${p.price.toFixed(3)}</td>
                <td><span class="success">Live</span></td>
            </tr>
        `).join('');

        // Update Resolved
        if (resolvedTable && data.resolved_positions) {
            resolvedTable.innerHTML = data.resolved_positions.map(p => {
                const profitClass = p.profit >= 0 ? 'success' : 'danger';
                return `
                    <tr>
                        <td title="${p.question}">${p.question.substring(0, 40)}...</td>
                        <td><span class="side-badge ${p.side.toLowerCase()}">${p.side}</span></td>
                        <td>$${p.amount}</td>
                        <td class="${profitClass}">$${p.profit.toFixed(2)}</td>
                        <td>${p.resolved_at}</td>
                    </tr>
                `;
            }).reverse().join('');
        }

        // Update Scan
        const scanCountBadge = document.getElementById('scan-count-badge');
        if (scanCountBadge) {
            scanCountBadge.innerText = `${data.total_scanned || 0} Markets Found`;
        }
        if (data.scanned_markets && data.scanned_markets.length > 0) {
            // Limit to 100 markets for UI performance
            const displayMarkets = data.scanned_markets.slice(0, 100);
            scanTable.innerHTML = displayMarkets.map(m => {
                const displayTitle = m.question.length > 85 ? m.question.substring(0, 82) + '...' : m.question;
                const statusTag = m.is_new ? '<span class="side-badge yes" style="padding: 2px 6px; font-size: 0.7rem;">New</span>' : '<span style="color: var(--text-dim); font-size: 0.8rem;">Watching</span>';
                return `
                    <tr>
                        <td title="${m.question}">${displayTitle}</td>
                        <td>$${Math.round(m.volume).toLocaleString()}</td>
                        <td>${statusTag}</td>
                    </tr>
                `;
            }).join('');
        } else {
            scanTable.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 40px; color: var(--text-dim);"><div class="loading-spinner"></div><br>Discovering high-volume weather markets...</td></tr>';
        }

        // Update News
        newsTable.innerHTML = data.news_events.map(e => `
            <tr>
                <td>${e.source}</td>
                <td>${e.location}</td>
                <td>${e.type}</td>
                <td>${(e.conf * 100).toFixed(0)}%</td>
                <td style="font-size: 0.75rem">${e.desc}</td>
            </tr>
        `).join('');
    });

    // Settings Form
    const settingsForm = document.getElementById('settings-form');
    settingsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const config = {
            paper_mode: document.getElementById('s-mode').value === 'true',
            trade_amount: parseFloat(document.getElementById('s-amount').value),
            min_edge: parseFloat(document.getElementById('s-edge').value),
            scan_interval: parseInt(document.getElementById('s-interval').value),
            paper_balance: parseFloat(document.getElementById('s-balance').value),
            max_trades: parseInt(document.getElementById('s-max-trades').value),
            private_key: document.getElementById('s-pk').value
        };

        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        })
        .then(res => res.json())
        .then(data => {
            alert('Settings saved successfully!');
        });
    });

    // Request initial update
    socket.emit('request_update');
});

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

    // Tables
    const positionsTable = document.getElementById('positions-table');
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

    // Socket Updates
    socket.on('bot_status', (data) => {
        updateBotUI(data.is_trading);

        // Update Metrics
        mTrades.innerText = data.metrics.total_trades;
        mWinrate.innerText = data.metrics.win_rate + '%';
        mProfit.innerText = '$' + data.metrics.total_profit.toFixed(2);
        mBalance.innerText = '$' + data.metrics.balance.toLocaleString();

        // Update Logs
        logDisplay.innerHTML = data.logs.map(log => `<div class="log-entry">${log}</div>`).join('');
        logDisplay.scrollTop = logDisplay.scrollHeight;

        // Update Positions
        positionsTable.innerHTML = data.open_positions.map(p => `
            <tr>
                <td>${p.question.substring(0, 50)}...</td>
                <td>$${p.amount}</td>
                <td>${p.price.toFixed(3)}</td>
                <td>-</td>
                <td><span class="success">Live</span></td>
            </tr>
        `).join('');

        // Update Scan
        scanTable.innerHTML = data.scanned_markets.map(m => `
            <tr>
                <td>${m.question}</td>
                <td>$${Math.round(m.volume).toLocaleString()}</td>
                <td><span style="color: var(--accent-blue)">Watching</span></td>
            </tr>
        `).join('');

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
            private_key: document.getElementById('s-pk').value,
            wallet_address: document.getElementById('s-wallet').value
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

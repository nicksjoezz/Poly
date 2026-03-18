from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from bot.engine import WeatherBot
import threading
import asyncio
import os

socketio = SocketIO(cors_allowed_origins="*")

# Shared bot instance
bot_instance = None
bot_config = {
    "private_key": os.getenv("PRIVATE_KEY", "0x0000000000000000000000000000000000000000000000000000000000000000"),
    "wallet_address": os.getenv("WALLET_ADDRESS", "0x0000000000000000000000000000000000000000"),
    "trade_amount": 10.0,
    "min_edge": 0.20,
    "scan_interval": 2,
    "paper_mode": True,
    "paper_balance": 1000.0,
    "max_trades": 10
}

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = 'weather_secret_key'

    socketio.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/config', methods=['GET', 'POST'])
    def handle_config():
        global bot_config
        if request.method == 'POST':
            new_config = request.json
            bot_config.update(new_config)
            if bot_instance:
                bot_instance.config = bot_config
            return jsonify({"status": "success", "config": {k: v for k, v in bot_config.items() if "key" not in k}})
        return jsonify({k: v for k, v in bot_config.items() if "key" not in k})

    @app.route('/api/control', methods=['POST'])
    def control_bot():
        global bot_instance
        action = request.json.get("action")

        if not bot_instance:
            bot_instance = WeatherBot(bot_config)
            bot_instance.initialize()

        if action == "start":
            bot_instance.start_trading()
        elif action == "stop":
            bot_instance.stop_trading()

        return jsonify({"status": "success", "is_trading": bot_instance.is_trading})

    @socketio.on('request_update')
    def handle_update():
        global bot_instance
        if not bot_instance:
            bot_instance = WeatherBot(bot_config)
            bot_instance.initialize()

        if bot_instance:
            socketio.emit('bot_status', bot_instance.get_status())
        else:
            socketio.emit('bot_status', {
                "is_running": False,
                "is_trading": False,
                "metrics": {"total_trades": 0, "win_rate": 0, "total_profit": 0, "balance": bot_config["paper_balance"]},
                "open_positions": [],
                "scanned_markets": [],
                "news_events": [],
                "logs": ["Bot offline."],
                "config": {k: v for k, v in bot_config.items() if "key" not in k}
            })

    # Background thread to emit updates periodically
    def background_update_loop():
        while True:
            if bot_instance:
                socketio.emit('bot_status', bot_instance.get_status())
            socketio.sleep(3)

    socketio.start_background_task(background_update_loop)

    return app

import os
from app.main import create_app, socketio

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # In production, debug should be False.
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=port, debug=debug_mode, allow_unsafe_werkzeug=True)

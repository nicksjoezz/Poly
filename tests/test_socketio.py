import socketio
import time

sio = socketio.Client()

@sio.on('bot_status')
def on_message(data):
    print(f"Received update: {list(data.keys())}")
    sio.disconnect()

def test_socket():
    try:
        sio.connect('http://localhost:8080')
        sio.emit('request_update')
        # Wait a bit for the message
        time.sleep(2)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_socket()

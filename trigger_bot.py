import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server")
    sio.emit('request_update')

@sio.on('bot_status')
def on_message(data):
    print("Received bot status")
    sio.disconnect()

sio.connect('http://localhost:8080')
sio.wait()

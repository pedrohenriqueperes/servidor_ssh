from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import paramiko
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

connections = {}
channels = {}

def ssh_thread(host, username, password, sid):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password)
        connections[sid] = client

        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.invoke_shell()
        channels[sid] = channel

        while True:
            if channel.recv_ready():
                output = channel.recv(1024).decode('utf-8')
                socketio.emit('output', {'output': output}, room=sid)
            time.sleep(0.1)
    except Exception as e:
        socketio.emit('output', {'output': str(e)}, room=sid)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connections:
        connections[sid].close()
        del connections[sid]
    if sid in channels:
        channels[sid].close()
        del channels[sid]

@socketio.on('start_ssh')
def handle_start_ssh(data):
    host = data['host']
    username = data['username']
    password = data['password']
    sid = request.sid

    thread = threading.Thread(target=ssh_thread, args=(host, username, password, sid))
    thread.start()
    join_room(sid)

@socketio.on('input')
def handle_input(data):
    command = data['command']
    sid = request.sid
    if sid in channels:
        channels[sid].send(command + '\n')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

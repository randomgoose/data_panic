from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Lock
from serial_reader import ser
from flask_sqlalchemy import SQLAlchemy
import api
 
async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'randomprecision'
socketio = SocketIO(app)
thread = None
thread_lock = Lock()

logged_user = {
        'log_status': False,
        'user_uid': '',
        'user_name': '',
        'user_query': '',
        'user_resource': 5
        }


db = SQLAlchemy(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect', namespace='/conn')
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)

def background_thread():
    while True:
        socketio.sleep(1)

        user_read = ser.readline().decode('utf-8')

        if user_read != logged_user['user_uid']:
            query_result = api.request_tweets()
            logged_user['user_result'] = query_result
            logged_user['user_uid'] = user_read
            logged_user['log_status'] = True

            if '39 )70 17 2D' in user_read:
                logged_user['user_name'] = 'C.CHEN'
            elif '8B 15 D6 15' in user_read:
                logged_user['user_name'] = 'X.FENG'
            else:
                logged_user['user_name'] = 'No User'

            socketio.emit('server_response', {'data': logged_user}, namespace='/conn')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    uid = db.Column(db.String(64), unique=True, index=True) 


if __name__ == '__main__':
    socketio.run(app, debug=True)

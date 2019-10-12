from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Lock
from serial_reader import ser
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import RPi.GPIO as GPIO
import time
import api
import os
 
async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'randomprecision'
socketio = SocketIO(app)
thread = None
thread_lock = Lock()

user_logged = {
        'user_uid': '',
        'user_name': '',
        'user_query': '',
        'user_choice': '',
        'user_resources': None
        }

button_counter = 0

basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Set GPIO mode
GPIO.setmode(GPIO.BCM)

# Set GPIO pins for buttons
GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(23, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(24, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(25, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(14, GPIO.OUT)
# GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_UP)

def my_callback(channel):
    global button_counter
    button_counter += 1
    print(button_counter)

GPIO.add_event_detect(18, GPIO.FALLING, callback=my_callback)

# Check the resources the logged user have
# If the remainder is more than required, trigger api query
def check_resources(user, requirement):
    if user.user_resource < requirement:
        return False
    else:
        return True

def listen_button_event():
    button_state = {
        'text_button': GPIO.input(18),
        'image_button': GPIO.input(23),
        'sound_button': GPIO.input(24),
        'video_button': GPIO.input(25)
    }

    if button_state['text_button'] == False:
        global button_counter
        button_counter += 1
        print('Button Pressed', button_counter)
        GPIO.output(14, GPIO.LOW)
        user_logged['user_choice'] = 'text'
        current_user = User.query.filter_by(username=user_logged['user_name']).first()
        if current_user.resources >= 1:
            current_user.resources -= 1
        else:
            print("You can't afford a text message!")
        db.session.commit()

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
        # 1. first listen for RFID read from user, do user checks etc.

        uid_read = str(ser.readline().decode('utf-8'))[1:12]
        # user_stored = User.query.filter_by(uid=uid_read).first()
        if(logIn(uid_read)):
            socketio.emit('server_response', {'data': user_logged}, namespace='/conn')
        else:
            print('log in failed')
        # if user_stored is None:
        #     print('This user is not registered.')
        #     print('none')
        # elif user_stored.uid == user_logged['user_uid']:
        #     print('same')
        # else:
        #     print('not same')
        #     user_logged['user_uid'] = user_stored.uid
        #     user_logged['user_name'] = user_stored.username
        #     user_logged['user_resources'] = user_stored.resources
        #     socketio.emit('server_response', {'data': user_logged}, namespace='/conn')
def logIn(uid_read):
    # check RFID + check if the user exists in the system
    user_stored = User.query.filter_by(uid=uid_read).first()

    if len(uid_read) >= 0:
        if user_stored is None:
            print('This user is not registered.')
            return False
        else:
            user_logged['user_uid'] = user_stored.uid
            user_logged['user_name'] = user_stored.username
            user_logged['user_resources'] = user_stored.resources
            print(user_logged)
            return True

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    uid = db.Column(db.String(64), unique=True, index=True)
    resources = db.Column(db.Integer)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User)

if __name__ == '__main__':
    socketio.run(app, debug=True)

import os
from flask import Flask, redirect, url_for
import flask_login
from flask_socketio import SocketIO
from .config import Config

app = Flask(__name__, static_folder="../dist", static_url_path="/static")
app.secret_key = os.environ.get("HorizonSecretKey",
                                "unguessablekey")  # Just a random string

conf = Config()

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

users = {
    'admin': {
        'password': os.environ.get("HorizonPassword", "unguessablepw")
    }
}

sio = SocketIO(app, manage_session=False)

from . import main

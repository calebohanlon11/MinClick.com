# This file starts the website app.
# It loads settings, connects the database, and wires the app together.
# Think of it as the main setup for the website.
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
import os
from flask_login import LoginManager
from .config import secret_key
from flask_migrate import Migrate
import json

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key()
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = path.join(app.instance_path, DB_NAME)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    db.init_app(app)

    migrate = Migrate(app, db)  # Initialize Flask-Migrate

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    # Template helper to safely parse JSON strings when needed
    app.jinja_env.filters['fromjson'] = json.loads

    from .models import User, Post, Comment, QuantMathResult, LiveSession  # Include your models

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app



def create_database(app):
    db_path = path.join(app.instance_path, DB_NAME)
    if not path.exists(db_path):
        with app.app_context():
            db.create_all()
            # Initialize shared password
            from .models import SharedPassword
            shared_password = SharedPassword(password='WalK!ing')
            db.session.add(shared_password)
            db.session.commit()

import os
from flask import Flask
from mongoengine import connect
from flask_login import LoginManager
from .model import Book, User, seed_books_if_empty, seed_users_if_missing

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret_key_1234")

    app.config.setdefault("MONGODB_HOST", "mongodb://localhost:27017/sg_library")
    connect(host=app.config["MONGODB_HOST"])

    from .books_bp import bp as books_bp
    from .auth_bp import bp as auth_bp
    app.register_blueprint(books_bp)
    app.register_blueprint(auth_bp)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please login or register first to get an account"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.objects(id=user_id).first()

    with app.app_context():
        seed_books_if_empty()
        seed_users_if_missing()

    return app

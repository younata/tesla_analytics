import os
from flask import Flask


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET", "test")


def app_factory():
    from tesla_analytics.api import data_controller, login_controller
    from tesla_analytics.api import jwt

    app.register_blueprint(data_controller.blueprint, url_prefix="/api")
    app.register_blueprint(login_controller.blueprint, url_prefix="/api")
    jwt.init_app(app)
    return app

import os
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET", "test")


def application(*_):
    from tesla_analytics import api_controller
    from tesla_analytics.api_controller import jwt

    app.register_blueprint(api_controller.blueprint, url_prefix="/api")
    jwt.init_app(app)
    return app

import flask_testing
from flask import Flask

from tesla_analytics.api import jwt
from tesla_analytics.models import db


class APITestCase(flask_testing.TestCase):
    blueprint = None

    def create_app(self):
        app = Flask(__name__)
        app.register_blueprint(self.blueprint)
        app.config['JWT_SECRET_KEY'] = "test"
        jwt.init_app(app)
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(APITestCase, self).setUp()

        self.test_app = self.app.test_client()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

    def tearDown(self):
        super(APITestCase, self).tearDown()
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
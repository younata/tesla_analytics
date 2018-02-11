from datetime import datetime, timedelta
from typing import List, Dict, Callable

import flask_testing
import os
from flask import Flask
from shared_context import behaves_like

from tesla_analytics import api_controller
from tesla_analytics.models import db, ChargeState, ClimateState, DriveState, VehicleState
from tests.helpers import isoformat_timestamp


def requires_auth(self):
    result = self.test_app.get(self.endpoint)
    self.assert401(result)


def requires_vehicle_id(self):
    result = self.test_app.get(self.endpoint, headers={"X-APP-TOKEN": "test"})
    self.assert400(result)


def paginates_results() -> List[Callable]:
    def returns_latest_50_results(self):
        expected = self.generate_items(51)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id".format(endpoint=self.endpoint),
            headers={"X-APP-TOKEN": "test"}
        )

        self.assert200(result)
        self.assertListEqual(result.json, expected[:50])

    def pages_results_by_50(self):
        expected = self.generate_items(101)
        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&page=2".format(endpoint=self.endpoint),
            headers={"X-APP-TOKEN": "test"}
        )

        self.assert200(result)

        self.assertEqual(result.json, expected[50:100])

    def sets_paging_headers_correctly_on_page_1(self):
        self.generate_items(101)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id".format(endpoint=self.endpoint),
            headers={"X-APP-TOKEN": "test"}
        )

        self.assert200(result)

        expected_link_header = ", ".join([
            '<http://localhost{endpoint}?vehicle_id=test_id&page=2>; rel="next"'.format(endpoint=self.endpoint),
            '<http://localhost{endpoint}?vehicle_id=test_id&page=3>; rel="last"'.format(endpoint=self.endpoint)
        ])

        self.assertEqual(result.headers["Link"], expected_link_header)

    def sets_paging_headers_correctly_on_middle_page(self):
        self.generate_items(101)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&page=2".format(endpoint=self.endpoint),
            headers={"X-APP-TOKEN": "test"}
        )

        self.assert200(result)

        expected_link_header = ", ".join([
            '<http://localhost{endpoint}?vehicle_id=test_id&page=1>; rel="prev"'.format(endpoint=self.endpoint),
            '<http://localhost{endpoint}?vehicle_id=test_id&page=3>; rel="next"'.format(endpoint=self.endpoint),
            '<http://localhost{endpoint}?vehicle_id=test_id&page=3>; rel="last"'.format(endpoint=self.endpoint),
            '<http://localhost{endpoint}?vehicle_id=test_id&page=1>; rel="first"'.format(endpoint=self.endpoint)
        ])

        self.assertEqual(result.headers["Link"], expected_link_header)

    def sets_paging_headers_correctly_on_last_page(self):
        self.generate_items(101)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&page=3".format(endpoint=self.endpoint),
            headers={"X-APP-TOKEN": "test"}
        )

        self.assert200(result)

        expected_link_header = ", ".join([
            '<http://localhost{endpoint}?vehicle_id=test_id&page=2>; rel="prev"'.format(endpoint=self.endpoint),
            '<http://localhost{endpoint}?vehicle_id=test_id&page=1>; rel="first"'.format(endpoint=self.endpoint)
        ])

        self.assertEqual(result.headers["Link"], expected_link_header)

    return [returns_latest_50_results, pages_results_by_50, sets_paging_headers_correctly_on_page_1,
            sets_paging_headers_correctly_on_middle_page, sets_paging_headers_correctly_on_last_page]


@behaves_like(requires_auth, requires_vehicle_id, *paginates_results())
class APIChargeTests(flask_testing.TestCase):
    endpoint = "/charge"

    def create_app(self):
        app = Flask(__name__)
        app.register_blueprint(api_controller.blueprint)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(APIChargeTests, self).setUp()
        self.test_app = self.app.test_client()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

        old_api_token = os.getenv("API_TOKEN")
        os.environ["API_TOKEN"] = "test"

        def reset_api_token():
            if old_api_token:
                os.environ["API_TOKEN"] = old_api_token
            else:
                del os.environ["API_TOKEN"]
        self.addCleanup(reset_api_token)

    def tearDown(self):
        super(APIChargeTests, self).tearDown()
        with self.app.app_context():
            db.session.commit()
            db.drop_all()

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        charge_states = [
            {"timestamp": datetime.now() - timedelta(hours=i)} for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_charging(charge_states)

        return [{"timestamp": isoformat_timestamp(state["timestamp"])} for state in charge_states]

    @staticmethod
    def _populate_charging(items: List[Dict]):
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            db.session.add(ChargeState(state))
        db.session.commit()


@behaves_like(requires_auth, requires_vehicle_id, *paginates_results())
class APIClimateTests(flask_testing.TestCase):
    endpoint = "/climate"

    def create_app(self):
        app = Flask(__name__)
        app.register_blueprint(api_controller.blueprint)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(APIClimateTests, self).setUp()
        self.test_app = self.app.test_client()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

        old_api_token = os.getenv("API_TOKEN")
        os.environ["API_TOKEN"] = "test"

        def reset_api_token():
            if old_api_token:
                os.environ["API_TOKEN"] = old_api_token
            else:
                del os.environ["API_TOKEN"]

        self.addCleanup(reset_api_token)

    def tearDown(self):
        super(APIClimateTests, self).tearDown()
        with self.app.app_context():
            db.session.commit()
            db.drop_all()

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        states = [
            {"timestamp": datetime.now() - timedelta(hours=i)} for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_database(states)

        return [{"timestamp": isoformat_timestamp(state["timestamp"])} for state in states]

    @staticmethod
    def _populate_database(items: List[Dict]):
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            db.session.add(ClimateState(state))
        db.session.commit()


@behaves_like(requires_auth, requires_vehicle_id, *paginates_results())
class APIDriveTests(flask_testing.TestCase):
    endpoint = "/drive"

    def create_app(self):
        app = Flask(__name__)
        app.register_blueprint(api_controller.blueprint)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(APIDriveTests, self).setUp()
        self.test_app = self.app.test_client()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

        old_api_token = os.getenv("API_TOKEN")
        os.environ["API_TOKEN"] = "test"

        def reset_api_token():
            if old_api_token:
                os.environ["API_TOKEN"] = old_api_token
            else:
                del os.environ["API_TOKEN"]

        self.addCleanup(reset_api_token)

    def tearDown(self):
        super(APIDriveTests, self).tearDown()
        with self.app.app_context():
            db.session.commit()
            db.drop_all()

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        states = [
            {
                "timestamp": datetime.now() - timedelta(hours=i),
                "gps_as_of": datetime.now() - timedelta(hours=i, minutes=5),
                "latitude": 37.548271,
                "longitude": -121.988571,  # Tesla Factory, Fremont
                "power": 0,
                "shift_state": "P",
                "speed": 0,
            } for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_database(states)

        return [
            {
                "timestamp": isoformat_timestamp(state["timestamp"]),
                "gps_as_of": datetime.fromtimestamp(int(state["gps_as_of"].timestamp())).isoformat(),
                "latitude": 37.548271,
                "longitude": -121.988571,  # Tesla Factory, Fremont
                "power": 0,
                "shift_state": "P",
                "speed": 0,
            } for state in states]

    @staticmethod
    def _populate_database(items: List[Dict]):
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            state["gps_as_of"] = int(state["gps_as_of"].timestamp())
            db.session.add(DriveState(state))
        db.session.commit()


@behaves_like(requires_auth, requires_vehicle_id, *paginates_results())
class APIVehicleTests(flask_testing.TestCase):
    endpoint = "/vehicle"

    def create_app(self):
        app = Flask(__name__)
        app.register_blueprint(api_controller.blueprint)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(APIVehicleTests, self).setUp()
        self.test_app = self.app.test_client()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

        old_api_token = os.getenv("API_TOKEN")
        os.environ["API_TOKEN"] = "test"

        def reset_api_token():
            if old_api_token:
                os.environ["API_TOKEN"] = old_api_token
            else:
                del os.environ["API_TOKEN"]

        self.addCleanup(reset_api_token)

    def tearDown(self):
        super(APIVehicleTests, self).tearDown()
        with self.app.app_context():
            db.session.commit()
            db.drop_all()

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        states = [
            {"timestamp": datetime.now() - timedelta(hours=i)} for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_database(states)

        return [{"timestamp": isoformat_timestamp(state["timestamp"])} for state in states]

    @staticmethod
    def _populate_database(items: List[Dict]):
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            db.session.add(VehicleState(state))
        db.session.commit()

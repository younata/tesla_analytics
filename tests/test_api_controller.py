import json
from datetime import datetime, timedelta
from typing import List, Dict, Callable

import flask_testing
from flask import Flask
from shared_context import behaves_like

from tesla_analytics import api_controller
from tesla_analytics.api_controller import jwt
from tesla_analytics.models import db, ChargeState, ClimateState, DriveState, VehicleState
from tests.helpers import isoformat_timestamp
from tests.test_worker import create_user, create_vehicle


def requires_user_auth() -> List[Callable]:
    def requires_auth(self):
        result = self.test_app.get(self.endpoint)
        self.assert401(result)
        self.assertEqual(result.json, {"msg": "Missing Authorization Header"})

    return [
        requires_auth,
    ]


def requires_vehicle() -> List[Callable]:
    def requires_vehicle_id(self):
        result = self.test_app.get(self.endpoint, headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())})
        self.assert400(result)

    def returns_400_if_wrong_vehicle_id(self):
        self.generate_items(1)
        result = self.test_app.get(
            "{endpoint}?vehicle_id=nonexistent".format(endpoint=self.endpoint),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )
        self.assert400(result)
        self.assertDictEqual(result.json, {"error": "Vehicle not found"})

    def returns_400_if_vehicle_exists_but_does_not_belong_to_user(self):
        other_user = create_user("other@example.com", "test_2")
        create_vehicle("test_id", other_user)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id".format(endpoint=self.endpoint),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )
        self.assert400(result)
        self.assertDictEqual(result.json, {"error": "Vehicle not found"})

    return [
        requires_vehicle_id,
        returns_400_if_wrong_vehicle_id,
        returns_400_if_vehicle_exists_but_does_not_belong_to_user,
    ]


def paginates_results() -> List[Callable]:
    def returns_results_in_timeframe(self):
        generated = self.generate_items(10)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&start={early}&end={later}".format(endpoint=self.endpoint,
                                                                               early=generated[7]["timestamp"],
                                                                               later=generated[2]["timestamp"]),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[2:8])

    def returns_latest_50_results(self):
        generated = self.generate_items(51)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id".format(endpoint=self.endpoint),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[:50])

    def pages_results_by_50(self):
        generated = self.generate_items(101)
        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&page=2".format(endpoint=self.endpoint),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)

        self.assertEqual(result.json, generated[50:100])

    def sets_paging_headers_correctly_on_page_1(self):
        self.generate_items(101)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id".format(endpoint=self.endpoint),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
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
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
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
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)

        expected_link_header = ", ".join([
            '<http://localhost{endpoint}?vehicle_id=test_id&page=2>; rel="prev"'.format(endpoint=self.endpoint),
            '<http://localhost{endpoint}?vehicle_id=test_id&page=1>; rel="first"'.format(endpoint=self.endpoint)
        ])

        self.assertEqual(result.headers["Link"], expected_link_header)

    return [returns_results_in_timeframe, returns_latest_50_results, pages_results_by_50,
            sets_paging_headers_correctly_on_page_1, sets_paging_headers_correctly_on_middle_page,
            sets_paging_headers_correctly_on_last_page]


class APITestCase(flask_testing.TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.register_blueprint(api_controller.blueprint)
        app.config['JWT_SECRET_KEY'] = "test"
        jwt.init_app(app)
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


class LoginTests(APITestCase):
    def test_when_user_exists_and_password_matches_returns_access_token(self):
        create_user()

        result = self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        )

        self.assert200(result)

        self.assertIsNotNone(result.json.get("access_token"))

    def test_when_doesnt_send_json_returns_400(self):
        create_user()

        result = self.test_app.post(
            "/login",
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        )

        self.assert400(result)
        self.assertDictEqual(
            result.json,
            {"error": "Must be JSON"}
        )

    def test_when_user_doesnt_exist_returns_401(self):
        result = self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        )

        self.assert401(result)
        self.assertDictEqual(
            result.json,
            {"error": "Wrong email or password"}
        )

    def test_when_password_is_wrong_returns_401(self):
        create_user()
        result = self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "not_test"
            })
        )

        self.assert401(result)
        self.assertDictEqual(
            result.json,
            {"error": "Wrong email or password"}
        )

    def test_when_email_is_left_out_returns_400(self):
        create_user()
        result = self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "password": "not_test"
            })
        )

        self.assert400(result)
        self.assertDictEqual(
            result.json,
            {"error": "Missing required parameter 'email'"}
        )

    def test_when_password_is_left_out_returns_400(self):
        create_user()
        result = self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com"
            })
        )

        self.assert400(result)
        self.assertDictEqual(
            result.json,
            {"error": "Missing required parameter 'password'"}
        )


@behaves_like(*requires_user_auth())
class VehiclesTests(APITestCase):
    endpoint = "/vehicles"

    def setUp(self):
        super(VehiclesTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        ).json.get("access_token")

    def test_returns_all_vehicles_a_user_has(self):
        other_user = create_user("other_email")
        _ = create_vehicle("test_id", self.user, vin="1")
        _ = create_vehicle("test_id_2", self.user, vin="2", color="Blue", name="name")
        _ = create_vehicle("test_id_3", other_user)

        result = self.test_app.get(
            "/vehicles",
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)

        self.assertEqual(result.json, [
            {
                "vehicle_id": "test_id",
                "vin": "1",
                "color": None,
                "name": None,
            },
            {
                "vehicle_id": "test_id_2",
                "vin": "2",
                "color": "Blue",
                "name": "name",
            }
        ])


@behaves_like(*requires_user_auth(), *requires_vehicle(), *paginates_results())
class ChargeTests(APITestCase):
    endpoint = "/charge"

    def setUp(self):
        super(ChargeTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        ).json.get("access_token")

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        charge_states = [
            {"timestamp": datetime.now() - timedelta(hours=i)} for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_charging(charge_states)

        return [{"timestamp": isoformat_timestamp(state["timestamp"])} for state in charge_states]

    def _populate_charging(self, items: List[Dict]):
        vehicle = create_vehicle("test_id", self.user)
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            db.session.add(ChargeState(state, vehicle=vehicle))
        db.session.commit()


@behaves_like(*requires_user_auth(), *requires_vehicle(), *paginates_results())
class ClimateTests(APITestCase):
    endpoint = "/climate"

    def setUp(self):
        super(ClimateTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        ).json.get("access_token")

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        states = [
            {"timestamp": datetime.now() - timedelta(hours=i)} for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_database(states)

        return [{"timestamp": isoformat_timestamp(state["timestamp"])} for state in states]

    def _populate_database(self, items: List[Dict]):
        vehicle = create_vehicle("test_id", self.user)
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            db.session.add(ClimateState(state, vehicle=vehicle))
        db.session.commit()


@behaves_like(*requires_user_auth(), *requires_vehicle(), *paginates_results())
class DriveTests(APITestCase):
    endpoint = "/drive"

    def setUp(self):
        super(DriveTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        ).json.get("access_token")

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
                "gps_as_of": datetime.fromtimestamp(int(state["gps_as_of"].timestamp())).isoformat() + "Z",
                "latitude": 37.548271,
                "longitude": -121.988571,  # Tesla Factory, Fremont
                "power": 0,
                "shift_state": "P",
                "speed": 0,
            } for state in states]

    def _populate_database(self, items: List[Dict]):
        vehicle = create_vehicle("test_id", self.user)
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            state["gps_as_of"] = int(state["gps_as_of"].timestamp())
            db.session.add(DriveState(state, vehicle=vehicle))
        db.session.commit()


@behaves_like(*requires_user_auth(), *requires_vehicle(), *paginates_results())
class VehicleTests(APITestCase):
    endpoint = "/vehicle"

    def setUp(self):
        super(VehicleTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        ).json.get("access_token")

    def generate_items(self, amount_to_generate: int) -> List[Dict]:
        states = [
            {"timestamp": datetime.now() - timedelta(hours=i)} for i in range(amount_to_generate)
        ]
        with self.app.app_context():
            self._populate_database(states)

        return [{"timestamp": isoformat_timestamp(state["timestamp"])} for state in states]

    def _populate_database(self, items: List[Dict]):
        vehicle = create_vehicle("test_id", self.user)
        for data in items:
            state = dict(data)
            state["timestamp"] = int(state["timestamp"].timestamp() * 1000)
            db.session.add(VehicleState(state, vehicle=vehicle))
        db.session.commit()

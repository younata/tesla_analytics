from datetime import datetime, timedelta
from typing import List, Dict

from flask_jwt_extended import create_access_token
from shared_context import behaves_like

from tesla_analytics.api import data_controller
from tesla_analytics.models import db, ChargeState, ClimateState, DriveState, VehicleState
from tests.api import APITestCase
from tests.api.shared_tests import requires_user_auth, requires_vehicle, paginates_results
from tests.helpers import isoformat_timestamp
from tests.test_worker import create_user, create_vehicle


@behaves_like(*requires_user_auth())
class VehiclesTests(APITestCase):
    blueprint = data_controller.blueprint
    endpoint = "/vehicles"

    def setUp(self):
        super(VehiclesTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return create_access_token(identity="me@example.com")

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
    blueprint = data_controller.blueprint
    endpoint = "/charge"

    def setUp(self):
        super(ChargeTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return create_access_token(identity="me@example.com")

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
    blueprint = data_controller.blueprint
    endpoint = "/climate"

    def setUp(self):
        super(ClimateTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return create_access_token(identity="me@example.com")

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
    blueprint = data_controller.blueprint
    endpoint = "/drive"

    def setUp(self):
        super(DriveTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return create_access_token(identity="me@example.com")

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
    blueprint = data_controller.blueprint
    endpoint = "/vehicle"

    def setUp(self):
        super(VehicleTests, self).setUp()
        self.user = create_user()

    def access_token(self):
        return create_access_token(identity="me@example.com")

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

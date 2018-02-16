from datetime import datetime, timedelta
from unittest.mock import patch
from urllib import error as urlliberror

import bcrypt
import flask_testing
from flask import Flask
from mockito import mock, verifyStubbedInvocationsAreUsed, unstub, when, verifyNoUnwantedInteractions, expect

from tesla_analytics import workers
from tesla_analytics.models import User, db, Vehicle
from tesla_analytics.workers import vehicle_poller, InvalidToken, monitor


class TestMonitor(flask_testing.TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(TestMonitor, self).setUp()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

    def tearDown(self):
        super(TestMonitor, self).tearDown()
        unstub()

        with self.app.app_context():
            db.session.commit()
            db.drop_all()

    def test_polls_vehicles_that_are_set_to_be_updated(self):
        user = create_user()

        vehicle_to_be_updated = create_vehicle("vehicle_1", user)
        vehicle_to_be_updated.next_update_time = datetime.now() - timedelta(seconds=10)
        vehicle_to_be_skipped = create_vehicle("vehicle_2", user)
        not_yet_updated_vehicle = create_vehicle("vehicle_3", user)
        not_yet_updated_vehicle.next_update_time = None
        skip_time = datetime.now() + timedelta(seconds=10)
        vehicle_to_be_skipped.next_update_time = skip_time

        db.session.add(vehicle_to_be_updated)
        db.session.add(vehicle_to_be_skipped)
        db.session.add(not_yet_updated_vehicle)
        db.session.commit()

        update_time = datetime(2018, 2, 14, 20, 15, 2, 50)

        when(workers).vehicle_poller(vehicle_to_be_updated).thenReturn(update_time)
        when(workers).vehicle_poller(not_yet_updated_vehicle).thenReturn(update_time)

        monitor()

        self.assertEqual(vehicle_to_be_updated.next_update_time, update_time)
        self.assertEqual(not_yet_updated_vehicle.next_update_time, update_time)
        self.assertEqual(vehicle_to_be_skipped.next_update_time, skip_time)

        verifyStubbedInvocationsAreUsed()
        verifyNoUnwantedInteractions()

    def test_if_invalid_token_raised_notifies_user_that_and_skips_users_other_vehicles(self):
        user = create_user()
        user_2 = create_user()

        vehicle_1 = create_vehicle("vehicle_1", user)
        vehicle_2 = create_vehicle("vehicle_2", user)

        vehicle_3 = create_vehicle("vehicle_3", user_2)

        for vehicle in [vehicle_1, vehicle_2, vehicle_3]:
            vehicle.next_update_time = datetime.now() - timedelta(seconds=10)
            db.session.add(vehicle)

        db.session.commit()

        when(workers).vehicle_poller(vehicle_1).thenRaise(InvalidToken())
        when(workers).vehicle_poller(vehicle_3).thenReturn(datetime.now())
        when(workers).notify_user_of_bad_token(user)

        try:
            monitor()
        except InvalidToken:
            assert False, "Expected to not raise InvalidToken, but raised"

        self.assertIsNone(user.tesla_access_token)

        verifyStubbedInvocationsAreUsed()
        verifyNoUnwantedInteractions()

    def test_if_user_has_no_token_skips_user(self):
        user = create_user()
        user.tesla_access_token = None

        vehicle_1 = create_vehicle("vehicle_1", user)

        for vehicle in [vehicle_1]:
            vehicle.next_update_time = datetime.now() - timedelta(seconds=10)
            db.session.add(vehicle)

        db.session.add(user)
        db.session.commit()

        expect(workers, times=0).vehicle_poller(vehicle_1)
        expect(workers, times=0).notify_user_of_bad_token(user)

        monitor()

        verifyStubbedInvocationsAreUsed()
        verifyNoUnwantedInteractions()


class TestNotifyUserOfBadToken(flask_testing.TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(TestNotifyUserOfBadToken, self).setUp()

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

    def tearDown(self):
        super(TestNotifyUserOfBadToken, self).tearDown()
        unstub()

        with self.app.app_context():
            db.session.commit()
            db.drop_all()


class TestVehiclePoller(flask_testing.TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://localhost"
        return app

    def setUp(self):
        super(TestVehiclePoller, self).setUp()
        self.service = mock(workers.TeslaService)
        when(workers).TeslaService(token="token").thenReturn(self.service)

        db.init_app(self.app)
        with self.app.app_context():
            db.session.commit()
            db.drop_all()
            db.create_all()

    def tearDown(self):
        super(TestVehiclePoller, self).tearDown()
        unstub()

        with self.app.app_context():
            db.session.commit()
            db.drop_all()

    # Happy Path

    def test_wakes_up_vehicle_and_asks_for_all_states(self):
        now = datetime.now()

        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id")
        when(self.service).charge_state("vehicle_id").thenReturn(self._generate_charge(now.timestamp() * 1000, None))
        when(self.service).climate("vehicle_id").thenReturn(self._generate_climate(now.timestamp() * 1000))
        when(self.service).position("vehicle_id").thenReturn(self._generate_drive(now.timestamp() * 1000, now.timestamp()))
        when(self.service).vehicle_state("vehicle_id").thenReturn(self._generate_vehicle_state(now.timestamp() * 1000))

        vehicle_poller(vehicle)

        verifyStubbedInvocationsAreUsed()

    def test_stores_state_data(self):
        now = datetime.now()

        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id")
        when(self.service).charge_state("vehicle_id").thenReturn(self._generate_charge(now.timestamp() * 1000, "None"))
        when(self.service).climate("vehicle_id").thenReturn(self._generate_climate(now.timestamp() * 1000))
        when(self.service).position("vehicle_id").thenReturn(self._generate_drive(now.timestamp() * 1000, int(now.timestamp())))
        when(self.service).vehicle_state("vehicle_id").thenReturn(self._generate_vehicle_state(now.timestamp() * 1000))

        self.assertEqual(len(vehicle.charge_states), 0)
        self.assertEqual(len(vehicle.climate_states), 0)
        self.assertEqual(len(vehicle.drive_states), 0)
        self.assertEqual(len(vehicle.vehicle_states), 0)

        now = datetime.fromtimestamp(int(now.timestamp() * 1000) / 1000.0)

        vehicle_poller(vehicle)

        self.assertEqual(len(vehicle.charge_states), 1)
        self.assertEqual(
            vehicle.charge_states[0].serialize(),
            {"timestamp": now.isoformat(), "charging_state": "None"}
        )

        self.assertEqual(len(vehicle.climate_states), 1)
        self.assertEqual(
            vehicle.climate_states[0].serialize(),
            {"timestamp": now.isoformat(), "climate": "yes"}
        )

        self.assertEqual(len(vehicle.drive_states), 1)
        self.assertEqual(
            vehicle.drive_states[0].serialize(),
            {
                "timestamp": now.isoformat(),
                "gps_as_of": datetime.fromtimestamp(int(now.timestamp())).isoformat(),
                "latitude": 37.548271,
                "longitude": -121.988571,  # Tesla Factory, Fremont
                "power": 0,
                "shift_state": "P",
                "speed": 0
            }
        )

        self.assertEqual(len(vehicle.vehicle_states), 1)
        self.assertEqual(
            vehicle.vehicle_states[0].serialize(),
            {"timestamp": now.isoformat(), "vehicle": "yes"}
        )

    def test_returns_15_seconds_later_as_next_time_to_poll_if_driving(self):
        now = datetime.now()

        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id")
        when(self.service).charge_state("vehicle_id").thenReturn(self._generate_charge(now.timestamp() * 1000, "Disconnected"))
        when(self.service).climate("vehicle_id").thenReturn(self._generate_climate(now.timestamp() * 1000))
        when(self.service).position("vehicle_id").thenReturn(self._generate_drive(now.timestamp() * 1000, now.timestamp(), "D"))
        when(self.service).vehicle_state("vehicle_id").thenReturn(self._generate_vehicle_state(now.timestamp() * 1000))

        with patch("tesla_analytics.workers.current_time", return_value=now):
            next_update_time = vehicle_poller(vehicle)

        self.assertEqual(next_update_time, now + timedelta(seconds=15))

    def test_returns_1_minute_later_as_next_time_to_poll_if_charging(self):
        now = datetime.now()

        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id")
        when(self.service).charge_state("vehicle_id").thenReturn(self._generate_charge(now.timestamp() * 1000, "Charging"))
        when(self.service).climate("vehicle_id").thenReturn(self._generate_climate(now.timestamp() * 1000))
        when(self.service).position("vehicle_id").thenReturn(self._generate_drive(now.timestamp() * 1000, now.timestamp()))
        when(self.service).vehicle_state("vehicle_id").thenReturn(self._generate_vehicle_state(now.timestamp() * 1000))

        with patch("tesla_analytics.workers.current_time", return_value=now):
            next_update_time = vehicle_poller(vehicle)

        self.assertEqual(next_update_time, now + timedelta(minutes=1))

    def test_returns_5_minutes_later_as_next_time_to_poll_if_parked_and_not_charging(self):
        now = datetime.now()

        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id")
        when(self.service).charge_state("vehicle_id").thenReturn(self._generate_charge(now.timestamp() * 1000, "Disconnected"))
        when(self.service).climate("vehicle_id").thenReturn(self._generate_climate(now.timestamp() * 1000))
        when(self.service).position("vehicle_id").thenReturn(self._generate_drive(now.timestamp() * 1000, now.timestamp()))
        when(self.service).vehicle_state("vehicle_id").thenReturn(self._generate_vehicle_state(now.timestamp() * 1000))

        with patch("tesla_analytics.workers.current_time", return_value=now):
            next_update_time = vehicle_poller(vehicle)

        self.assertEqual(next_update_time, now + timedelta(minutes=5))

    # Sad Paths

    def test_if_tesla_service_raises_401_raises_invalid_token(self):
        unstub(workers)
        when(workers).TeslaService(token="token").thenRaise(urlliberror.HTTPError(None, 401, None, None, None))

        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        with self.assertRaises(InvalidToken):
            vehicle_poller(vehicle)

    def test_if_vehicle_data_fetch_returns_value_error_continues_and_returns_10_minutes_as_next_poll_time(self):
        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id").thenRaise(ValueError("timeout"))
        when(self.service).vehicles().thenReturn([])

        now = datetime.now()
        with patch("tesla_analytics.workers.current_time", return_value=now):
            next_update_time = vehicle_poller(vehicle)

        self.assertEqual(next_update_time, now + timedelta(minutes=10))

    def test_if_vehicle_wake_up_raises_error_returns_2_minutes_as_next_time_to_poll(self):
        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id").thenRaise(urlliberror.URLError("timeout"))

        now = datetime.now()
        with patch("tesla_analytics.workers.current_time", return_value=now):
            next_update_time = vehicle_poller(vehicle)

        self.assertEqual(next_update_time, now + timedelta(minutes=2))

    def test_if_vehicle_data_fetch_raises_error_returns_2_minutes_as_next_time_to_poll(self):
        user = create_user()
        vehicle = create_vehicle("vehicle_id", user)

        when(self.service).wake_up("vehicle_id")
        when(self.service).charge_state("vehicle_id").thenRaise(urlliberror.URLError("timeout"))
        when(self.service).climate("vehicle_id").thenRaise(urlliberror.URLError("timeout"))
        when(self.service).position("vehicle_id").thenRaise(urlliberror.URLError("timeout"))
        when(self.service).vehicle_state("vehicle_id").thenRaise(urlliberror.URLError("timeout"))

        now = datetime.now()

        with patch("tesla_analytics.workers.current_time", return_value=now):
            next_update_time = vehicle_poller(vehicle)

        self.assertEqual(next_update_time, now + timedelta(minutes=2))

    @staticmethod
    def _generate_charge(timestamp, charging_state):
        return {"timestamp": int(timestamp), "charging_state": charging_state}

    @staticmethod
    def _generate_climate(timestamp):
        return {"timestamp": int(timestamp), "climate": "yes"}

    @staticmethod
    def _generate_drive(timestamp, gps_timestamp, shift_state="P"):
        return {
            "timestamp": int(timestamp),
            "gps_as_of": gps_timestamp,
            "latitude": 37.548271,
            "longitude": -121.988571,  # Tesla Factory, Fremont
            "power": 0,
            "shift_state": shift_state,
            "speed": 0
        }

    @staticmethod
    def _generate_vehicle_state(timestamp):
        return {"timestamp": int(timestamp), "vehicle": "yes"}


def create_vehicle(vehicle_id, user):
    vehicle = Vehicle(tesla_id=vehicle_id, vin="my_vin", user=user)
    db.session.add(vehicle)
    db.session.commit()
    return vehicle


def create_user(email="me@example.com", password="test"):
    password_hash = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt()).decode("utf-8")
    user = User(
        email=email,
        password_hash=password_hash,
        tesla_access_token="token"
    )
    db.session.add(user)
    db.session.commit()
    return user

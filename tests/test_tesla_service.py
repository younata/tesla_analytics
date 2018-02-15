import unittest

import teslajson
from mockito import unstub, when, mock, verifyStubbedInvocationsAreUsed

from tesla_analytics import tesla_service
from tesla_analytics.tesla_service import TeslaService


class TestTeslaService(unittest.TestCase):
    def setUp(self):
        self.teslajson = mock(tesla_service.teslajson)

    def tearDown(self):
        verifyStubbedInvocationsAreUsed()
        unstub()

    def test_init_when_given_email_and_password_logs_in(self):
        self._setup_for_email()
        TeslaService(email="email", password="password")

    def test_init_on_login_with_email_and_password_sets_token_property(self):
        self._setup_for_email()
        self.teslajson.access_token = "access_token"
        subject = TeslaService("email", "password")

        self.assertEqual(subject.token, "access_token")

    def test_init_allows_with_access_token(self):
        self._setup_for_access_token()
        TeslaService(token="access_token")

    def test_vehicles_returns_available_vehicles(self):
        self._setup_for_access_token()
        subject = TeslaService(token="access_token")

        self.teslajson.vehicles = [
            {"id": "vehicle_id_1"},
            {"id": "vehicle_id_2"},
        ]

        self.assertEqual(
            subject.vehicles(),
            [
                {"id": "vehicle_id_1"},
                {"id": "vehicle_id_2"},
            ]
        )

    def test_wake_up_tells_vehicle_to_wake_up(self):
        self._setup_for_access_token()

        vehicle = self._create_vehicle("vehicle_id_1")
        when(vehicle).wake_up()

        subject = TeslaService(token="access_token")

        subject.wake_up("vehicle_id_1")

    def test_charge_state_fetches_and_returns_charge_data_for_vehicle(self):
        self._setup_for_access_token()

        vehicle = self._create_vehicle("vehicle_id_1")
        when(vehicle).data_request("charge_state").thenReturn({"some": "data"})

        subject = TeslaService(token="access_token")

        self.assertEqual(
            subject.charge_state("vehicle_id_1"),
            {"some": "data"}
        )

    def test_climate_fetches_and_returns_climate_data_for_vehicle(self):
        self._setup_for_access_token()

        vehicle = self._create_vehicle("vehicle_id_1")
        when(vehicle).data_request("climate_state").thenReturn({"some": "data"})

        subject = TeslaService(token="access_token")

        self.assertEqual(
            subject.climate("vehicle_id_1"),
            {"some": "data"}
        )

    def test_position_fetches_and_returns_drive_data_for_vehicle(self):
        self._setup_for_access_token()

        vehicle = self._create_vehicle("vehicle_id_1")
        when(vehicle).data_request("drive_state").thenReturn({"some": "data"})

        subject = TeslaService(token="access_token")

        self.assertEqual(
            subject.position("vehicle_id_1"),
            {"some": "data"}
        )

    def test_vehicle_state_fetches_and_returns_vehicle_data_for_vehicle(self):
        self._setup_for_access_token()

        vehicle = self._create_vehicle("vehicle_id_1")
        when(vehicle).data_request("vehicle_state").thenReturn({"some": "data"})

        subject = TeslaService(token="access_token")

        self.assertEqual(
            subject.vehicle_state("vehicle_id_1"),
            {"some": "data"}
        )

    def _setup_for_email(self):
        when(tesla_service.teslajson).Connection(email="email", password="password", access_token='').thenReturn(self.teslajson)

    def _setup_for_access_token(self):
        when(tesla_service.teslajson).Connection(email='', password='', access_token="access_token").thenReturn(self.teslajson)

    def _create_vehicle(self, id):
        vehicle = mock(spec=teslajson.Vehicle)
        when(vehicle).__getitem__("id").thenReturn(id)
        self.teslajson.vehicles = [vehicle]
        return vehicle

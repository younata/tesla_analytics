import json

from tesla_analytics.api import login_controller
from tests.api import APITestCase
from tests.test_worker import create_user


class LoginTests(APITestCase):
    blueprint = login_controller.blueprint

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
        self.assertIsNotNone(result.json.get("refresh_token"))

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


class RefreshTests(APITestCase):
    blueprint = login_controller.blueprint

    def setUp(self):
        super(RefreshTests, self).setUp()

        create_user()

        self.login_result = self.test_app.post(
            "/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "email": "me@example.com",
                "password": "test"
            })
        )

    def test_can_use_refresh_token_to_refresh_access_token(self):
        refresh_result = self.test_app.post(
            "/refresh",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.login_result.json["refresh_token"])
            }
        )

        self.assert200(refresh_result)

        self.assertIsNotNone(refresh_result.json["access_token"])
        self.assertNotEqual(refresh_result.json["access_token"], self.login_result.json["access_token"])
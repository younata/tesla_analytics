from typing import List, Callable

from tests.test_worker import create_user, create_vehicle


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
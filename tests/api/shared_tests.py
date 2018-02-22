from datetime import timedelta, datetime
from typing import List, Callable

from tests.test_worker import create_user, create_vehicle


def paginates_results() -> List[Callable]:
    def returns_results_in_timeframe(self):
        generated = self.generate_items(10)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&after={after}&before={before}".format(
                endpoint=self.endpoint,
                before=generated[2]["timestamp"],
                after=generated[7]["timestamp"],
            ),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[2:8])

    def returns_400_if_before_is_before_after(self):
        _ = self.generate_items(1)
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        five_minutes_from_now = datetime.now() + timedelta(minutes=5)

        assert five_minutes_ago < five_minutes_from_now

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&after={after}&before={before}".format(
                endpoint=self.endpoint,
                after=five_minutes_from_now.isoformat() + "Z",
                before=five_minutes_ago.isoformat() + "Z"
            ),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert400(result)
        self.assertEqual(result.json, {"error": "Before must be earlier than after"})

    def can_specify_all_items_before_certain_date(self):
        generated = self.generate_items(60)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&before={before}".format(endpoint=self.endpoint,
                                                                   before=generated[5]["timestamp"]),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[6:56])

    def items_before_date_are_paginated(self):
        generated = self.generate_items(60)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&before={before}&page=2".format(
                endpoint=self.endpoint,
                before=generated[5]["timestamp"]
            ),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[56:])

    def can_specify_all_items_after_certain_date(self):
        generated = self.generate_items(60)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&after={after}".format(
                endpoint=self.endpoint,
                after=generated[56]["timestamp"]
            ),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[:50])

    def items_after_date_are_paginated(self):
        generated = self.generate_items(60)

        result = self.test_app.get(
            "{endpoint}?vehicle_id=test_id&after={after}&page=2".format(
                endpoint=self.endpoint,
                after=generated[55]["timestamp"]
            ),
            headers={"AUTHORIZATION": "Bearer {}".format(self.access_token())}
        )

        self.assert200(result)
        self.assertListEqual(result.json, generated[50:55])

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

    return [returns_results_in_timeframe,
            returns_400_if_before_is_before_after,
            returns_latest_50_results,
            pages_results_by_50,
            sets_paging_headers_correctly_on_page_1,
            sets_paging_headers_correctly_on_middle_page,
            sets_paging_headers_correctly_on_last_page,
            can_specify_all_items_before_certain_date,
            items_before_date_are_paginated,
            can_specify_all_items_after_certain_date,
            items_after_date_are_paginated,
        ]


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
import datetime
import os
import tempfile
import unittest
import uuid

_test_directory = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(_test_directory.name, "planner-test.db")
os.environ["ENABLE_DEMO_DATA"] = "true"
os.environ["JWT_SECRET_KEY"] = "event-planner-regression-test-secret-32"

from backend.app import app


class EventPlannerApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.client.environ_base["REMOTE_ADDR"] = f"planner-test-{uuid.uuid4().hex}"

    def payload(self, **overrides):
        data = {
            "event_type": "wedding",
            "occasion": "Silver anniversary",
            "city": "Hyderabad",
            "guests": 100,
            "total_budget": 300000,
            "language": "en",
            "event_date": "",
        }
        data.update(overrides)
        return data

    def test_plan_returns_localized_sections_and_accepts_optional_fields(self):
        for language in ("en", "te", "hi"):
            with self.subTest(language=language):
                response = self.client.post(
                    "/api/ai/plan",
                    json=self.payload(language=language),
                )
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                plan = result["blueprint"]
                self.assertEqual(result["planner_mode"], "local_estimate")
                self.assertEqual(plan["language"], language)
                self.assertEqual(plan["occasion"], "Silver anniversary")
                self.assertEqual(len(plan["checklist"]), 4)
                self.assertTrue(plan["venue_suggestions"])
                self.assertTrue(plan["guest_arrangements"])
                self.assertTrue(plan["photography_suggestions"])
                self.assertTrue(plan["entertainment_suggestions"])
                self.assertEqual(
                    sum(item["amount"] for item in plan["itemized_budget"].values()),
                    plan["total_estimated_budget"],
                )
                self.assertLessEqual(plan["total_estimated_budget"], plan["total_budget"])

    def test_small_and_large_guest_counts_and_high_budget(self):
        for guests, budget in ((1, 100000), (50000, 1000000000)):
            with self.subTest(guests=guests):
                response = self.client.post(
                    "/api/ai/plan",
                    json=self.payload(guests=guests, total_budget=budget),
                )
                self.assertEqual(response.status_code, 200)
                plan = response.get_json()["blueprint"]
                self.assertEqual(plan["guests"], guests)
                self.assertLessEqual(plan["total_estimated_budget"], budget)
                self.assertEqual(
                    sum(item["amount"] for item in plan["itemized_budget"].values()),
                    plan["total_estimated_budget"],
                )

    def test_low_budget_caps_allocations_and_reports_shortfall(self):
        response = self.client.post(
            "/api/ai/plan",
            json=self.payload(total_budget=1),
        )

        self.assertEqual(response.status_code, 200)
        plan = response.get_json()["blueprint"]
        self.assertEqual(plan["total_estimated_budget"], 1)
        self.assertEqual(plan["budget_status"], "budget_insufficient")
        self.assertGreater(plan["budget_shortfall"], 0)
        self.assertEqual(sum(item["amount"] for item in plan["itemized_budget"].values()), 1)

    def test_city_packages_are_referenced_but_unmatched_city_is_not(self):
        matched = self.client.post(
            "/api/ai/plan",
            json=self.payload(city="Hyderabad"),
        ).get_json()["blueprint"]
        self.assertTrue(matched["recommended_vendors"])
        self.assertTrue(
            all("Hyderabad" in vendor["cities"] for vendor in matched["recommended_vendors"])
        )
        self.assertTrue(
            any(item["basis"] == "marketplace_listing" for item in matched["itemized_budget"].values())
        )

        unmatched = self.client.post(
            "/api/ai/plan",
            json=self.payload(city="A city without listings"),
        ).get_json()["blueprint"]
        self.assertEqual(unmatched["recommended_vendors"], [])
        self.assertTrue(
            all(item["basis"] == "indicative_planning_estimate" for item in unmatched["itemized_budget"].values())
        )
        wildcard_location = self.client.post(
            "/api/ai/plan",
            json=self.payload(city="%"),
        ).get_json()["blueprint"]
        self.assertEqual(wildcard_location["recommended_vendors"], [])

    def test_invalid_inputs_return_actionable_validation_errors(self):
        invalid_payloads = (
            (self.payload(guests=0), "Expected guests"),
            (self.payload(guests=True), "Expected guests"),
            (self.payload(total_budget=0), "Total budget"),
            (self.payload(language="fr"), "plan language"),
            (self.payload(event_date=(datetime.date.today() - datetime.timedelta(days=1)).isoformat()), "past"),
            (self.payload(venue_type=42), "Venue preference"),
        )
        for payload, message in invalid_payloads:
            with self.subTest(message=message, payload=payload):
                response = self.client.post("/api/ai/plan", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.get_json()["error"])

    def test_event_date_and_preferences_are_preserved(self):
        event_date = (datetime.date.today() + datetime.timedelta(days=60)).isoformat()
        response = self.client.post(
            "/api/ai/plan",
            json=self.payload(
                event_date=event_date,
                venue_type="outdoor garden",
                food_preference="vegetarian",
                decoration_preference="low-waste florals",
                theme_preference="garden",
            ),
        )

        self.assertEqual(response.status_code, 200)
        plan = response.get_json()["blueprint"]
        self.assertEqual(plan["event_date"], event_date)
        self.assertEqual(plan["preferences"]["venue_type"], "outdoor garden")
        self.assertTrue(any("outdoor garden" in item for item in plan["venue_suggestions"]))
        self.assertTrue(any("vegetarian" in item for item in plan["guest_arrangements"]))

    def test_planner_rate_limit_returns_retry_after(self):
        payload = self.payload()
        for _ in range(20):
            self.assertEqual(self.client.post("/api/ai/plan", json=payload).status_code, 200)

        response = self.client.post("/api/ai/plan", json=payload)
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)


if __name__ == "__main__":
    unittest.main()

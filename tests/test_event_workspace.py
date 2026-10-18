import os
import tempfile
import unittest
import uuid

_test_directory = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(_test_directory.name, "veduka-test.db")
os.environ["ENABLE_DEMO_DATA"] = "true"
os.environ["JWT_SECRET_KEY"] = "event-workspace-regression-test-secret-32"

from backend.app import app


class EventWorkspaceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def login_as_demo_customer(self):
        response = self.client.post(
            "/api/auth/login",
            json={"identifier": "customer@veduka.ai", "password": "customer123"},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.get_json()['token']}"}

    def test_event_details_include_database_budget(self):
        headers = self.login_as_demo_customer()
        response = self.client.get("/api/events", headers=headers)

        self.assertEqual(response.status_code, 200)
        events = response.get_json()["events"]
        self.assertEqual(len(events), 1)

        detail_response = self.client.get(
            f"/api/events/{events[0]['id']}", headers=headers
        )
        event = detail_response.get_json()["event"]
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(event["total_budget"], 500000)
        allocated_total = sum(
            item["allocated_amount"] for item in event["budget_breakdown"]
        )
        self.assertEqual(allocated_total, 500000)

    def test_empty_account_cannot_read_another_users_event(self):
        email = f"workspace-{uuid.uuid4().hex}@example.com"
        response = self.client.post(
            "/api/auth/register",
            json={
                "full_name": "Workspace Test User",
                "email": email,
                "password": "test-password-123",
                "role": "customer",
            },
        )

        self.assertEqual(response.status_code, 201)
        headers = {"Authorization": f"Bearer {response.get_json()['token']}"}
        events_response = self.client.get("/api/events", headers=headers)
        self.assertEqual(events_response.status_code, 200)
        self.assertEqual(events_response.get_json()["events"], [])

        detail_response = self.client.get("/api/events/1", headers=headers)
        self.assertEqual(detail_response.status_code, 403)

    def test_zero_budget_is_returned_without_replacing_it(self):
        headers = self.login_as_demo_customer()
        create_response = self.client.post(
            "/api/events",
            headers=headers,
            json={
                "title": "Zero Budget Test",
                "event_type": "celebration",
                "event_date": "2027-01-01",
                "city": "Hyderabad",
                "total_budget": 0,
            },
        )

        self.assertEqual(create_response.status_code, 201)
        event_id = create_response.get_json()["event_id"]
        detail_response = self.client.get(f"/api/events/{event_id}", headers=headers)
        event = detail_response.get_json()["event"]
        self.assertEqual(event["total_budget"], 0)
        self.assertTrue(all(item["allocated_amount"] == 0 for item in event["budget_breakdown"]))


if __name__ == "__main__":
    unittest.main()

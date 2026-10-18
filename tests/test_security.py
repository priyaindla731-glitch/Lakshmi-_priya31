import datetime
import hashlib
import os
import uuid
import unittest
from unittest.mock import patch

import jwt

from backend import auth
from backend.app import app
from backend.database import demo_data_enabled, get_db, hash_password, init_db


class SecurityApiTests(unittest.TestCase):
    password = "Test-only-password-41!"

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.suffix = uuid.uuid4().hex
        conn = get_db()
        cursor = conn.cursor()
        cls.users = {}

        for role in ("customer", "other_customer", "vendor", "other_vendor", "admin"):
            email = f"{role}-{cls.suffix}@example.test"
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
                """,
                (email, hash_password(cls.password), role.title(), "customer" if role.endswith("customer") else "vendor" if role.endswith("vendor") else role),
            )
            cls.users[role] = {"id": cursor.lastrowid, "email": email}

        cls.vendor_profiles = {}
        for role in ("vendor", "other_vendor"):
            cursor.execute(
                """
                INSERT INTO vendor_profiles (user_id, business_name, category, cities, bio_en)
                VALUES (?, ?, 'photography', 'Hyderabad', 'Test business')
                """,
                (cls.users[role]["id"], f"Business {role} {cls.suffix}"),
            )
            cls.vendor_profiles[role] = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO events (customer_id, title, event_type, event_date, city, venue, total_budget, special_notes)
            VALUES (?, ?, 'wedding', '2027-01-01', 'Hyderabad', 'Private venue', 200000, 'Private planning notes')
            """,
            (cls.users["customer"]["id"], f"Security event {cls.suffix}"),
        )
        cls.event_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO bookings (event_id, customer_id, vendor_id, service_category, total_amount, balance_amount)
            VALUES (?, ?, ?, 'photography', 50000, 35000)
            """,
            (cls.event_id, cls.users["customer"]["id"], cls.vendor_profiles["vendor"]),
        )
        cls.booking_id = cursor.lastrowid
        cls.qr_token = f"SECURITY-{cls.suffix.upper()}"
        cursor.execute(
            """
            INSERT INTO guests (event_id, full_name, phone, qr_code_token)
            VALUES (?, 'Private Guest', '5550100', ?)
            """,
            (cls.event_id, cls.qr_token),
        )
        cls.guest_id = cursor.lastrowid
        conn.commit()
        conn.close()

    def setUp(self):
        conn = get_db()
        conn.execute("DELETE FROM auth_rate_limits")
        conn.commit()
        conn.close()

    def login(self, role):
        response = self.client.post(
            "/api/auth/login",
            json={"identifier": self.users[role]["email"], "password": self.password},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        return {"Authorization": f"Bearer {response.get_json()['token']}"}

    def test_registration_and_role_switch_cannot_grant_admin(self):
        email = f"no-admin-{uuid.uuid4().hex}@example.test"
        response = self.client.post(
            "/api/auth/register",
            json={
                "full_name": "Not an administrator",
                "email": email,
                "password": self.password,
                "role": "admin",
            },
        )
        self.assertEqual(response.status_code, 400)
        conn = get_db()
        self.assertIsNone(conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone())
        conn.close()

        customer_headers = self.login("customer")
        response = self.client.post(
            "/api/auth/switch-role",
            headers=customer_headers,
            json={"role": "admin"},
        )
        self.assertEqual(response.status_code, 403, response.get_json())

        admin_headers = self.login("admin")
        response = self.client.post(
            "/api/auth/switch-role",
            headers=admin_headers,
            json={"role": "customer"},
        )
        self.assertEqual(response.status_code, 403)

    def test_role_boundaries_and_booking_ownership(self):
        other_customer = self.login("other_customer")
        response = self.client.get(
            f"/api/bookings/{self.booking_id}", headers=other_customer
        )
        self.assertEqual(response.status_code, 403)

        other_vendor = self.login("other_vendor")
        response = self.client.get(
            f"/api/bookings/{self.booking_id}", headers=other_vendor
        )
        self.assertEqual(response.status_code, 403)

        vendor = self.login("vendor")
        response = self.client.get(f"/api/bookings/{self.booking_id}", headers=vendor)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("customer_phone", response.get_json()["booking"])

        customer = self.login("customer")
        self.assertEqual(
            self.client.get(f"/api/bookings/{self.booking_id}", headers=customer).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/admin/overview", headers=customer).status_code, 403
        )
        self.assertEqual(
            self.client.get("/api/seller/dashboard", headers=customer).status_code, 403
        )
        self.assertEqual(
            self.client.get("/api/admin/overview", headers=self.login("admin")).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/quotations/request",
                headers=other_customer,
                json={"event_id": self.event_id, "vendor_id": self.vendor_profiles["vendor"]},
            ).status_code,
            403,
        )

        vendor_headers = self.login("vendor")
        switched = self.client.post(
            "/api/auth/switch-role",
            headers=vendor_headers,
            json={"role": "customer"},
        )
        self.assertEqual(switched.status_code, 200)
        switched_headers = {
            "Authorization": f"Bearer {switched.get_json()['token']}"
        }
        self.assertEqual(
            self.client.get(
                f"/api/bookings/{self.booking_id}", headers=switched_headers
            ).status_code,
            403,
        )
        conn = get_db()
        conn.execute(
            "UPDATE users SET role = 'vendor' WHERE id = ?",
            (self.users["vendor"]["id"],),
        )
        conn.commit()
        conn.close()

    def test_guest_list_and_qr_checkin_require_event_access(self):
        other_customer = self.login("other_customer")
        self.assertEqual(
            self.client.get(
                f"/api/events/{self.event_id}/guests", headers=other_customer
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/events/{self.event_id}/guests",
                headers=other_customer,
                json={"full_name": "Intruder"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/guests/check-in", json={"qr_code_token": self.qr_token}
            ).status_code,
            401,
        )

        other_vendor = self.login("other_vendor")
        self.assertEqual(
            self.client.post(
                "/api/guests/check-in",
                headers=other_vendor,
                json={"qr_code_token": self.qr_token},
            ).status_code,
            403,
        )
        vendor = self.login("vendor")
        checked_in = self.client.post(
            "/api/guests/check-in",
            headers=vendor,
            json={"qr_code_token": self.qr_token},
        )
        self.assertEqual(checked_in.status_code, 200)
        self.assertNotIn("qr_code_token", checked_in.get_json()["guest"])

        conn = get_db()
        guest = conn.execute(
            "SELECT checked_in FROM guests WHERE id = ?", (self.guest_id,)
        ).fetchone()
        conn.close()
        self.assertEqual(guest["checked_in"], 1)

    def test_vendor_workspace_and_public_profile_hide_private_fields(self):
        vendor_headers = self.login("vendor")
        workspace = self.client.get(
            f"/api/events/{self.event_id}", headers=vendor_headers
        )
        self.assertEqual(workspace.status_code, 200)
        event = workspace.get_json()["event"]
        self.assertNotIn("total_budget", event)
        self.assertNotIn("special_notes", event)
        self.assertEqual(event["guests"], [])
        self.assertEqual(len(event["bookings"]), 1)

        denied = self.client.get(
            f"/api/events/{self.event_id}/guests", headers=vendor_headers
        )
        self.assertEqual(denied.status_code, 403)

        vendor_id = self.vendor_profiles["vendor"]
        profile = self.client.get(f"/api/vendors/{vendor_id}").get_json()["vendor"]
        for private_field in ("user_id", "email", "phone"):
            self.assertNotIn(private_field, profile)

    def test_legacy_password_is_rehashed_after_successful_login(self):
        email = f"legacy-{uuid.uuid4().hex}@example.test"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, 'Legacy User', 'customer')",
            (email, hashlib.sha256(self.password.encode("utf-8")).hexdigest()),
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        response = self.client.post(
            "/api/auth/login",
            json={"identifier": email, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        conn = get_db()
        stored_hash = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()["password_hash"]
        conn.close()
        self.assertFalse(len(stored_hash) == 64)
        self.assertTrue(stored_hash.startswith(("scrypt:", "pbkdf2:")))

    def test_logout_revokes_token_and_expired_tokens_are_rejected(self):
        headers = self.login("customer")
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)
        self.assertEqual(
            self.client.get("/api/auth/me", headers=self.login("customer")).status_code,
            200,
        )

        expired = jwt.encode(
            {
                "user_id": self.users["customer"]["id"],
                "exp": datetime.datetime.utcnow() - datetime.timedelta(seconds=1),
            },
            auth.SECRET_KEY,
            algorithm="HS256",
        )
        response = self.client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {expired}"}
        )
        self.assertEqual(response.status_code, 401)

    def test_authentication_endpoints_rate_limit_repeated_attempts(self):
        env = {"REMOTE_ADDR": "203.0.113.77"}
        for _ in range(10):
            response = self.client.post(
                "/api/auth/login",
                json={"identifier": "missing@example.test", "password": "wrong"},
                environ_overrides=env,
            )
            self.assertEqual(response.status_code, 401)
        limited = self.client.post(
            "/api/auth/login",
            json={"identifier": "missing@example.test", "password": "wrong"},
            environ_overrides=env,
        )
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Retry-After", limited.headers)

        for index in range(5):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "full_name": "Attempt",
                    "email": f"admin-attempt-{index}-{self.suffix}@example.test",
                    "password": self.password,
                    "role": "admin",
                },
                environ_overrides=env,
            )
            self.assertEqual(response.status_code, 400)
        limited = self.client.post(
            "/api/auth/register",
            json={
                "full_name": "Attempt",
                "email": f"admin-attempt-limited-{self.suffix}@example.test",
                "password": self.password,
                "role": "customer",
            },
            environ_overrides=env,
        )
        self.assertEqual(limited.status_code, 429)

    def test_demo_data_cannot_be_enabled_in_production(self):
        with patch.dict(
            os.environ,
            {"ENABLE_DEMO_DATA": "true", "RENDER_SERVICE_ID": "production-service"},
        ):
            self.assertFalse(demo_data_enabled())

    def test_legacy_seeded_admin_is_demoted_without_deleting_account(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO users (email, password_hash, full_name, role)
            VALUES ('admin@veduka.ai', ?, 'Super Administrator', 'admin')
            """,
            (hash_password(self.password),),
        )
        user_id = cursor.lastrowid
        conn.commit()
        before_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        init_db()

        conn = get_db()
        user = conn.execute(
            "SELECT role, password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        after_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        self.assertEqual(user["role"], "customer")
        self.assertEqual(after_count, before_count)
        self.assertTrue(user["password_hash"].startswith(("scrypt:", "pbkdf2:")))
        response = self.client.post(
            "/api/auth/login",
            json={"identifier": "admin@veduka.ai", "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        headers = {"Authorization": f"Bearer {response.get_json()['token']}"}
        self.assertEqual(self.client.get("/api/admin/overview", headers=headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()

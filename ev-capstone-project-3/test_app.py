"""
Test suite for Flask Customer Support RAG Application.
Validates session start, multi-turn messaging, RAG retrieval, history persistence, and session termination.
"""

import os
import sys
import unittest
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

from app import app
import database


class TestSupportApp(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_01_index_page(self):
        """Verify home page loads successfully with HTML content."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"OmniSupport AI", response.data)
        self.assertIn(b"CloudSync Pro", response.data)

    def test_02_get_products(self):
        """Verify /api/products returns products list and metadata."""
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("products", data)
        self.assertIn("metadata", data)
        self.assertIn("CloudSync Pro", data["products"])
        self.assertIn("SecureAuth Gateway", data["products"])

    def test_03_start_session_with_query(self):
        """Verify session creation and RAG processing for initial query."""
        payload = {
            "name": "David Miller",
            "email": "david.miller@enterprise.org",
            "product": "SecureAuth Gateway",
            "initial_query": "Users cannot sign in via Okta SAML SSO. It says Audience URI mismatch."
        }
        response = self.client.post(
            "/api/sessions/start",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("session", data)
        self.assertIn("messages", data)

        session = data["session"]
        session_id = session["session_id"]
        self.assertEqual(session["customer_name"], "David Miller")
        self.assertEqual(session["status"], "active")

        # Check that messages include user query and AI response
        messages = data["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["sender"], "user")
        self.assertEqual(messages[1]["sender"], "assistant")
        self.assertTrue(len(messages[1]["message"]) > 50)
        
        # Check that RAG sources were returned
        sources = messages[1].get("rag_sources", [])
        self.assertTrue(len(sources) > 0)
        codes = [s["ticket_code"] for s in sources]
        self.assertIn("SAG-301", codes)

    def test_04_session_lifecycle_multi_turn_and_end(self):
        """Verify multi-turn conversation, history persistence, and ending session."""
        # 1. Start session
        start_payload = {
            "name": "Sarah Connor",
            "email": "sarah@cyberdyne.io",
            "product": "CloudSync Pro",
            "initial_query": "My desktop client is stuck on 'Connecting to sync engine' on macOS."
        }
        res_start = self.client.post("/api/sessions/start", data=json.dumps(start_payload), content_type="application/json")
        self.assertEqual(res_start.status_code, 200)
        session_id = res_start.get_json()["session"]["session_id"]

        # 2. Send follow-up question
        followup_payload = {
            "message": "Where can I find the lock file to delete it on Mac?"
        }
        res_msg = self.client.post(
            f"/api/sessions/{session_id}/message",
            data=json.dumps(followup_payload),
            content_type="application/json"
        )
        self.assertEqual(res_msg.status_code, 200)
        msg_data = res_msg.get_json()
        self.assertTrue(msg_data["success"])
        self.assertIn("assistant_message", msg_data)
        reply = msg_data["assistant_message"]["message"]
        self.assertTrue("sync.lock" in reply or "Library" in reply or "Terminal" in reply)

        # 3. Verify conversation history retrieval
        res_hist = self.client.get(f"/api/sessions/{session_id}")
        self.assertEqual(res_hist.status_code, 200)
        hist_data = res_hist.get_json()
        self.assertEqual(len(hist_data["messages"]), 4)  # 2 user msgs + 2 bot msgs

        # 4. End session
        res_end = self.client.post(f"/api/sessions/{session_id}/end")
        self.assertEqual(res_end.status_code, 200)
        self.assertEqual(res_end.get_json()["session"]["status"], "ended")

        # 5. Verify cannot send message to ended session
        res_blocked = self.client.post(
            f"/api/sessions/{session_id}/message",
            data=json.dumps({"message": "Can I still ask something?"}),
            content_type="application/json"
        )
        self.assertEqual(res_blocked.status_code, 400)
        self.assertIn("closed", res_blocked.get_json()["error"])

    def test_05_list_sessions(self):
        """Verify session listing endpoint returns past sessions."""
        response = self.client.get("/api/sessions")
        self.assertEqual(response.status_code, 200)
        sessions = response.get_json()["sessions"]
        self.assertIsInstance(sessions, list)
        self.assertTrue(len(sessions) >= 2)

    def test_06_historical_tickets(self):
        """Verify historical tickets API endpoint."""
        response = self.client.get("/api/historical-tickets?product=DevFlow%20CI/CD")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total"], 7)
        self.assertEqual(data["tickets"][0]["product"], "DevFlow CI/CD")


if __name__ == "__main__":
    unittest.main()

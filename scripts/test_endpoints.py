#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app

def test_flow():
    with TestClient(app) as client:
        # 1. Test Health Check
        print("Testing /api/health...")
        res = client.get("/api/health")
        print(f"Health status: {res.status_code}, body: {res.json()}")
        assert res.status_code == 200
        
        # 2. Test Create Conversation
        print("\nTesting POST /api/conversations (creating an English conversation)...")
        res = client.post("/api/conversations", json={
            "language": "English",
            "topic": "Ordering food"
        })
        print(f"Create conversation status: {res.status_code}")
        conv_data = res.json()
        print(f"Created conversation: {conv_data}")
        assert res.status_code == 201
        assert "id" in conv_data
        conv_id = conv_data["id"]
        
        # 3. Test Post Message with grammar error
        print(f"\nTesting POST /api/conversations/{conv_id}/messages (sending a message with an error)...")
        user_message = "Hello, I wants a coffee."
        res = client.post(f"/api/conversations/{conv_id}/messages", json={
            "text": user_message
        })
        print(f"Post message status: {res.status_code}")
        reply_data = res.json()
        print("Reply response:")
        print(json.dumps(reply_data, indent=2))
        assert res.status_code == 200
        assert "reply" in reply_data
        assert "feedback" in reply_data
        assert reply_data["feedback"]["has_errors"] is True
        
        # 4. Verify Database state
        print(f"\nTesting GET /api/conversations/{conv_id}/messages...")
        res = client.get(f"/api/conversations/{conv_id}/messages")
        print(f"Get messages status: {res.status_code}")
        history_data = res.json()
        print("Conversation Messages History in DB:")
        print(json.dumps(history_data, indent=2))
        assert res.status_code == 200
        assert len(history_data["messages"]) == 2
        assert history_data["messages"][0]["role"] == "user"
        assert history_data["messages"][0]["feedback"]["has_errors"] is True
        assert history_data["messages"][1]["role"] == "assistant"
        
        print("\n🎉 ALL TESTS PASSED! SQLite + LLM client + Prompts + Parallel processing working end-to-end.")

if __name__ == "__main__":
    test_flow()

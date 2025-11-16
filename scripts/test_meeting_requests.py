# scripts/test_meeting_request.py
import requests

def main():
    payload = {
        "owner_id": "am-123",
        "title": "Intro call with Alta",
        "duration_minutes": 30,
        "window_start": "2025-01-01T09:00:00",
        "window_end": "2025-01-01T11:00:00",
        "max_bookings": 3,
    }

    resp = requests.post("http://127.0.0.1:8000/meeting-requests/simple", json=payload)
    print("Status:", resp.status_code)
    print(resp.json())

if __name__ == "__main__":
    main()
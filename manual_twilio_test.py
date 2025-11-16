import requests


def main():
    url = "http://127.0.0.1:8000/twilio/voice"

    data = {
        "CallSid": "CA123",
        "From": "+15551234567",
        "To": "+15557654321",
    }

    resp = requests.post(url, data=data)
    print("Status:", resp.status_code)
    print("Headers:", resp.headers.get("content-type"))
    print("Body:", resp.text)


if __name__ == "__main__":
    main()

import requests


def main():
    url = "http://127.0.0.1:8000/calls/test"

    resp = requests.post(url, json={
        "phone": "+972546688243",
        "name": "Elyashiv"
    })

    print("Status:", resp.status_code)
    print("Body:", resp.text)


if __name__ == "__main__":
    main()

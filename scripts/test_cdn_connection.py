import socket

import requests
import urllib3.util.connection


IMAGE_URL = "https://static.wikia.nocookie.net/forzamotorsport/images/e/e1/FH6_Abarth_595_esseesse.png/revision/latest?cb=20260516171717"


def main():
    print("Addresses Python sees:")

    addresses = socket.getaddrinfo(
        "static.wikia.nocookie.net",
        443,
        type=socket.SOCK_STREAM,
    )

    for address in addresses:
        print(address)

    print("\nTrying Requests with IPv4 only...")

    # urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

    response = requests.get(
        IMAGE_URL,
        timeout=15,
    )

    print("Status:", response.status_code)
    print("Content type:", response.headers.get("content-type"))
    print("Downloaded bytes:", len(response.content))


if __name__ == "__main__":
    main()
import requests

from config.caizhanyun_config import CAIZHANYUN_CONFIG


URL = f"{CAIZHANYUN_CONFIG['detail_url']}/lottery-store/api/prescient-hall/order/info"


def main():
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    data = {
        "token": CAIZHANYUN_CONFIG["token"],
        "orderId": "P20260823000001123212",
    }

    response = requests.post(
        URL,
        headers=headers,
        json=data,
        timeout=15,
    )

    print(response.status_code)
    print(response.text[:3000])


if __name__ == "__main__":
    main()

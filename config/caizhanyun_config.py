import os


VERIFIED_CAIZHANYUN_STORE_ID = "ds711"
VERIFIED_CAIZHANYUN_REQUEST_USER_ID = "260610"


def get_caizhanyun_config(environment=None):
    values = os.environ if environment is None else environment
    store_id = str(
        values.get("CAIZHANYUN_STORE_ID")
        or VERIFIED_CAIZHANYUN_STORE_ID
    ).strip()

    return {
        "base_url": "https://usergw.magicangle.cn",
        "detail_url": "https://userapi.magicangle.cn",
        "token": str(
            values.get("CAIZHANYUN_TOKEN") or ""
        ).strip(),
        "cookie": str(
            values.get("CAIZHANYUN_COOKIE") or ""
        ).strip(),
        "store_id": store_id,
        "request_user_id": VERIFIED_CAIZHANYUN_REQUEST_USER_ID,
    }


CAIZHANYUN_CONFIG = get_caizhanyun_config()

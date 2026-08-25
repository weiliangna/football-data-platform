import os


CAIZHANYUN_CONFIG = {
    "base_url": "https://usergw.magicangle.cn",
    "detail_url": "https://userapi.magicangle.cn",
    "token": os.getenv("CAIZHANYUN_TOKEN", "").strip(),
    "cookie": os.getenv("CAIZHANYUN_COOKIE", "").strip(),
}

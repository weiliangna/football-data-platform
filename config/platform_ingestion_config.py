import os


class MissingPlatformConfig(RuntimeError):
    pass


class SourceContractUnavailable(RuntimeError):
    pass


def _value(environment, name, default=""):
    return str(environment.get(name) or default).strip()


def get_zhouyunbao_config(environment=None):
    values = os.environ if environment is None else environment
    return {
        "token": _value(values, "ZHOUYUNBAO_TOKEN"),
        "store_id": _value(
            values,
            "ZHOUYUNBAO_STORE_ID",
            "ds1038",
        ),
        "bootstrap_user_id": _value(
            values,
            "ZHOUYUNBAO_BOOTSTRAP_USER_ID",
            "93",
        ),
        "login_url": (
            "https://userapi.cfkjmagic.top/"
            "login/api/foundation/loginByToken"
        ),
        "list_url": (
            "https://usergw.cfkjmagic.top/"
            "store/api/prescient-hall/order/recommend/list"
        ),
        "detail_url": (
            "https://userapi.cfkjmagic.top/"
            "lottery-store/api/prescient-hall/order/info"
        ),
    }


def get_yuncai_config(environment=None):
    values = os.environ if environment is None else environment
    return {
        "authorization": _value(values, "YUNCAI_AUTHORIZATION"),
        "cookie": _value(values, "YUNCAI_COOKIE"),
        "x_ca_key": _value(values, "YUNCAI_X_CA_KEY"),
        "base_url": "https://ycahdtoquick03.sadsdh.com",
        "hall_path": "/prod-api/order/order/track/hall",
        "detail_path": (
            "/prod-api/order/orderDetail/tracking/order/item"
        ),
        "profile_path": "/prod-api/order/order/track/achievements",
        "user_orders_path": "/prod-api/order/order/user/order/list",
    }


def get_haodianzhu_config(environment=None):
    values = os.environ if environment is None else environment
    return {
        "sid": _value(values, "HAODIANZHU_SID"),
        "uuid": _value(values, "HAODIANZHU_UUID"),
        "cookie": _value(values, "HAODIANZHU_COOKIE"),
        "shop_id": _value(
            values,
            "HAODIANZHU_SHOP_ID",
            "7876",
        ),
        "url": "https://bbbkzu.haodianzhu.com.cn/router/rest",
    }


def get_qishilu_config(environment=None):
    values = os.environ if environment is None else environment
    return {
        "authorization": _value(
            values,
            "QISHILU_AUTHORIZATION",
        ),
        "base_url": "https://apisaasgatewayhz.htycp.cn",
    }


def require_values(config, platform_name, names):
    missing = [name for name in names if not config.get(name)]
    if missing:
        labels = ", ".join(missing)
        raise MissingPlatformConfig(
            f"{platform_name} 缺少安全环境配置: {labels}"
        )
    return config

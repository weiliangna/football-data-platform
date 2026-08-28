from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation


FIRST_ORDER_TAG_CONFIG = {
    "exact_amounts": {
        Decimal("100"): {
            "confirmed": "NEW_FIRST_ORDER_100",
            "suspected": "SUSPECTED_FIRST_ORDER_100",
        },
        Decimal("200"): {
            "confirmed": "NEW_FIRST_ORDER_200",
            "suspected": "SUSPECTED_FIRST_ORDER_200",
        },
    },
    "low_amount_max": Decimal("200"),
    "observe_days": 7,
    "observe_max_orders": 3,
}


def decimal_amount(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def build_first_order_profile(
    amount,
    first_order_time,
    lifetime_orders,
    *,
    history_complete=False,
    now=None,
):
    current_time = now or datetime.now()
    first_amount = decimal_amount(amount)
    confidence = "confirmed" if history_complete else "suspected"
    tags = []

    exact = FIRST_ORDER_TAG_CONFIG["exact_amounts"].get(first_amount)
    if exact:
        tags.append(exact[confidence])

    if (
        history_complete
        and Decimal("0") < first_amount <= FIRST_ORDER_TAG_CONFIG["low_amount_max"]
    ):
        tags.append("NEW_FIRST_ORDER_LOW_AMOUNT")

    observe_start = current_time - timedelta(
        days=FIRST_ORDER_TAG_CONFIG["observe_days"]
    )
    if (
        first_order_time
        and 0 < int(lifetime_orders or 0) <= FIRST_ORDER_TAG_CONFIG["observe_max_orders"]
        and observe_start <= first_order_time <= current_time
    ):
        tags.append("NEW_ACCOUNT_OBSERVE")

    return {
        "first_order_amount": float(first_amount),
        "first_order_time": first_order_time,
        "first_order_confidence": confidence,
        "auto_tags": tags,
    }

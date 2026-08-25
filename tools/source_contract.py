import re
from datetime import datetime, timezone


REDACTED = "[REDACTED]"
REDACTED_JWT = "[REDACTED_JWT]"

JWT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+"
    r"(?:\.[A-Za-z0-9_-]+){1,2}",
    re.IGNORECASE,
)
AUTHORIZATION_PATTERN = re.compile(
    r"(\bAuthorization\b\s*[:=]\s*)"
    r"(?:Bearer\s+)?(?:\"[^\"]*\"|'[^']*'|[^\s,]+)",
    re.IGNORECASE,
)
COOKIE_PATTERN = re.compile(
    r"(\bCookie\b\s*[:=]\s*)[^\r\n]*",
    re.IGNORECASE,
)
ASSIGNMENT_PATTERN = re.compile(
    r"(\b[A-Za-z0-9_]*(?:token|password|passwd|secret)"
    r"[A-Za-z0-9_]*\b\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;&]+)",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(
    r"(\bBearer\s+)[A-Za-z0-9._~+/-]+",
    re.IGNORECASE,
)
DATABASE_URI_PATTERN = re.compile(
    r"((?:mysql|mariadb)(?:\+[A-Za-z0-9_]+)?://)"
    r"([^\s/:]+):([^\s/@]+)@",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
)

SECRET_KEY_PARTS = (
    "token",
    "cookie",
    "password",
    "passwd",
    "secret",
    "authorization",
)
PERSONAL_KEYS = {
    "userid",
    "user_id",
    "starterid",
    "starter_id",
    "openid",
    "open_id",
    "unionid",
    "union_id",
    "nickname",
    "nick_name",
    "username",
    "user_name",
    "statername",
    "startername",
    "phone",
    "mobile",
    "telephone",
    "tel",
    "idcard",
    "id_card",
    "identity",
    "identity_no",
    "account",
    "account_id",
}
AVATAR_KEYS = {
    "headpic",
    "head_pic",
    "userpic",
    "user_pic",
    "avatar",
    "avatarurl",
    "avatar_url",
}
PERSON_CONTEXT = {
    "user",
    "userinfo",
    "user_info",
    "starter",
    "starterinfo",
    "starter_info",
    "member",
    "memberinfo",
    "member_info",
    "account",
    "profile",
}

TIME_KEYWORDS = (
    "time",
    "date",
    "start",
    "stop",
    "end",
    "deadline",
    "close",
    "sale",
    "publish",
    "create",
    "kickoff",
)
TIME_EXACT_FIELDS = {
    "day",
    "week",
}
MATCH_KEYWORDS = (
    "match",
    "teamid",
    "team_id",
    "week_name",
    "weekname",
    "matchid",
    "match_id",
    "matchcode",
    "match_code",
)
HANDICAP_KEYWORDS = (
    "letpoint",
    "handicap",
    "rq_number",
    "rqnumber",
)
AVATAR_KEYWORDS = (
    "headpic",
    "head_pic",
    "userpic",
    "user_pic",
    "avatar",
)


def sensitive_replacement(match):
    marker = (
        REDACTED_JWT
        if JWT_PATTERN.search(match.group(0))
        else REDACTED
    )
    return match.group(1) + marker


def redact_text(value):
    text = "" if value is None else str(value)
    text = AUTHORIZATION_PATTERN.sub(
        sensitive_replacement,
        text,
    )
    text = COOKIE_PATTERN.sub(
        lambda match: match.group(1) + REDACTED,
        text,
    )
    text = ASSIGNMENT_PATTERN.sub(
        sensitive_replacement,
        text,
    )
    text = BEARER_PATTERN.sub(
        sensitive_replacement,
        text,
    )
    text = JWT_PATTERN.sub(REDACTED_JWT, text)
    text = DATABASE_URI_PATTERN.sub(
        lambda match: match.group(1) + REDACTED + "@",
        text,
    )
    text = EMAIL_PATTERN.sub(REDACTED, text)
    return text


def normalize_key(value):
    return re.sub(
        r"[^a-z0-9_]",
        "",
        str(value or "").strip().lower(),
    )


def path_segments(path):
    return [
        normalize_key(item)
        for item in path
        if not isinstance(item, int)
    ]


def is_secret_key(key):
    normalized = normalize_key(key)
    return any(
        part in normalized
        for part in SECRET_KEY_PARTS
    )


def is_personal_key(key, path):
    normalized = normalize_key(key)

    if normalized in PERSONAL_KEYS:
        return True

    if normalized in AVATAR_KEYS:
        return True

    context = set(path_segments(path[:-1]))
    if normalized in {"id", "name"} and context & PERSON_CONTEXT:
        return True

    return False


def redact_structure(value):
    if isinstance(value, dict):
        return {
            key: redact_structure(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            redact_structure(item)
            for item in value
        ]

    if isinstance(value, str) and JWT_PATTERN.search(value):
        return REDACTED_JWT

    return REDACTED


def sanitize_json(value, path=()):
    if isinstance(value, dict):
        sanitized = {}

        for key, item in value.items():
            next_path = path + (str(key),)

            if is_secret_key(key) or is_personal_key(
                key,
                next_path,
            ):
                sanitized[key] = redact_structure(item)
                continue

            sanitized[key] = sanitize_json(
                item,
                next_path,
            )

        return sanitized

    if isinstance(value, list):
        return [
            sanitize_json(
                item,
                path + (index,),
            )
            for index, item in enumerate(value)
        ]

    if isinstance(value, str):
        return redact_text(value)

    return value


def observed_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "string"


def json_path(path):
    result = "$"

    for item in path:
        if isinstance(item, int):
            result += "[]"
        else:
            result += "." + str(item)

    return result


def sample_value(value):
    if isinstance(value, str):
        return value[:200]
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return value
    return None


def classify_field(field_name):
    normalized = normalize_key(field_name)

    categories = []

    if (
        any(keyword in normalized for keyword in TIME_KEYWORDS)
        or normalized in TIME_EXACT_FIELDS
    ):
        categories.append("time_candidates")

    if any(
        keyword in normalized
        for keyword in MATCH_KEYWORDS
    ):
        categories.append("match_identity_candidates")

    if any(
        keyword in normalized
        for keyword in HANDICAP_KEYWORDS
    ):
        categories.append("handicap_candidates")

    if any(
        keyword in normalized
        for keyword in AVATAR_KEYWORDS
    ):
        categories.append("avatar_candidates")

    return categories


def build_source_contract(
    platform,
    payload,
    orders_sampled=0,
    captured_at=None,
):
    sanitized = sanitize_json(payload)
    fields = {}
    categories = {
        "time_candidates": [],
        "match_identity_candidates": [],
        "handicap_candidates": [],
        "avatar_candidates": [],
    }
    category_seen = {
        key: set()
        for key in categories
    }
    unknown_fields = []
    unknown_seen = set()

    def visit(value, path=()):
        if isinstance(value, dict):
            for key, item in value.items():
                current_path = path + (str(key),)
                field_path = json_path(current_path)
                field_type = observed_type(item)
                entry = fields.setdefault(
                    str(key),
                    {
                        "json_paths": [],
                        "observed_types": [],
                        "occurrences": 0,
                    },
                )
                entry["occurrences"] += 1

                if field_path not in entry["json_paths"]:
                    entry["json_paths"].append(field_path)
                if field_type not in entry["observed_types"]:
                    entry["observed_types"].append(field_type)

                matched = classify_field(key)

                if not isinstance(item, (dict, list)):
                    for category in matched:
                        identity = (str(key), field_path)
                        if identity in category_seen[category]:
                            continue
                        category_seen[category].add(identity)
                        categories[category].append(
                            {
                                "field_name": str(key),
                                "json_path": field_path,
                                "sample_value": sample_value(item),
                                "observed_type": field_type,
                                "semantic_status": "unknown",
                            }
                        )

                if not matched:
                    identity = (str(key), field_path)
                    if identity not in unknown_seen:
                        unknown_seen.add(identity)
                        unknown_fields.append(
                            {
                                "field_name": str(key),
                                "json_path": field_path,
                                "observed_type": field_type,
                            }
                        )

                visit(item, current_path)

        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path + (index,))

    visit(sanitized)

    for entry in fields.values():
        entry["json_paths"].sort()
        entry["observed_types"].sort()

    return {
        "platform": str(platform),
        "captured_at": (
            captured_at
            or datetime.now(timezone.utc).isoformat()
        ),
        "orders_sampled": int(orders_sampled),
        "fields": dict(sorted(fields.items())),
        "time_candidates": categories["time_candidates"],
        "match_identity_candidates": categories[
            "match_identity_candidates"
        ],
        "handicap_candidates": categories[
            "handicap_candidates"
        ],
        "avatar_candidates": categories[
            "avatar_candidates"
        ],
        "unknown_fields": unknown_fields,
    }

import re

CARDNO_RE = re.compile(r"h[A-Z]{2}\d{2}-\d{3}", re.I)

TAG_ALIAS = {
    "동물귀": ["인권없음"],
    "인권없음": ["동물귀"],
}

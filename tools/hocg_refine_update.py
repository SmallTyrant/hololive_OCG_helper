def normalize_raw_text(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    i = 0

    MERGE_LABELS = {"カードタイプ", "レアリティ", "色", "LIFE", "HP"}

    ALL_LABELS = set(MERGE_LABELS) | {
        "タグ", "推しスキル", "SP推しスキル", "Bloomレベル",
        "アーツ", "バトンタッチ", "エクストラ",
        "イラストレーター名", "カードナンバー", "収録商品"
    }

    section_start_re = re.compile(
        r"^(カードタイプ|レアリティ|色|LIFE|HP|推しスキル|SP推しスキル|"
        r"Bloomレベル|アーツ|バトンタッチ|エクストラ|"
        r"イラストレーター名|カードナンバー)"
    )

    while i < len(lines):
        line = lines[i]

        # 라벨 + 값 병합 (다음 줄이 라벨이면 병합 금지)
        if line in MERGE_LABELS and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt in ALL_LABELS:
                out.append(line)
                i += 1
                continue
            out.append(f"{line} {nxt}")
            i += 2
            continue

        # 収録商品 섹션 제거
        if line == "収録商品":
            i += 1
            while i < len(lines) and not section_start_re.match(lines[i]):
                i += 1
            continue

        out.append(line)
        i += 1

    return "\n".join(out).strip() + "\n"

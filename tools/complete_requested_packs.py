"""Collect source evidence and complete the three requested card packs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup
import hocg_tool2 as official
import namuwiki_ko_import as namu

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "pack_verification_sources"
PACKS = {"hBP08": "바운서 바운드", "hEB01": "서머 홀로그램", "hBP09": "볼륨 볼텍스"}
BASE = "https://hololive-official-cardgame.com"
ICON_KO = {"W": "백", "G": "녹", "R": "적", "B": "청", "P": "자", "Y": "황", "C": "무색", "N": "무색"}


def with_icons(soup, korean=False):
    for node in soup.select("noscript,script,style"):
        node.decompose()
    for image in soup.select("img[alt]"):
        alt = image.get("alt", "")
        if korean:
            match = re.fullmatch(r"홀로(?:아츠|옐) ([WGRBPYCN])", alt)
            if match:
                image.insert_before("[" + ICON_KO[match[1]] + "]")
                image.unwrap()
        elif "texticon/" in image.get("src", ""):
            image.insert_before("[" + alt + "]")
            image.unwrap()
    return soup


def parse_official_list(html, code):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for anchor in soup.select("a[href*='cardlist/?id=']"):
        number = anchor.select_one(".number")
        name = anchor.select_one(".name")
        if number is None or name is None:
            continue
        card = number.get_text(strip=True)
        detail_id = int(re.search(r"[?&]id=(\d+)", anchor["href"])[1])
        img = anchor.select_one(".img img")
        image_url = urljoin(BASE, img["src"])
        anchor = with_icons(anchor)
        fields = {}
        for dt in anchor.select("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                fields[dt.get_text(strip=True)] = dd.get_text(" ", strip=True)
        effects = []
        for block in anchor.select(".skill,.arts,.keyword,.extra"):
            effects.append(block.get_text("\n", strip=True))
        if fields.get("能力テキスト"):
            effects.insert(0, fields["能力テキスト"])
        rows.append(dict(card_number=card, name=name.get_text(strip=True),
                         card_type=fields.get("カードタイプ", ""), rarity=fields.get("レアリティ", ""),
                         color=fields.get("色", "").replace("[", "").replace("]", "").replace(" ", "/"),
                         product=fields.get("収録商品", "").split("【")[0].strip(),
                         tags=fields.get("タグ", "").split(), image_url=image_url,
                         detail_id=detail_id, detail_url=BASE + "/cardlist/?id=" + str(detail_id),
                         set_code=card.split("-")[0], raw_text="\n".join(effects), expansion=code,
                         html=str(anchor)))
    return rows


def parse_namu_detail(html, url, expected_names=None):
    soup = with_icons(BeautifulSoup(html, "html.parser"), korean=True)
    rows = {}
    for table in soup.select("table"):
        # Summary tables have several cards; only use individual card tables.
        numbers = {m.group(0).upper() for m in namu.CARDNO_RE.finditer(table.get_text(" ", strip=True))}
        context_card = namu.infer_card_number_from_table_context(table)
        if len(numbers) > 1 or (not numbers and not context_card):
            continue
        card = next(iter(numbers)) if numbers else context_card
        # These observed table numbers are typos, confirmed against official
        # names, Bloom levels and arts. Other tables may follow an older heading.
        verified_number_typos = {('HBP02-026','HBP02-027'),('HBP09-049','HBP09-050'),
                                 ('HBP09-036','HBP09-037'),('HBP09-064','HBP09-065')}
        if not numbers or (card,context_card) in verified_number_typos:
            card = context_card
        trs = [tr for tr in table.select("tr") if tr.find_parent("table") is table]
        if not trs:
            continue
        first = trs[0].find(["td", "th"])
        if first is None or not first.get_text(strip=True):
            continue
        if len(trs) < 2 or not any(x in trs[1].get_text() for x in ("홀로멤", "서포트", "옐")):
            continue
        name = first.get_text("\n", strip=True).splitlines()[0]
        name = re.sub(r"\{\{\{[+-]?\d+\s*([^{}]+)\}\}?", r"\1", name)
        name = namu.sanitize_ko_name(name)
        if not name or namu._is_bad_name(name):
            continue
        # Some support tables contain a copied, incorrect card number.
        # Only remap against an unambiguous name in the requested inventories.
        all_expected = set().union(*expected_names.values()) if expected_names else set()
        is_support = len(trs) > 1 and trs[1].get_text(strip=True).startswith("서포트")
        if is_support and card not in all_expected and expected_names and name in expected_names and len(expected_names[name]) == 1:
            if card not in expected_names[name]:
                card = next(iter(expected_names[name]))
        lines = []
        skip_next = False
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"], recursive=False)]
            if skip_next:
                skip_next = False
                continue
            text = " ".join(c for c in cells if c).strip()
            if sum(c.lower() in {"레벨", "속성", "hp", "배턴 터치"} for c in cells) >= 2:
                skip_next = True
                continue
            if text in {"홀로멤", "오시 홀로멤", "속성"} or re.match(r"^(카드 넘버|카드번호|수록 팩|레어도)", text):
                continue
            if text.startswith("#"):
                continue
            if namu.CARDNO_RE.search(text):
                continue
            if text:
                lines.append(text)
        effect = "\n".join(lines)
        effect = re.sub(r"\{\{\{(?:#[^\s]+|[+-]\d+)\s*([^{}]+)\}\}?", r"\1", effect)
        effect = re.sub(r"\[파일:[^\]\n]*아츠\s+N[^\]\n]*\]\]?", "[무색]", effect)
        effect = re.sub(r"^(서포트\s*/[^\n]+)\n", "", effect)
        if len(effect) < 8:
            continue
        rows[card] = dict(name=name, effect=effect, source_url=url)
    return rows


def collect():
    expected = {}
    links = set()
    for code, title in PACKS.items():
        url = "https://namu.wiki/w/" + quote(title)
        soup = BeautifulSoup(fetch(url), "html.parser")
        cards = {}
        for table in soup.select("table"):
            if not all(x in table.get_text() for x in ("카드넘버", "카드명", "레어도")):
                continue
            for tr in table.select("tr"):
                cells = tr.find_all(["td", "th"], recursive=False)
                if len(cells) < 6:
                    continue
                card = cells[0].get_text(strip=True)
                if not namu.CARDNO_RE.fullmatch(card):
                    continue
                cards[card] = dict(name=cells[1].get_text(" ", strip=True), type=cells[2].get_text(" ", strip=True),
                                   rarity=" ".join(c.get_text(" ", strip=True) for c in cells[5:]))
                for a in cells[1].select("a[href]"):
                    link = urljoin("https://namu.wiki", a["href"]).split("#")[0]
                    if "/w/" in link:
                        links.add(link)
        if not cards:
            raise RuntimeError("No NamuWiki inventory: " + url)
        expected[code] = cards
        links.add(url + "/" + quote("카드"))
        print("INVENTORY", code, len(cards), flush=True)
    pages = []
    for code in PACKS:
        first_url = official.build_list_url(code, 1, "page")
        first = fetch(first_url)
        total = official.detect_total_count(first)
        if not total:
            raise RuntimeError("No official total: " + code)
        pages.append((code, first_url))
        for page in range(2, math.ceil(total / 15) + 1):
            pages.append((code, f"{BASE}/cardlist/cardsearch_ex?expansion={code}&view=text&page={page}"))
    def read_official(item):
        code, url = item
        return code, parse_official_list(fetch(url), code)
    rows = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for code, parsed in pool.map(read_official, pages):
            rows.extend(parsed)
    for code in PACKS:
        variants = [r for r in rows if r["expansion"] == code]
        total = official.detect_total_count(fetch(official.build_list_url(code, 1, "page")))
        if len({r["detail_id"] for r in variants}) != total:
            raise RuntimeError(f"Incomplete official pagination {code}: {len(variants)} / {total}")
        missing = set(expected[code]) - {r["card_number"] for r in variants}
        if missing:
            raise RuntimeError(f"Missing official cards {code}: {sorted(missing)}")
        print("OFFICIAL COMPLETE", code, "variants", len(variants), "cards", len({r['card_number'] for r in variants}), flush=True)
    translations = {}
    expected_names = {}
    for cards in expected.values():
        for card, info in cards.items():
            expected_names.setdefault(info["name"], set()).add(card.upper())
    def read_namu(url):
        return url, parse_namu_detail(fetch(url), url, expected_names)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for url, parsed in pool.map(read_namu, sorted(links)):
            translations.update(parsed)
            print("TRANSLATIONS", unquote(url.rsplit("/w/", 1)[-1]), len(parsed), flush=True)
    data = dict(expected=expected, official=rows, translations=translations)
    out = CACHE / "collected.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = sorted({r['card_number'].upper() for r in rows} - set(translations))
    print("TRANSLATION SOURCE MISSING", missing, flush=True)
    print("COLLECTED", out, flush=True)
    return data


COLOR_KO = {"白": "백", "緑": "녹", "赤": "적", "青": "청", "紫": "자", "黄": "황", "無色": "무색"}
TYPE_KO = {"推しホロメン": "오시 홀로멤", "ホロメン": "홀로멤", "Buzzホロメン": "Buzz 홀로멤", "エール": "옐",
           "サポート": "서포트", "アイテム": "아이템", "イベント": "이벤트", "ツール": "툴", "スタッフ": "스태프", "ファン": "팬", "マスコット": "마스코트"}
TAG_KO = {"#歌": "#노래", "#絵": "#그림", "#ケモミミ": "#동물귀", "#トリ": "#새", "#お酒": "#술", "#料理": "#요리",
          "#食べ物": "#음식", "#シューター": "#슈터", "#ゲーマーズ": "#게이머즈", "#秘密結社holoX": "#비밀 결사 holoX",
          "#ハーフエルフ": "#하프엘프", "#ベイビー": "#베이비", "#サマー": "#서머", "#ラミィのお酒": "#라미의 술",
          "#カエラ'sアームズ": "#카엘라's 암즈", "#コヨラボ": "#코요 랩"}


def translate_tag(tag):
    if tag in TAG_KO:
        return TAG_KO[tag]
    return re.sub(r"(ID)?(\d+)期生", lambda m: (("ID " if m[1] else "") + m[2] + "기생"), tag)


def corrected_effect(card, effect):
    """Corrections verified against the collected official Japanese ability text."""
    complete = {
        'hBP08-034': '콜라보 이펙트 FUWAMOCO를 믿어!\n자신이 후공이고 최초의 턴이라면, 자신의 덱에서, Debut 홀로멤인 [〈후와와 어비스가드〉와 〈모코코 어비스가드〉] 1장씩을 스테이지에 낸다. 그리고 덱을 셔플 한다.\n아츠 [무색] 당신의 모코모코한 모코코 30',
        'hBP09-029': '아츠 [녹] [녹] [무색] BIG3 친목회 side N 100\n자신의 덱에서, 2nd 〈시로가네 노엘〉 1장을 공개하고, 패에 더한다. 그리고 덱을 셔플 한다.\n엑스트라 이 홀로멤이 다운 했을 때, 자신의 라이프 -2.',
    }
    if card in complete:
        return complete[card]
    replacements = {
        'hBP08-048': [('FLOW GLOW의 훌륭한 선전 담당','기척 있는 183cm')],
        'hBP09-035': [('요리는 애정 130+','요리는 애정 180+')],
        'hBP09-070': [('비베이셔스 비전 100','비베이셔스 비전 120+')],
        'hBP09-083': [('#술 을 가진 서프트','#라미의 술 을 가진 서포트'),('460+','160±')],
        'hBP09-091': [('[〈AZKi〉나 〈카자마 이로하〉] 1장씩','1st [〈AZKi〉와 〈카자마 이로하〉] 1장씩')],
        'hBP09-080': [('자신의 서포트가 붙어 있는 홀로멤이 있다면, 자신의 덱을 1장 드로우 한다.','')],
        'hEB01-029': [('LIMITED : 턴에 1번밖에 사용할 수 없다.\n','')],
        'hBP02-059': [('자신의 덱에서, 카드 1장을 공개하고, 아카이브 한다.','자신의 덱에서, 카드 1장을 아카이브 한다.'),
                       ('8장 이상 있을 때, 다시, 이 아츠 +40.','8장 이상 있다면, 대신, 이 아츠 +80.')],
        'hBP09-110': [('유키히나 라미','유키하나 라미')],
        'hBP09-065': [('키키라리 비비','키키라라 비비')],
    }
    for before, after in replacements.get(card, []):
        effect = effect.replace(before, after)
    if card == 'hBP08-057':
        effect += '\n이 홀로멤에게 적 옐이 붙어 있다면, 이 아츠 +20.'
    if card == 'hBP09-053':
        effect += '\n아츠 [청] [무색] [무색] 토코야미 권속과 보내는 한때 80'
    return effect.strip()


def validate(conn, data):
    problems = []
    inventory = {card for cards in data['expected'].values() for card in cards}
    for card in sorted(inventory):
        row = conn.execute("""SELECT p.*,k.name AS ko_name,k.effect_text AS ko_effect,j.effect_text AS ja_effect
            FROM prints p LEFT JOIN card_texts_ko k ON k.print_id=p.print_id
            LEFT JOIN card_texts_ja j ON j.print_id=p.print_id WHERE p.card_number=?""", (card,)).fetchone()
        if row is None:
            problems.append([card, "missing card"])
            continue
        for col in ('rarity','card_type','product','name_ja','image_url','detail_url','ko_name'):
            if not (row[col] or '').strip():
                problems.append([card, "blank " + col])
        if 'サポート' not in row['card_type'] and '서포트' not in row['card_type'] and not row['color']:
            problems.append([card, "blank color"])
        if row['card_type'] != '옐':
            for col in ('ko_effect','ja_effect'):
                if not (row[col] or '').strip():
                    problems.append([card, "blank " + col])
        if '{{{' in row['ko_name'] or '{{{' in (row['ko_effect'] or ''):
            problems.append([card, "wiki markup"])
        if not conn.execute("SELECT 1 FROM card_illustrations WHERE card_number=? AND is_default=1", (card,)).fetchone():
            problems.append([card, "missing default illustration"])
    for item in data['official']:
        if not conn.execute("SELECT 1 FROM card_illustrations WHERE card_number=? AND rarity=? AND trim(coalesce(image_url,''))<>''", (item['card_number'], item['rarity'])).fetchone():
            problems.append([item['card_number'], "missing rarity " + item['rarity']])
    integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
    fk = conn.execute('PRAGMA foreign_key_check').fetchall()
    if integrity != 'ok' or fk:
        problems.append(["database", str((integrity, [tuple(r) for r in fk]))])
    if problems:
        raise RuntimeError(json.dumps(problems, ensure_ascii=False))
    return dict(integrity=integrity, foreign_key_errors=len(fk), missing_fields=0,
                packs={code:dict(cards=len(cards), missing_cards=0,
                                 official_variants=len([r for r in data['official'] if r['expansion']==code]))
                       for code,cards in data['expected'].items()})


def apply(data):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_dir = ROOT / 'data' / 'pack_verification_backups' / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    inventory = {card:info for cards in data['expected'].values() for card,info in cards.items()}
    grouped = {}
    for row in data['official']:
        grouped.setdefault(row['card_number'], []).append(row)
    # Every expected card must have an observed, official base rarity.
    primary = {}
    for card, variants in grouped.items():
        preferred = inventory[card]['rarity'].split()[0]
        primary[card] = min(variants, key=lambda r:(r['rarity'] != preferred,r['detail_id']))
    report = dict(timestamp=stamp, databases={}, source_notes=[
        'Official AJAX pagination exhausted and checked against reported totals.',
        'NamuWiki individual-table number typos resolved using card section IDs.',
        'hEB01-025 table says hEB01-090: mapped by unique support name.',
        'hBP09-111 source table name Bloom＆Gloom corrected to inventory/official Pemaloe.',
        'Cheer cards have no ability text; blank effects are intentional.',
        'Existing illustrations of the same card and rarity are preserved; schema stores one per pair.'
    ])
    staged = []
    for relative in ('data/hololive_ocg.sqlite','app/assets/hololive_ocg.sqlite'):
        original = ROOT / relative
        backup = backup_dir / (relative.replace('/', '_'))
        stage = backup_dir / (relative.replace('/', '_') + '.staged')
        with sqlite3.connect(f'file:{original.as_posix()}?mode=ro', uri=True) as source:
            with sqlite3.connect(backup) as dest:
                source.backup(dest)
            with sqlite3.connect(stage) as dest:
                source.backup(dest)
        source.close()
        dest.close()
        conn = sqlite3.connect(stage)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        columns = {r[1] for r in conn.execute('PRAGMA table_info(prints)')}
        if 'manage_id_jp' not in columns:
            conn.execute('ALTER TABLE prints ADD COLUMN manage_id_jp INTEGER')
        from import_illustrations import ensure_schema
        ensure_schema(conn)
        existing_ko = namu.load_existing_ko(conn)
        include_source = namu.has_column(conn, 'card_texts_ko', 'source')
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        stats = dict(added_cards=0, updated_cards=0, korean_texts_updated=0, added_illustrations=0,
                     backup=str(backup.relative_to(ROOT)), original_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
        try:
            with conn:
                for card, main in sorted(primary.items()):
                    old = conn.execute('SELECT * FROM prints WHERE card_number=?', (card,)).fetchone()
                    in_new_set = card.split('-')[0] in PACKS
                    products = list(dict.fromkeys([*(old['product'].split(' | ') if old and old['product'] else []),
                                                  *(PACKS[r['expansion']] for r in grouped[card])]))
                    detail = dict(main)
                    detail['color'] = '/'.join(COLOR_KO.get(c,c) for c in main['color'].split('/') if c)
                    detail['card_type'] = ' / '.join(TYPE_KO.get(t,t) for t in main['card_type'].split('・') if t != 'LIMITED')
                    detail['product'] = ' | '.join(products)
                    if old and not in_new_set:
                        for field in ('rarity','color','card_type','name_ja','image_url','detail_id','detail_url'):
                            if old[field]:
                                detail['name' if field == 'name_ja' else field] = old[field]
                    pid = official.upsert_print(conn, card, detail)
                    stats['updated_cards' if old else 'added_cards'] += 1
                    conn.execute('UPDATE prints SET manage_id_jp=? WHERE print_id=?',
                                 (old['manage_id_jp'] if old and old['manage_id_jp'] and not in_new_set else main['detail_id'],pid))
                    official.upsert_text_ja(conn,pid,main['name'],main['raw_text'])
                    conn.execute('DELETE FROM print_tags WHERE print_id=?',(pid,))
                    for tag in main['tags']:
                        ko_tag = translate_tag(tag)
                        tag_row = conn.execute('SELECT tag_id FROM tags WHERE tag=?',(tag,)).fetchone()
                        if tag_row is None:
                            tag_id = conn.execute('INSERT INTO tags(tag,normalized) VALUES(?,?)',(tag,official.normalize_tag(tag))).lastrowid
                        else:
                            tag_id = tag_row[0]
                        conn.execute('INSERT INTO print_tags(print_id,tag_id) VALUES(?,?)',(pid,tag_id))
                        for table, value in (('tags_ja',tag),('tags_ko',ko_tag)):
                            if table in tables and not conn.execute(f'SELECT 1 FROM {table} WHERE tag_id=?',(tag_id,)).fetchone():
                                # Preserve existing table IDs and unique translated labels.
                                if not conn.execute(f'SELECT 1 FROM {table} WHERE tag=?',(value,)).fetchone():
                                    conn.execute(f'INSERT INTO {table}(tag_id,tag,normalized) VALUES(?,?,?)',(tag_id,value,official.normalize_tag(value)))
                    trans = data['translations'].get(card.upper())
                    ko_name = inventory[card]['name']
                    if main['card_type'] == 'エール':
                        trans = dict(name=ko_name,effect='',source_url='https://namu.wiki/w/'+quote('홀로라이브 오피셜 카드 게임/옐'))
                        # An effectless Cheer card should not get a copied member ability.
                        conn.execute('''INSERT INTO card_texts_ko(print_id,name,effect_text,memo,version,updated_at)
                            VALUES(?,?,?,?,1,?) ON CONFLICT(print_id) DO UPDATE SET name=excluded.name,
                            effect_text=excluded.effect_text,memo=excluded.memo,updated_at=excluded.updated_at''',
                            (pid,ko_name,'',trans['source_url'],stamp))
                    else:
                        if trans is None:
                            raise RuntimeError('Missing Korean source for '+card)
                        effect = corrected_effect(card,trans['effect'])
                        source_url = trans['source_url']
                        if effect != trans['effect'].strip():
                            source_url += '\nOfficial verification: ' + main['detail_url']
                        if namu.upsert_ko_text(conn,pid,ko_name,effect,source_url,
                                             include_source=include_source,overwrite=True,existing=existing_ko):
                            stats['korean_texts_updated'] += 1
                    for variant in grouped[card]:
                        ci = conn.execute('SELECT * FROM card_illustrations WHERE card_number=? AND rarity=?',(card,variant['rarity'])).fetchone()
                        if ci is None:
                            conn.execute('''INSERT INTO card_illustrations(card_number,rarity,manage_id_jp,image_url,is_default)
                                VALUES(?,?,?,?,0)''',(card,variant['rarity'],variant['detail_id'],variant['image_url']))
                            stats['added_illustrations'] += 1
                        elif in_new_set or not ci['image_url']:
                            conn.execute('UPDATE card_illustrations SET manage_id_jp=?,image_url=? WHERE illustration_id=?',
                                         (variant['detail_id'],variant['image_url'],ci['illustration_id']))
                    # Match the default artwork with the canonical print.
                    default_rarity = detail['rarity']
                    conn.execute('UPDATE card_illustrations SET is_default=0 WHERE card_number=?',(card,))
                    conn.execute('UPDATE card_illustrations SET is_default=1 WHERE card_number=? AND rarity=?',(card,default_rarity))
                    if not conn.execute('SELECT 1 FROM card_illustrations WHERE card_number=? AND is_default=1',(card,)).fetchone():
                        conn.execute('UPDATE card_illustrations SET is_default=1 WHERE illustration_id=(SELECT illustration_id FROM card_illustrations WHERE card_number=? ORDER BY manage_id_jp LIMIT 1)',(card,))
                for code in PACKS:
                    conn.execute('INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                                 (code.lower()+'_verified_imported_at',stamp))
                stats['verification'] = validate(conn,data)
            conn.close()
        except Exception:
            conn.close()
            raise
        stats['new_sha256'] = hashlib.sha256(stage.read_bytes()).hexdigest()
        report['databases'][relative] = stats
        staged.append((original,stage,stats['original_sha256']))
    # Check both originals still match the snapshots before replacing either one.
    for original,stage,digest in staged:
        # SQLite read-only connections can leave an empty WAL in WAL mode.
        # Ask SQLite to checkpoint and close it; never unlink sidecars by hand.
        wal = Path(str(original)+'-wal')
        if wal.exists():
            cleanup = sqlite3.connect(original, timeout=5)
            status = cleanup.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            cleanup.close()
            if status[0] != 0:
                raise RuntimeError('Database WAL is busy: '+str(original))
        if hashlib.sha256(original.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Database changed during import: '+str(original))
        if Path(str(original)+'-wal').exists() or Path(str(original)+'-journal').exists():
            raise RuntimeError('Database may be open for writing: '+str(original))
    for original,stage,_ in staged:
        os.replace(stage,original)
    out = ROOT/'tools'/'reports'/'requested_packs_verification.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


def fetch(url):
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".html")
    if path.exists():
        return path.read_bytes()
    response = requests.get(url, timeout=(10, 40), headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return response.content


def probe():
    for code, title in PACKS.items():
        for suffix in ("", "/카드"):
            url = "https://namu.wiki/w/" + quote(title + suffix)
            try:
                html = fetch(url).decode("utf-8")
                soup = BeautifulSoup(html, "html.parser")
                rows = namu.parse_tables(html, url)
                links = namu.collect_linked_pages(html, include_re=None, exclude_re=None)
                print("NAMU", code, suffix, "rows", len(rows), "links", len(links), "title", soup.title.get_text() if soup.title else "", flush=True)
                print("SAMPLE", rows[:2], flush=True)
            except Exception as exc:
                print("ERROR", url, repr(exc), flush=True)
        url = official.build_list_url(code, 1, "page")
        html = fetch(url)
        items = official.parse_list_page(html)
        print("OFFICIAL", code, "total", official.detect_total_count(html), "pages", official.detect_max_page(html, "page"), "items", len(items), items[:2], flush=True)
        if items:
            detail_url = "https://hololive-official-cardgame.com/cardlist/?id=" + items[0].card_id
            detail_html = fetch(detail_url)
            print("DETAIL", official.parse_detail(detail_html, items[0].card_number, False), flush=True)
            soup = BeautifulSoup(detail_html, "html.parser")
            root = soup.select_one(".cardlist-Detail")
            print("STRUCTURE", str(root)[:1000], flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.apply:
        apply(json.loads((CACHE/'collected.json').read_text(encoding='utf-8')))
    elif args.collect:
        collect()
    else:
        probe()

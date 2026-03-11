-- Fix Korean card text issues in database
-- This script addresses 3 problems:
-- 1. Remove "배턴 터치" metadata from effect_text (41 cards)
-- 2. Remove brackets from 콜라보 이펙트 (173 cards)
-- 3. Remove brackets from 블룸 이펙트 (173 cards)

-- Begin transaction for atomic updates
BEGIN TRANSACTION;

-- 1. Remove 배턴 터치 metadata lines
-- Pattern: "레벨 ...\nHP ...\n배턴 터치 ...\n" should be stripped
UPDATE card_texts_ko
SET effect_text = TRIM(
  REGEXP_REPLACE(
    effect_text,
    '레벨[^\n]*\nHP[^\n]*\n배턴 터치[^\n]*\n',
    '',
    'g'
  )
),
version = version + 1,
updated_at = datetime('now')
WHERE effect_text LIKE '%배턴 터치%';

-- 2. Remove brackets from 콜라보 이펙트
-- Change: 【콜라보 이펙트】 → 콜라보 이펙트
UPDATE card_texts_ko
SET effect_text = REPLACE(effect_text, '【콜라보 이펙트】', '콜라보 이펙트'),
version = version + 1,
updated_at = datetime('now')
WHERE effect_text LIKE '%【콜라보 이펙트】%';

-- 3. Remove brackets from 블룸 이펙트
-- Change: 【블룸 이펙트】 → 블룸 이펙트
UPDATE card_texts_ko
SET effect_text = REPLACE(effect_text, '【블룸 이펙트】', '블룸 이펙트'),
version = version + 1,
updated_at = datetime('now')
WHERE effect_text LIKE '%【블룸 이펙트】%';

-- Commit all changes
COMMIT;

-- Verification queries
-- Run these after the script to verify the fixes

-- Check for remaining 배턴 터치 entries (should be 0)
SELECT '=== Remaining 배턴 터치 entries ===' AS check_name;
SELECT COUNT(*) AS count FROM card_texts_ko WHERE effect_text LIKE '%배턴 터치%';

-- Check for remaining bracketed collab/bloom effects (should be 0)
SELECT '=== Remaining bracketed 콜라보/블룸 이펙트 ===' AS check_name;
SELECT COUNT(*) AS count FROM card_texts_ko 
WHERE effect_text LIKE '%【콜라보 이펙트】%' 
   OR effect_text LIKE '%【블룸 이펙트】%';

-- Sample verification: show a few updated cards
SELECT '=== Sample updated cards ===' AS check_name;
SELECT card_id, SUBSTR(effect_text, 1, 100) AS effect_preview
FROM card_texts_ko
WHERE card_id IN ('hBP04-054', 'hBP04-055', 'hBP04-056')
   OR effect_text LIKE '%콜라보 이펙트%'
   OR effect_text LIKE '%블룸 이펙트%'
LIMIT 10;

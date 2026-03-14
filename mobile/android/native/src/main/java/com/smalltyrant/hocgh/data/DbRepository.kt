package com.smalltyrant.hocgh.data

import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import com.smalltyrant.hocgh.model.CardDetail
import com.smalltyrant.hocgh.model.CardSnapshot
import com.smalltyrant.hocgh.model.PrintBrief
import com.smalltyrant.hocgh.model.PrintRow
import java.time.Instant
import java.time.ZoneOffset

private val TAG_ALIAS: Map<String, List<String>> = mapOf(
    "동물귀" to listOf("인권없음"),
    "인권없음" to listOf("동물귀"),
)

class DbRepository(private val paths: AppPaths) {

    data class ImageTarget(
        val cardNumber: String,
        val imageUrl: String,
    )

    private data class DbFingerprint(
        val path: String,
        val size: Long,
        val modifiedAtMillis: Long,
    )

    private data class DbHealthCache(
        val fingerprint: DbFingerprint,
        val needsUpdate: Boolean,
    )

    private data class SchemaCache(
        val fingerprint: DbFingerprint,
        val tableColumns: MutableMap<String, Set<String>> = mutableMapOf(),
        var tagJoinResolved: Boolean = false,
        var tagJoinSql: String? = null,
    )

    private data class SnapshotCache(
        val fingerprint: DbFingerprint,
        val snapshots: LinkedHashMap<Long, CardSnapshot>,
    )

    @Volatile
    private var dbHealthCache: DbHealthCache? = null

    @Volatile
    private var schemaCache: SchemaCache? = null

    @Volatile
    private var snapshotCache: SnapshotCache? = null

    fun needsDbUpdate(): Boolean {
        val fingerprint = dbFingerprint()
        if (fingerprint == null) {
            clearCaches()
            return true
        }

        cachedNeedsDbUpdate(fingerprint)?.let { return it }

        val needsUpdate = try {
            openReadOnly().useDb { db ->
                if (!tableExists(db, "prints")) {
                    true
                } else {
                    val cols = tableColumns(db, "prints", fingerprint)
                    val required = setOf("print_id", "card_number", "name_ja", "image_url")
                    if (!cols.containsAll(required)) {
                        return@useDb true
                    }
                    val hasRows = db.rawQuery("SELECT 1 FROM prints LIMIT 1", null).useCursor { cursor ->
                        cursor.moveToFirst()
                    }
                    !hasRows
                }
            }
        } catch (_: Throwable) {
            true
        }

        storeNeedsDbUpdate(fingerprint, needsUpdate)
        return needsUpdate
    }

    fun querySuggest(query: String, limit: Int? = null): List<PrintRow> {
        val q = query.trim()
        if (q.isEmpty()) {
            return emptyList()
        }

        val like = "%$q%"
        val terms = buildSearchTerms(q)
        val normalizedTerms = terms.map(::normalizeTerm).filter { it.isNotEmpty() }.distinct()

        return try {
            openReadOnly().useDb { db ->
                val sessionFingerprint = dbFingerprint()
                val joins = buildTagJoinSql(db, sessionFingerprint)
                if (joins != null) {
                    val params = mutableListOf(like, like, like, like, like, like)
                    val sql = buildString {
                        append(
                            """
                            SELECT DISTINCT
                                p.print_id,
                                p.card_number,
                                COALESCE(p.name_ja,'') AS name_ja,
                                COALESCE(ko.name,'') AS name_ko
                            FROM prints p
                            LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                            $joins
                            WHERE
                                UPPER(p.card_number) LIKE UPPER(?)
                                OR COALESCE(p.name_ja,'') LIKE ?
                                OR COALESCE(ko.name,'') LIKE ?
                                OR COALESCE(ko.effect_text,'') LIKE ?
                                OR (t.tag IS NOT NULL AND (t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?))
                            """.trimIndent()
                        )
                        for (term in terms) {
                            append(" OR t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?")
                            params += "%$term%"
                            params += "%$term%"
                        }

                        if (normalizedTerms.isNotEmpty()) {
                            val normCardNumber = sqlNormalizeExpr("p.card_number")
                            val normTag = sqlNormalizeExpr("t.tag")
                            val normNormalized = sqlNormalizeExpr("t.normalized")
                            val normNameJa = sqlNormalizeExpr("p.name_ja")
                            val normNameKo = sqlNormalizeExpr("ko.name")
                            val normEffectText = sqlNormalizeExpr("ko.effect_text")
                            for (term in normalizedTerms) {
                                append(
                                    " OR $normCardNumber LIKE ? OR $normTag LIKE ? OR $normNormalized LIKE ?" +
                                        " OR $normNameJa LIKE ? OR $normNameKo LIKE ? OR $normEffectText LIKE ?",
                                )
                                params += "%$term%"
                                params += "%$term%"
                                params += "%$term%"
                                params += "%$term%"
                                params += "%$term%"
                                params += "%$term%"
                            }
                        }

                        append(" ORDER BY p.card_number")
                        if (limit != null && limit > 0) {
                            append(" LIMIT ?")
                            params += limit.toString()
                        }
                    }
                    return@useDb queryRows(db, sql, params)
                }

                val params = mutableListOf(like, like, like, like)
                val sql = buildString {
                    append(
                        """
                        SELECT
                            p.print_id,
                            p.card_number,
                            COALESCE(p.name_ja,'') AS name_ja,
                            COALESCE(ko.name,'') AS name_ko
                        FROM prints p
                        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                        WHERE UPPER(p.card_number) LIKE UPPER(?)
                           OR COALESCE(p.name_ja,'') LIKE ?
                           OR COALESCE(ko.name,'') LIKE ?
                           OR COALESCE(ko.effect_text,'') LIKE ?
                        """.trimIndent()
                    )
                    if (normalizedTerms.isNotEmpty()) {
                        val normCardNumber = sqlNormalizeExpr("p.card_number")
                        val normNameJa = sqlNormalizeExpr("p.name_ja")
                        val normNameKo = sqlNormalizeExpr("ko.name")
                        val normEffectText = sqlNormalizeExpr("ko.effect_text")
                        for (term in normalizedTerms) {
                            append(" OR $normCardNumber LIKE ? OR $normNameJa LIKE ? OR $normNameKo LIKE ? OR $normEffectText LIKE ?")
                            params += "%$term%"
                            params += "%$term%"
                            params += "%$term%"
                            params += "%$term%"
                        }
                    }
                    append(" ORDER BY p.card_number")
                    if (limit != null && limit > 0) {
                        append(" LIMIT ?")
                        params += limit.toString()
                    }
                }
                queryRows(db, sql, params)
            }
        } catch (_: Throwable) {
            emptyList()
        }
    }

    fun queryExact(query: String, limit: Int? = null): List<PrintRow> {
        val q = query.trim()
        if (q.isEmpty()) {
            return emptyList()
        }

        val normalizedQ = normalizeTerm(q)

        return try {
            openReadOnly().useDb { db ->
                val sessionFingerprint = dbFingerprint()
                val joins = buildTagJoinSql(db, sessionFingerprint)
                if (joins != null) {
                    val params = mutableListOf(q, q, q, q, q)
                    val sql = buildString {
                        append(
                            """
                            SELECT DISTINCT
                                p.print_id,
                                p.card_number,
                                COALESCE(p.name_ja,'') AS name_ja,
                                COALESCE(ko.name,'') AS name_ko
                            FROM prints p
                            LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                            $joins
                            WHERE
                                UPPER(COALESCE(p.card_number,'')) = UPPER(?)
                                OR LOWER(COALESCE(p.name_ja,'')) = LOWER(?)
                                OR LOWER(COALESCE(ko.name,'')) = LOWER(?)
                                OR (
                                    t.tag IS NOT NULL
                                    AND (
                                        LOWER(COALESCE(t.tag,'')) = LOWER(?)
                                        OR LOWER(COALESCE(t.normalized,'')) = LOWER(?)
                            """.trimIndent()
                        )
                        if (normalizedQ.isNotEmpty()) {
                            val normTag = sqlNormalizeExpr("t.tag")
                            val normNormalized = sqlNormalizeExpr("t.normalized")
                            append(" OR $normTag = ? OR $normNormalized = ?")
                            params += normalizedQ
                            params += normalizedQ
                        }
                        append(
                            """
                                    )
                                )
                            """.trimIndent()
                        )
                        if (normalizedQ.isNotEmpty()) {
                            val normCardNumber = sqlNormalizeExpr("p.card_number")
                            val normNameJa = sqlNormalizeExpr("p.name_ja")
                            val normNameKo = sqlNormalizeExpr("ko.name")
                            append(" OR $normCardNumber = ? OR $normNameJa = ? OR $normNameKo = ?")
                            params += normalizedQ
                            params += normalizedQ
                            params += normalizedQ
                        }
                        append(" ORDER BY p.card_number")
                        if (limit != null && limit > 0) {
                            append(" LIMIT ?")
                            params += limit.toString()
                        }
                    }
                    return@useDb queryRows(db, sql, params)
                }

                val params = mutableListOf(q, q, q)
                val sql = buildString {
                    append(
                        """
                        SELECT
                            p.print_id,
                            p.card_number,
                            COALESCE(p.name_ja,'') AS name_ja,
                            COALESCE(ko.name,'') AS name_ko
                        FROM prints p
                        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                        WHERE
                            UPPER(COALESCE(p.card_number,'')) = UPPER(?)
                            OR LOWER(COALESCE(p.name_ja,'')) = LOWER(?)
                            OR LOWER(COALESCE(ko.name,'')) = LOWER(?)
                        """.trimIndent()
                    )
                    if (normalizedQ.isNotEmpty()) {
                        val normCardNumber = sqlNormalizeExpr("p.card_number")
                        val normNameJa = sqlNormalizeExpr("p.name_ja")
                        val normNameKo = sqlNormalizeExpr("ko.name")
                        append(" OR $normCardNumber = ? OR $normNameJa = ? OR $normNameKo = ?")
                        params += normalizedQ
                        params += normalizedQ
                        params += normalizedQ
                    }
                    append(" ORDER BY p.card_number")
                    if (limit != null && limit > 0) {
                        append(" LIMIT ?")
                        params += limit.toString()
                    }
                }
                queryRows(db, sql, params)
            }
        } catch (_: Throwable) {
            emptyList()
        }
    }

    fun getPrintBrief(printId: Long): PrintBrief? {
        return try {
            openReadOnly().useDb { db ->
                db.rawQuery(
                    """
                    SELECT
                        p.print_id,
                        p.card_number,
                        COALESCE(p.name_ja,'') AS name_ja,
                        COALESCE(ko.name,'') AS name_ko,
                        COALESCE(p.image_url,'') AS image_url
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    WHERE p.print_id=?
                    """.trimIndent(),
                    arrayOf(printId.toString()),
                ).useCursor { cursor ->
                    if (!cursor.moveToFirst()) {
                        return@useCursor null
                    }
                    PrintBrief(
                        printId = cursor.getLongOrZero("print_id"),
                        cardNumber = cursor.getStringOrEmpty("card_number"),
                        nameJa = cursor.getStringOrEmpty("name_ja"),
                        nameKo = cursor.getStringOrEmpty("name_ko"),
                        imageUrl = cursor.getStringOrEmpty("image_url"),
                    )
                }
            }
        } catch (_: Throwable) {
            null
        }
    }

    fun listDeckCards(query: String, limit: Int = 240): List<com.smalltyrant.hocgh.model.DeckCardCandidate> {
        val like = "%${query.trim()}%"
        return try {
            openReadOnly().useDb { db ->
                db.rawQuery(
                    """
                    SELECT
                        p.print_id,
                        p.card_number,
                        COALESCE(p.name_ja,'') AS name_ja,
                        COALESCE(ko.name,'') AS name_ko,
                        COALESCE(p.image_url,'') AS image_url,
                        COALESCE(
                            NULLIF(TRIM(COALESCE(p.card_type,'')), ''),
                            CASE
                                WHEN instr(COALESCE(ja.effect_text,''), 'カードタイプ ') > 0 THEN
                                    TRIM(
                                        substr(
                                            substr(
                                                COALESCE(ja.effect_text,''),
                                                instr(COALESCE(ja.effect_text,''), 'カードタイプ ') + length('カードタイプ ')
                                            ),
                                            1,
                                            instr(
                                                substr(
                                                    COALESCE(ja.effect_text,''),
                                                    instr(COALESCE(ja.effect_text,''), 'カードタイプ ') + length('カードタイプ ')
                                                ) || char(10),
                                                char(10)
                                            ) - 1
                                        )
                                    )
                                ELSE ''
                            END,
                            ''
                        ) AS card_type,
                        COALESCE(
                            NULLIF(TRIM(COALESCE(p.color,'')), ''),
                            CASE
                                WHEN instr(COALESCE(ja.effect_text,''), '色 ') > 0 THEN
                                    TRIM(
                                        substr(
                                            substr(
                                                COALESCE(ja.effect_text,''),
                                                instr(COALESCE(ja.effect_text,''), '色 ') + length('色 ')
                                            ),
                                            1,
                                            instr(
                                                substr(
                                                    COALESCE(ja.effect_text,''),
                                                    instr(COALESCE(ja.effect_text,''), '色 ') + length('色 ')
                                                ) || char(10),
                                                char(10)
                                            ) - 1
                                        )
                                    )
                                ELSE ''
                            END,
                            ''
                        ) AS color,
                        CASE
                            WHEN instr(COALESCE(ja.effect_text,''), 'レアリティ ') > 0 THEN
                                TRIM(
                                    substr(
                                        substr(
                                            COALESCE(ja.effect_text,''),
                                            instr(COALESCE(ja.effect_text,''), 'レアリティ ') + length('レアリティ ')
                                        ),
                                        1,
                                        instr(
                                            substr(
                                                COALESCE(ja.effect_text,''),
                                                instr(COALESCE(ja.effect_text,''), 'レアリティ ') + length('レアリティ ')
                                            ) || char(10),
                                            char(10)
                                        ) - 1
                                    )
                                )
                            ELSE ''
                        END AS rarity,
                        COALESCE(ko.effect_text,'') AS ko_text
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
                    WHERE
                        ? = '%%'
                        OR UPPER(COALESCE(p.card_number,'')) LIKE UPPER(?)
                        OR LOWER(COALESCE(ko.name,'')) LIKE LOWER(?)
                        OR LOWER(COALESCE(p.name_ja,'')) LIKE LOWER(?)
                    ORDER BY p.card_number
                    LIMIT ?
                    """.trimIndent(),
                    arrayOf(like, like, like, like, limit.toString()),
                ).useCursor { cursor ->
                    val out = mutableListOf<com.smalltyrant.hocgh.model.DeckCardCandidate>()
                    while (cursor.moveToNext()) {
                        out += com.smalltyrant.hocgh.model.DeckCardCandidate(
                            printId = cursor.getLongOrZero("print_id"),
                            cardNumber = cursor.getStringOrEmpty("card_number"),
                            nameJa = cursor.getStringOrEmpty("name_ja"),
                            nameKo = cursor.getStringOrEmpty("name_ko"),
                            imageUrl = cursor.getStringOrEmpty("image_url"),
                            cardType = cursor.getStringOrEmpty("card_type"),
                            color = cursor.getStringOrEmpty("color"),
                            rarity = cursor.getStringOrEmpty("rarity"),
                            koText = cursor.getStringOrEmpty("ko_text"),
                        )
                    }
                    out
                }
            }
        } catch (_: Throwable) {
            emptyList()
        }
    }

    fun loadCardDetail(printId: Long): CardDetail? {
        return loadCardSnapshot(printId)?.detail
    }

    fun loadCardSnapshot(printId: Long): CardSnapshot? {
        val fingerprint = dbFingerprint() ?: return null
        cachedSnapshot(printId = printId, fingerprint = fingerprint)?.let {
            return it
        }

        return try {
            openReadOnly().useDb { db ->
                val sessionFingerprint = fingerprint
                val jaColumns = tableColumns(db, "card_texts_ja", sessionFingerprint)
                val hasJaEffectText = jaColumns.contains("effect_text")
                val sql = if (hasJaEffectText) {
                    """
                    SELECT
                        p.print_id,
                        COALESCE(p.card_number,'') AS card_number,
                        COALESCE(p.name_ja,'') AS name_ja,
                        COALESCE(ko.name,'') AS name_ko,
                        COALESCE(p.image_url,'') AS image_url,
                        COALESCE(ko.effect_text,'') AS ko_text,
                        COALESCE(ja.effect_text,'') AS ja_text,
                        COALESCE(ko.name,'') AS ko_name
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
                    WHERE p.print_id=?
                    """.trimIndent()
                } else {
                    """
                    SELECT
                        p.print_id,
                        COALESCE(p.card_number,'') AS card_number,
                        COALESCE(p.name_ja,'') AS name_ja,
                        COALESCE(ko.name,'') AS name_ko,
                        COALESCE(p.image_url,'') AS image_url,
                        COALESCE(ko.effect_text,'') AS ko_text,
                        '' AS ja_text,
                        COALESCE(ko.name,'') AS ko_name
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    WHERE p.print_id=?
                    """.trimIndent()
                }
                db.rawQuery(
                    sql,
                    arrayOf(printId.toString()),
                ).useCursor { cursor ->
                    if (!cursor.moveToFirst()) {
                        return@useCursor null
                    }

                    val brief = PrintBrief(
                        printId = cursor.getLongOrZero("print_id"),
                        cardNumber = cursor.getStringOrEmpty("card_number"),
                        nameJa = cursor.getStringOrEmpty("name_ja"),
                        nameKo = cursor.getStringOrEmpty("name_ko"),
                        imageUrl = cursor.getStringOrEmpty("image_url"),
                    )

                    var koTextRaw = cursor.getStringOrEmpty("ko_text")
                    val jaTextRaw = cursor.getStringOrEmpty("ja_text")
                    val koName = cleanDisplayName(cursor.getStringOrEmpty("ko_name"))

                    // Strip duplicate card name from start of effect_text
                    if (koName.isNotEmpty()) {
                        val trimmed = koTextRaw.trim()
                        if (trimmed.startsWith(koName)) {
                            koTextRaw = trimmed.removePrefix(koName).trim()
                        }
                    }

                    val tags = loadTagsForPrint(db, printId, sessionFingerprint)

                    val detail = CardDetail(
                        koText = appendTagsIfNeeded(koTextRaw, tags, "태그"),
                        jaText = appendTagsIfNeeded(jaTextRaw, tags, "タグ"),
                    )

                    val snapshot = CardSnapshot(brief = brief, detail = detail)
                    storeSnapshot(printId = printId, snapshot = snapshot, fingerprint = fingerprint)
                    snapshot
                }
            }
        } catch (_: Throwable) {
            null
        }
    }

     private fun loadTagsForPrint(
        db: SQLiteDatabase,
        printId: Long,
        fingerprint: DbFingerprint? = null,
    ): List<String> {
        val tagJoinSql = buildTagJoinSql(db, fingerprint) ?: return emptyList()
        // tags_ko 테이블이 있으면 한국어 태그를 우선 사용, 없으면 원본 태그 사용
        val hasTagsKo = tableExists(db, "tags_ko")
        val tagSelect = if (hasTagsKo) {
            "COALESCE(ko.tag, t.tag, '') AS tag"
        } else {
            "COALESCE(t.tag,'') AS tag"
        }
        val koJoin = if (hasTagsKo) {
            "LEFT JOIN tags_ko ko ON ko.tag_id = t.tag_id"
        } else {
            ""
        }
        return db.rawQuery(
            """
            SELECT $tagSelect
            FROM prints p
            $tagJoinSql
            $koJoin
            WHERE p.print_id=?
            ORDER BY t.tag
            """.trimIndent(),
            arrayOf(printId.toString()),
        ).useCursor { cursor ->
            val out = LinkedHashSet<String>()
            while (cursor.moveToNext()) {
                var tag = cursor.getStringOrEmpty("tag").trim()
                if (tag.isEmpty()) continue
                if (!tag.startsWith("#")) {
                    tag = "#$tag"
                }
                out += tag
            }
            out.toList()
        }
    }

    private fun appendTagsIfNeeded(text: String, tags: List<String>, sectionLabel: String): String {
        if (tags.isEmpty()) {
            return text
        }

        val existingTags = text
            .split(Regex("\\s+"))
            .map { it.trim() }
            .filter { it.startsWith("#") }
            .toSet()

        if (existingTags.isNotEmpty()) {
            return text
        }

        val missing = tags.filterNot(existingTags::contains)
        if (missing.isEmpty()) {
            return text
        }

        val normalized = text.trim()
        val tagLine = missing.joinToString(" ")
        return if (normalized.isEmpty()) {
            "$sectionLabel\n$tagLine"
        } else {
            "$normalized\n$sectionLabel\n$tagLine"
        }
    }

    fun loadMultiWordTags(): List<String> {
        return try {
            openReadOnly().useDb { db ->
                val allTags = mutableListOf<String>()
                val seen = mutableSetOf<String>()
                for (table in listOf("tags", "tags_ja", "tags_ko")) {
                    if (!tableExists(db, table)) continue
                    db.rawQuery(
                        "SELECT tag FROM $table WHERE tag LIKE '% %' ORDER BY LENGTH(tag) DESC",
                        null,
                    ).useCursor { cursor ->
                        while (cursor.moveToNext()) {
                            var tag = cursor.getStringOrEmpty("tag").trim()
                            if (tag.isNotEmpty()) {
                                if (!tag.startsWith("#")) tag = "#$tag"
                                if (seen.add(tag)) {
                                    allTags += tag
                                }
                            }
                        }
                    }
                }
                allTags.sortedByDescending { it.length }
            }
        } catch (_: Throwable) {
            emptyList()
        }
    }

    fun listImageTargets(): List<ImageTarget> {
        return try {
            openReadOnly().useDb { db ->
                db.rawQuery(
                    """
                    SELECT
                        COALESCE(p.card_number,'') AS card_number,
                        COALESCE(p.image_url,'') AS image_url
                    FROM prints p
                    WHERE COALESCE(p.card_number,'') <> ''
                    ORDER BY p.card_number
                    """.trimIndent(),
                    null,
                ).useCursor { cursor ->
                    val byCard = LinkedHashMap<String, String>()
                    while (cursor.moveToNext()) {
                        val cardNumber = cursor.getStringOrEmpty("card_number").trim()
                        if (cardNumber.isEmpty()) {
                            continue
                        }
                        val imageUrl = cursor.getStringOrEmpty("image_url").trim()
                        val existing = byCard[cardNumber]
                        if (existing == null || (existing.isEmpty() && imageUrl.isNotEmpty())) {
                            byCard[cardNumber] = imageUrl
                        }
                    }
                    byCard.entries.map { (cardNumber, imageUrl) ->
                        ImageTarget(cardNumber = cardNumber, imageUrl = imageUrl)
                    }
                }
            }
        } catch (_: Throwable) {
            emptyList()
        }
    }

    fun localDbDate(): String? {
        val dbFile = paths.dbFile
        if (!dbFile.exists() || !dbFile.isFile || dbFile.length() <= 0L) {
            return null
        }

        try {
            val inDbDate = openReadOnly().useDb { db ->
                if (tableExists(db, "meta")) {
                    val keys = listOf(
                        "release_asset_updated_at",
                        "release_published_at",
                        "release_created_at",
                    )
                    for (key in keys) {
                        val value = db.rawQuery(
                            "SELECT value FROM meta WHERE key=?",
                            arrayOf(key),
                        ).useCursor { cursor ->
                            if (cursor.moveToFirst()) cursor.getStringOrNull(0) else null
                        }
                        val normalized = formatIsoDateOrNull(value)
                        if (!normalized.isNullOrEmpty()) {
                            return@useDb normalized
                        }
                    }
                }

                val tables = listOf("prints", "card_texts_ko", "card_texts_ja")
                for (table in tables) {
                    if (!tableExists(db, table)) {
                        continue
                    }
                    val rawUpdatedAt = db.rawQuery(
                        "SELECT MAX(updated_at) FROM $table WHERE updated_at IS NOT NULL AND updated_at <> ''",
                        null,
                    ).useCursor { cursor ->
                        if (cursor.moveToFirst()) cursor.getStringOrNull(0) else null
                    }
                    val normalized = formatIsoDateOrNull(rawUpdatedAt)
                    if (!normalized.isNullOrEmpty()) {
                        return@useDb normalized
                    }
                }
                null
            }

            if (!inDbDate.isNullOrEmpty()) {
                return inDbDate
            }
        } catch (_: Throwable) {
            // Use file timestamp fallback.
        }

        return runCatching {
            Instant.ofEpochMilli(dbFile.lastModified())
                .atOffset(ZoneOffset.UTC)
                .toLocalDate()
                .toString()
        }.getOrNull()
    }

    private fun dbFingerprint(): DbFingerprint? {
        val dbFile = paths.dbFile
        if (!dbFile.exists() || !dbFile.isFile) {
            return null
        }
        val size = dbFile.length()
        if (size <= 0L) {
            return null
        }
        return DbFingerprint(
            path = dbFile.absolutePath,
            size = size,
            modifiedAtMillis = dbFile.lastModified(),
        )
    }

    @Synchronized
    private fun clearCaches() {
        dbHealthCache = null
        schemaCache = null
        snapshotCache = null
    }

    @Synchronized
    private fun cachedNeedsDbUpdate(fingerprint: DbFingerprint): Boolean? {
        val cache = dbHealthCache
        if (cache != null && cache.fingerprint == fingerprint) {
            return cache.needsUpdate
        }
        return null
    }

    @Synchronized
    private fun storeNeedsDbUpdate(fingerprint: DbFingerprint, needsUpdate: Boolean) {
        dbHealthCache = DbHealthCache(fingerprint = fingerprint, needsUpdate = needsUpdate)
    }

    @Synchronized
    private fun cachedSnapshot(printId: Long, fingerprint: DbFingerprint): CardSnapshot? {
        val cache = snapshotCache
        if (cache == null || cache.fingerprint != fingerprint) {
            return null
        }
        return cache.snapshots[printId]
    }

    @Synchronized
    private fun storeSnapshot(printId: Long, snapshot: CardSnapshot, fingerprint: DbFingerprint) {
        val cache = snapshotCache
        val target = if (cache != null && cache.fingerprint == fingerprint) {
            cache.snapshots
        } else {
            LinkedHashMap<Long, CardSnapshot>(SNAPSHOT_CACHE_LIMIT, 0.75f, true)
        }

        target[printId] = snapshot
        while (target.size > SNAPSHOT_CACHE_LIMIT) {
            val oldestKey = target.entries.firstOrNull()?.key ?: break
            target.remove(oldestKey)
        }

        snapshotCache = SnapshotCache(fingerprint = fingerprint, snapshots = target)
    }

    @Synchronized
    private fun schemaCacheFor(fingerprint: DbFingerprint): SchemaCache {
        val cache = schemaCache
        if (cache != null && cache.fingerprint == fingerprint) {
            return cache
        }
        val fresh = SchemaCache(fingerprint = fingerprint)
        schemaCache = fresh
        if (dbHealthCache?.fingerprint != fingerprint) {
            dbHealthCache = null
        }
        return fresh
    }

    private fun queryRows(
        db: SQLiteDatabase,
        sql: String,
        args: List<String>,
    ): List<PrintRow> {
        return db.rawQuery(sql, args.toTypedArray()).useCursor { cursor ->
            val out = mutableListOf<PrintRow>()
            while (cursor.moveToNext()) {
                out += PrintRow(
                    printId = cursor.getLongOrZero("print_id"),
                    cardNumber = cursor.getStringOrEmpty("card_number"),
                    nameJa = cursor.getStringOrEmpty("name_ja"),
                    nameKo = cursor.getStringOrEmpty("name_ko"),
                )
            }
            out
        }
    }

    private fun buildTagJoinSql(
        db: SQLiteDatabase,
        fingerprint: DbFingerprint? = null,
    ): String? {
        val cacheFingerprint = fingerprint ?: dbFingerprint()
        if (cacheFingerprint != null) {
            val cached = synchronized(this) {
                val cache = schemaCacheFor(cacheFingerprint)
                cache.tagJoinResolved to cache.tagJoinSql
            }
            if (cached.first) {
                return cached.second
            }
        }

        val ptCols = tableColumns(db, "print_tags", cacheFingerprint)
        val tagCols = tableColumns(db, "tags", cacheFingerprint)

        val resolved = if (ptCols.contains("tag") && tagCols.contains("tag")) {
            """
                LEFT JOIN print_tags pt ON pt.print_id = p.print_id
                LEFT JOIN tags t ON t.tag = pt.tag
            """.trimIndent()
        } else if (ptCols.contains("tag_id") && tagCols.contains("tag_id")) {
            """
                LEFT JOIN print_tags pt ON pt.print_id = p.print_id
                LEFT JOIN tags t ON t.tag_id = pt.tag_id
            """.trimIndent()
        } else {
            null
        }

        if (cacheFingerprint != null) {
            synchronized(this) {
                val cache = schemaCacheFor(cacheFingerprint)
                cache.tagJoinResolved = true
                cache.tagJoinSql = resolved
            }
        }
        return resolved
    }

    private fun tableExists(db: SQLiteDatabase, table: String): Boolean {
        return db.rawQuery(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            arrayOf(table),
        ).useCursor { cursor -> cursor.moveToFirst() }
    }

    private fun tableColumns(
        db: SQLiteDatabase,
        table: String,
        fingerprint: DbFingerprint? = null,
    ): Set<String> {
        val cacheFingerprint = fingerprint ?: dbFingerprint()
        if (cacheFingerprint != null) {
            val cached = synchronized(this) { schemaCacheFor(cacheFingerprint).tableColumns[table] }
            if (cached != null) {
                return cached
            }
        }

        val columns = db.rawQuery("PRAGMA table_info($table)", null).useCursor { cursor ->
            val out = mutableSetOf<String>()
            while (cursor.moveToNext()) {
                val name = cursor.getStringOrEmpty("name")
                if (name.isNotBlank()) {
                    out += name
                }
            }
            out
        }

        if (cacheFingerprint != null) {
            synchronized(this) {
                schemaCacheFor(cacheFingerprint).tableColumns[table] = columns
            }
        }
        return columns
    }

    private fun sqlNormalizeExpr(column: String): String {
        return "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(COALESCE($column,'')), ' ', ''), char(9), ''), char(10), ''), char(13), ''), '#', ''), '_', ''), '-', ''), '/', ''), '|', ''), ',', ''), '.', '')"
    }

    companion object {
        private const val SNAPSHOT_CACHE_LIMIT = 256
        private val EDGE_DASHES = setOf('-', '\u2013', '\u2014', '\u2015', '\u30FC')

        /** Strip leading and trailing Unicode dashes from display name */
        fun cleanDisplayName(name: String): String {
            var result = name.trim()
            while (result.isNotEmpty() && result.last() in EDGE_DASHES) {
                result = result.dropLast(1).trim()
            }
            while (result.isNotEmpty() && result.first() in EDGE_DASHES) {
                result = result.drop(1).trim()
            }
            return result
        }
    }

    private fun openReadOnly(): SQLiteDatabase {
        return SQLiteDatabase.openDatabase(
            paths.dbFile.absolutePath,
            null,
            SQLiteDatabase.OPEN_READONLY,
        )
    }

    private fun buildSearchTerms(q: String): List<String> {
        val splitTerms = q
            .split(Regex("[\\s,|/]+"))
            .filter { normalizeTerm(it).length >= 3 }

        val baseTerms = uniqueTerms(listOf(q) + splitTerms)
        val expanded = baseTerms.toMutableList()

        for (term in baseTerms) {
            for ((key, aliases) in TAG_ALIAS) {
                val aliasTerms = listOf(key) + aliases
                if (aliasTerms.any { alias -> isRelatedTerm(term, alias) }) {
                    expanded += aliasTerms
                }
            }
        }
        return uniqueTerms(expanded)
    }

    private fun uniqueTerms(values: List<String>): List<String> {
        val out = mutableListOf<String>()
        val seen = mutableSetOf<String>()
        for (value in values) {
            val normalized = value.trim()
            if (normalized.isEmpty() || seen.contains(normalized)) {
                continue
            }
            seen += normalized
            out += normalized
        }
        return out
    }

    private fun normalizeTerm(text: String): String {
        var out = text.trim().lowercase()
        listOf(" ", "\t", "\n", "\r", "#", "_", "-", "/", "|", ",", ".").forEach { token ->
            out = out.replace(token, "")
        }
        return out
    }

    private fun isRelatedTerm(a: String, b: String): Boolean {
        val na = normalizeTerm(a)
        val nb = normalizeTerm(b)
        if (na.isEmpty() || nb.isEmpty()) {
            return false
        }
        if (na == nb) {
            return true
        }
        if (na.length < 2 || nb.length < 2) {
            return false
        }
        return na.contains(nb) || nb.contains(na)
    }
}

private fun Cursor.getStringOrEmpty(columnName: String): String {
    val idx = getColumnIndex(columnName)
    if (idx < 0 || isNull(idx)) {
        return ""
    }
    return getString(idx) ?: ""
}

private fun Cursor.getLongOrZero(columnName: String): Long {
    val idx = getColumnIndex(columnName)
    if (idx < 0 || isNull(idx)) {
        return 0L
    }
    return getLong(idx)
}

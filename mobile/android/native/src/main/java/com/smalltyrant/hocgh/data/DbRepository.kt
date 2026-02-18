package com.smalltyrant.hocgh.data

import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import com.smalltyrant.hocgh.model.CardDetail
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

    fun needsDbUpdate(): Boolean {
        val dbFile = paths.dbFile
        if (!dbFile.exists() || !dbFile.isFile || dbFile.length() <= 0L) {
            return true
        }

        return try {
            openReadOnly().useDb { db ->
                if (!tableExists(db, "prints")) {
                    true
                } else {
                    val cols = tableColumns(db, "prints")
                    val required = setOf("print_id", "card_number", "name_ja", "image_url")
                    if (!cols.containsAll(required)) {
                        return@useDb true
                    }
                    val count = db.rawQuery("SELECT COUNT(1) FROM prints", null).useCursor { cursor ->
                        if (cursor.moveToFirst()) cursor.getLong(0) else 0L
                    }
                    count <= 0L
                }
            }
        } catch (_: Throwable) {
            true
        }
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
                val joins = buildTagJoinSql(db)
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
                val joins = buildTagJoinSql(db)
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

    fun loadCardDetail(printId: Long): CardDetail? {
        return try {
            openReadOnly().useDb { db ->
                db.rawQuery(
                    """
                    SELECT
                        COALESCE(ko.effect_text,'') AS ko_text
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    WHERE p.print_id=?
                    """.trimIndent(),
                    arrayOf(printId.toString()),
                ).useCursor { cursor ->
                    if (!cursor.moveToFirst()) {
                        return@useCursor null
                    }
                    CardDetail(koText = cursor.getStringOrEmpty("ko_text"))
                }
            }
        } catch (_: Throwable) {
            null
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

    private fun buildTagJoinSql(db: SQLiteDatabase): String? {
        val ptCols = tableColumns(db, "print_tags")
        val tagCols = tableColumns(db, "tags")

        if (ptCols.contains("tag") && tagCols.contains("tag")) {
            return """
                LEFT JOIN print_tags pt ON pt.print_id = p.print_id
                LEFT JOIN tags t ON t.tag = pt.tag
            """.trimIndent()
        }
        if (ptCols.contains("tag_id") && tagCols.contains("tag_id")) {
            return """
                LEFT JOIN print_tags pt ON pt.print_id = p.print_id
                LEFT JOIN tags t ON t.tag_id = pt.tag_id
            """.trimIndent()
        }
        return null
    }

    private fun tableExists(db: SQLiteDatabase, table: String): Boolean {
        return db.rawQuery(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            arrayOf(table),
        ).useCursor { cursor -> cursor.moveToFirst() }
    }

    private fun tableColumns(db: SQLiteDatabase, table: String): Set<String> {
        return db.rawQuery("PRAGMA table_info($table)", null).useCursor { cursor ->
            val out = mutableSetOf<String>()
            while (cursor.moveToNext()) {
                val name = cursor.getStringOrEmpty("name")
                if (name.isNotBlank()) {
                    out += name
                }
            }
            out
        }
    }

    private fun sqlNormalizeExpr(column: String): String {
        return "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(COALESCE($column,'')), ' ', ''), char(9), ''), char(10), ''), char(13), ''), '#', ''), '_', ''), '-', ''), '/', ''), '|', ''), ',', ''), '.', '')"
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

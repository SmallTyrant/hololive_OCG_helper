import Foundation
import SQLite3

private let tagAlias: [String: [String]] = [
    "동물귀": ["인권없음"],
    "인권없음": ["동물귀"],
]

final class DatabaseRepository {
    private let paths: AppPaths
    private let rarityOrder = ["C", "U", "R", "RR", "SR", "S", "RE", "RRR", "OSR", "OUR", "UR", "SEC", "SY", "OC", "HR", "P"]

    private struct DbFingerprint: Equatable {
        let path: String
        let size: UInt64
        let modifiedAt: TimeInterval
    }

    private struct DbHealthCache {
        let fingerprint: DbFingerprint
        let needsUpdate: Bool
    }

    private struct SchemaCache {
        let fingerprint: DbFingerprint
        var tableColumns: [String: Set<String>] = [:]
        var tagJoinResolved = false
        var tagJoinSql: String?
    }

    private struct SnapshotCache {
        let fingerprint: DbFingerprint
        var snapshots: [Int64: CardSnapshot] = [:]
        var lru: [Int64] = []
    }

    private let cacheLock = NSLock()
    private var dbHealthCache: DbHealthCache?
    private var schemaCache: SchemaCache?
    private var snapshotCache: SnapshotCache?

    private let snapshotCacheLimit = 256

    init(paths: AppPaths) {
        self.paths = paths
    }

    func needsDbUpdate() -> Bool {
        let dbPath = paths.dbURL.path
        guard let fingerprint = dbFingerprint(path: dbPath) else {
            clearCaches()
            return true
        }

        if let cached = cachedNeedsDbUpdate(for: fingerprint) {
            return cached
        }

        let needsUpdate: Bool

        do {
            needsUpdate = try withSQLite(path: dbPath, readOnly: true) { db in
                guard try tableExists(db: db, table: "prints") else {
                    return true
                }
                let columns = try tableColumns(db: db, table: "prints", fingerprint: fingerprint)
                let required: Set<String> = ["print_id", "card_number", "name_ja", "image_url"]
                guard columns.isSuperset(of: required) else {
                    return true
                }
                // prints 테이블 행 유무는 체크하지 않음.
                // 행이 없어도 파일과 스키마가 정상이면 "DB 없음" 판정하지 않는다.
                // (prints가 비어있는 상태를 "DB 없음"으로 오탐하는 버그 수정)
                return false
            }
        } catch {
            needsUpdate = true
        }

        storeNeedsDbUpdate(needsUpdate, for: fingerprint)
        return needsUpdate
    }

    func querySuggest(_ query: String, limit: Int? = nil) -> [PrintRow] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return [] }

        let like = "%\(q)%"
        let terms = buildSearchTerms(q)
        let normalizedTerms = unique(terms.map(normalizeTerm).filter { !$0.isEmpty })

        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let sessionFingerprint = dbFingerprint(path: paths.dbURL.path)
                let joins = try buildTagJoinSql(db: db, fingerprint: sessionFingerprint)
                if let joins {
                    var params: [SQLiteBindValue] = [
                        .text(like), .text(like), .text(like), .text(like), .text(like), .text(like),
                    ]

                    var sql = """
                    SELECT DISTINCT
                        p.print_id,
                        p.card_number,
                        COALESCE(p.name_ja,'') AS name_ja,
                        COALESCE(ko.name,'') AS name_ko
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    \(joins)
                    WHERE
                        UPPER(p.card_number) LIKE UPPER(?)
                        OR COALESCE(p.name_ja,'') LIKE ?
                        OR COALESCE(ko.name,'') LIKE ?
                        OR COALESCE(ko.effect_text,'') LIKE ?
                        OR (t.tag IS NOT NULL AND (t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?))
                    """

                    for term in terms {
                        sql += " OR t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?"
                        params.append(.text("%\(term)%"))
                        params.append(.text("%\(term)%"))
                    }

                    if !normalizedTerms.isEmpty {
                        let normCardNumber = sqlNormalizeExpr("p.card_number")
                        let normTag = sqlNormalizeExpr("t.tag")
                        let normNormalized = sqlNormalizeExpr("t.normalized")
                        let normNameJa = sqlNormalizeExpr("p.name_ja")
                        let normNameKo = sqlNormalizeExpr("ko.name")
                        let normEffectText = sqlNormalizeExpr("ko.effect_text")
                        for term in normalizedTerms {
                            sql += " OR \(normCardNumber) LIKE ? OR \(normTag) LIKE ? OR \(normNormalized) LIKE ?"
                            sql += " OR \(normNameJa) LIKE ? OR \(normNameKo) LIKE ? OR \(normEffectText) LIKE ?"
                            params.append(.text("%\(term)%"))
                            params.append(.text("%\(term)%"))
                            params.append(.text("%\(term)%"))
                            params.append(.text("%\(term)%"))
                            params.append(.text("%\(term)%"))
                            params.append(.text("%\(term)%"))
                        }
                    }

                    sql += " ORDER BY p.card_number"
                    if let limit, limit > 0 {
                        sql += " LIMIT ?"
                        params.append(.int64(Int64(limit)))
                    }
                    return try runPrintRowsQuery(db: db, sql: sql, params: params)
                }

                var params: [SQLiteBindValue] = [.text(like), .text(like), .text(like), .text(like)]
                var sql = """
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
                """
                if !normalizedTerms.isEmpty {
                    let normCardNumber = sqlNormalizeExpr("p.card_number")
                    let normNameJa = sqlNormalizeExpr("p.name_ja")
                    let normNameKo = sqlNormalizeExpr("ko.name")
                    let normEffectText = sqlNormalizeExpr("ko.effect_text")
                    for term in normalizedTerms {
                        sql += " OR \(normCardNumber) LIKE ? OR \(normNameJa) LIKE ? OR \(normNameKo) LIKE ? OR \(normEffectText) LIKE ?"
                        params.append(.text("%\(term)%"))
                        params.append(.text("%\(term)%"))
                        params.append(.text("%\(term)%"))
                        params.append(.text("%\(term)%"))
                    }
                }
                sql += " ORDER BY p.card_number"
                if let limit, limit > 0 {
                    sql += " LIMIT ?"
                    params.append(.int64(Int64(limit)))
                }
                return try runPrintRowsQuery(db: db, sql: sql, params: params)
            }
        } catch {
            return []
        }
    }

    func queryExact(_ query: String, limit: Int? = nil) -> [PrintRow] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return [] }

        let normalizedQ = normalizeTerm(q)

        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let sessionFingerprint = dbFingerprint(path: paths.dbURL.path)
                let joins = try buildTagJoinSql(db: db, fingerprint: sessionFingerprint)
                if let joins {
                    var params: [SQLiteBindValue] = [.text(q), .text(q), .text(q), .text(q), .text(q)]
                    var sql = """
                    SELECT DISTINCT
                        p.print_id,
                        p.card_number,
                        COALESCE(p.name_ja,'') AS name_ja,
                        COALESCE(ko.name,'') AS name_ko
                    FROM prints p
                    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                    \(joins)
                    WHERE
                        UPPER(COALESCE(p.card_number,'')) = UPPER(?)
                        OR LOWER(COALESCE(p.name_ja,'')) = LOWER(?)
                        OR LOWER(COALESCE(ko.name,'')) = LOWER(?)
                        OR (
                            t.tag IS NOT NULL
                            AND (
                                LOWER(COALESCE(t.tag,'')) = LOWER(?)
                                OR LOWER(COALESCE(t.normalized,'')) = LOWER(?)
                    """

                    if !normalizedQ.isEmpty {
                        let normTag = sqlNormalizeExpr("t.tag")
                        let normNormalized = sqlNormalizeExpr("t.normalized")
                        sql += " OR \(normTag) = ? OR \(normNormalized) = ?"
                        params.append(.text(normalizedQ))
                        params.append(.text(normalizedQ))
                    }

                    sql += """
                            )
                        )
                    """
                    if !normalizedQ.isEmpty {
                        let normCardNumber = sqlNormalizeExpr("p.card_number")
                        let normNameJa = sqlNormalizeExpr("p.name_ja")
                        let normNameKo = sqlNormalizeExpr("ko.name")
                        sql += " OR \(normCardNumber) = ? OR \(normNameJa) = ? OR \(normNameKo) = ?"
                        params.append(.text(normalizedQ))
                        params.append(.text(normalizedQ))
                        params.append(.text(normalizedQ))
                    }
                    sql += " ORDER BY p.card_number"

                    if let limit, limit > 0 {
                        sql += " LIMIT ?"
                        params.append(.int64(Int64(limit)))
                    }
                    return try runPrintRowsQuery(db: db, sql: sql, params: params)
                }

                var params: [SQLiteBindValue] = [.text(q), .text(q), .text(q)]
                var sql = """
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
                """
                if !normalizedQ.isEmpty {
                    let normCardNumber = sqlNormalizeExpr("p.card_number")
                    let normNameJa = sqlNormalizeExpr("p.name_ja")
                    let normNameKo = sqlNormalizeExpr("ko.name")
                    sql += " OR \(normCardNumber) = ? OR \(normNameJa) = ? OR \(normNameKo) = ?"
                    params.append(.text(normalizedQ))
                    params.append(.text(normalizedQ))
                    params.append(.text(normalizedQ))
                }
                sql += " ORDER BY p.card_number"
                if let limit, limit > 0 {
                    sql += " LIMIT ?"
                    params.append(.int64(Int64(limit)))
                }
                return try runPrintRowsQuery(db: db, sql: sql, params: params)
            }
        } catch {
            return []
        }
    }

    func listDeckCards(query: String, limit: Int = 240) -> [DeckCardCandidate] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let like = "%\(q)%"
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let sql = """
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
                    COALESCE(ko.effect_text,'') AS ko_text,
                    COALESCE(ja.effect_text,'') AS ja_text,
                    (SELECT GROUP_CONCAT(ci.rarity || '|' || COALESCE(ci.manage_id_jp,'') || '|' || COALESCE(ci.image_url,''), ';;')
                     FROM card_illustrations ci WHERE ci.card_number = p.card_number
                     ORDER BY ci.is_default DESC, ci.illustration_id) AS illustrations_csv
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
                """
                let stmt = try sqlitePrepare(db: db, sql: sql)
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.text(like), .text(like), .text(like), .text(like), .int64(Int64(limit))], to: stmt)
                var rows: [DeckCardCandidate] = []
                while sqlite3_step(stmt) == SQLITE_ROW {
                    let illustrationsCSV = sqliteColumnString(stmt, index: 10)
                    let illustrations = parseIllustrationsCSV(illustrationsCSV)
                    rows.append(
                        DeckCardCandidate(
                            printId: sqliteColumnInt64(stmt, index: 0),
                            cardNumber: sqliteColumnString(stmt, index: 1),
                            nameJa: sqliteColumnString(stmt, index: 2),
                            nameKo: sqliteColumnString(stmt, index: 3),
                            imageUrl: sqliteColumnString(stmt, index: 4),
                            cardType: sqliteColumnString(stmt, index: 5),
                            color: sqliteColumnString(stmt, index: 6),
                            rarity: sqliteColumnString(stmt, index: 7),
                            koText: sqliteColumnString(stmt, index: 8),
                            jaText: sqliteColumnString(stmt, index: 9),
                            illustrations: illustrations,
                        )
                    )
                }
                return rows
            }
        } catch {
            return []
        }
    }

    func getPrintBrief(printId: Int64) -> PrintBrief? {
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let sql = """
                SELECT
                    p.print_id,
                    p.card_number,
                    COALESCE(p.name_ja,'') AS name_ja,
                    COALESCE(ko.name,'') AS name_ko,
                    COALESCE(p.image_url,'') AS image_url
                FROM prints p
                LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                WHERE p.print_id=?
                """
                let stmt = try sqlitePrepare(db: db, sql: sql)
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.int64(printId)], to: stmt)
                guard sqlite3_step(stmt) == SQLITE_ROW else {
                    throw NSError(domain: "DatabaseRepository", code: 404)
                }
                return PrintBrief(
                    printId: sqliteColumnInt64(stmt, index: 0),
                    cardNumber: sqliteColumnString(stmt, index: 1),
                    nameJa: sqliteColumnString(stmt, index: 2),
                    nameKo: sqliteColumnString(stmt, index: 3),
                    imageUrl: sqliteColumnString(stmt, index: 4),
                )
            }
        } catch {
            return nil
        }
    }

    func loadCardDetail(printId: Int64) -> CardDetail? {
        loadCardSnapshot(printId: printId)?.detail
    }

    func loadCardSnapshot(printId: Int64) -> CardSnapshot? {
        guard let fingerprint = dbFingerprint(path: paths.dbURL.path) else {
            return nil
        }

        if let cached = cachedSnapshot(printId: printId, fingerprint: fingerprint) {
            return cached
        }

        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let sessionFingerprint: DbFingerprint? = fingerprint
                let jaColumns = try tableColumns(db: db, table: "card_texts_ja", fingerprint: sessionFingerprint)
                let hasJaEffectText = jaColumns.contains("effect_text")
                let sql = hasJaEffectText ?
                """
                SELECT
                    p.print_id,
                    COALESCE(p.card_number,'') AS card_number,
                    COALESCE(p.name_ja,'') AS name_ja,
                    COALESCE(ko.name,'') AS name_ko,
                    COALESCE(p.image_url,'') AS image_url,
                    COALESCE(ko.effect_text,'') AS ko_text,
                    COALESCE(ja.effect_text,'') AS ja_text,
                    (SELECT GROUP_CONCAT(ci.rarity || '|' || COALESCE(ci.manage_id_jp,'') || '|' || COALESCE(ci.image_url,''), ';;')
                     FROM card_illustrations ci WHERE ci.card_number = p.card_number
                     ORDER BY ci.is_default DESC, ci.illustration_id) AS illustrations_csv,
                    COALESCE(ko.name,'') AS ko_name
                FROM prints p
                LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
                WHERE p.print_id=?
                """
                :
                """
                SELECT
                    p.print_id,
                    COALESCE(p.card_number,'') AS card_number,
                    COALESCE(p.name_ja,'') AS name_ja,
                    COALESCE(ko.name,'') AS name_ko,
                    COALESCE(p.image_url,'') AS image_url,
                    COALESCE(ko.effect_text,'') AS ko_text,
                    '' AS ja_text,
                    (SELECT GROUP_CONCAT(ci.rarity || '|' || COALESCE(ci.manage_id_jp,'') || '|' || COALESCE(ci.image_url,''), ';;')
                     FROM card_illustrations ci WHERE ci.card_number = p.card_number
                     ORDER BY ci.is_default DESC, ci.illustration_id) AS illustrations_csv,
                    COALESCE(ko.name,'') AS ko_name
                FROM prints p
                LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                WHERE p.print_id=?
                """
                let stmt = try sqlitePrepare(db: db, sql: sql)
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.int64(printId)], to: stmt)
                guard sqlite3_step(stmt) == SQLITE_ROW else {
                    throw NSError(domain: "DatabaseRepository", code: 404)
                }

                let brief = PrintBrief(
                    printId: sqliteColumnInt64(stmt, index: 0),
                    cardNumber: sqliteColumnString(stmt, index: 1),
                    nameJa: sqliteColumnString(stmt, index: 2),
                    nameKo: sqliteColumnString(stmt, index: 3),
                    imageUrl: sqliteColumnString(stmt, index: 4),
                    illustrations: parseIllustrationsCSV(sqliteColumnString(stmt, index: 7))
                )

                var koTextRaw = sqliteColumnString(stmt, index: 5)
                let jaTextRaw = sqliteColumnString(stmt, index: 6)
                let koName = Self.cleanDisplayName(sqliteColumnString(stmt, index: 8))

                // Strip duplicate card name from start of effect_text
                if !koName.isEmpty {
                    let trimmed = koTextRaw.trimmingCharacters(in: .whitespacesAndNewlines)
                    if trimmed.hasPrefix(koName) {
                        koTextRaw = String(trimmed.dropFirst(koName.count))
                            .trimmingCharacters(in: .whitespacesAndNewlines)
                    }
                }
                let tags = try loadTagsForPrint(db: db, printId: printId, fingerprint: sessionFingerprint)

                let detail = CardDetail(
                    koText: appendTagsIfNeeded(to: koTextRaw, tags: tags, sectionLabel: "태그"),
                    jaText: appendTagsIfNeeded(to: jaTextRaw, tags: tags, sectionLabel: "タグ"),
                )

                let snapshot = CardSnapshot(brief: brief, detail: detail)
                storeSnapshot(snapshot, printId: printId, fingerprint: fingerprint)
                return snapshot
            }
        } catch {
            return nil
        }
    }

    func listImageTargets() -> [(cardNumber: String, imageURL: String)] {
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let stmt = try sqlitePrepare(
                    db: db,
                    sql: """
                    SELECT card_number, image_url FROM (
                        SELECT
                            COALESCE(p.card_number,'') AS card_number,
                            COALESCE(p.image_url,'') AS image_url,
                            0 AS priority
                        FROM prints p
                        UNION ALL
                        SELECT
                            COALESCE(ci.card_number,'') AS card_number,
                            COALESCE(ci.image_url,'') AS image_url,
                            1 AS priority
                        FROM card_illustrations ci
                    ) src
                    WHERE COALESCE(card_number,'') <> ''
                    ORDER BY card_number, priority
                    """,
                )
                defer { sqlite3_finalize(stmt) }

                var out: [(cardNumber: String, imageURL: String)] = []
                var indexByCard: [String: Int] = [:]
                while sqlite3_step(stmt) == SQLITE_ROW {
                    let cardNumber = sqliteColumnString(stmt, index: 0).trimmingCharacters(in: .whitespacesAndNewlines)
                    if cardNumber.isEmpty {
                        continue
                    }
                    let imageURL = sqliteColumnString(stmt, index: 1).trimmingCharacters(in: .whitespacesAndNewlines)
                    if let existingIndex = indexByCard[cardNumber] {
                        if out[existingIndex].imageURL.isEmpty, !imageURL.isEmpty {
                            out[existingIndex] = (cardNumber: cardNumber, imageURL: imageURL)
                        }
                        continue
                    }
                    indexByCard[cardNumber] = out.count
                    out.append((cardNumber: cardNumber, imageURL: imageURL))
                }
                return out
            }
        } catch {
            return []
        }
    }

    /// prints 테이블의 manage_id_jp 컬럼 값 반환 (부시나비 내보내기용)
    func getManageIdJp(printId: Int64) -> Int? {
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let cols = try tableColumns(db: db, table: "prints", fingerprint: nil)
                guard cols.contains("manage_id_jp") else { return nil }
                let stmt = try sqlitePrepare(db: db, sql: "SELECT manage_id_jp FROM prints WHERE print_id=?")
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.int64(printId)], to: stmt)
                guard sqlite3_step(stmt) == SQLITE_ROW else { return nil }
                if sqlite3_column_type(stmt, 0) == SQLITE_NULL { return nil }
                return Int(sqliteColumnInt64(stmt, index: 0))
            }
        } catch {
            return nil
        }
    }

    /// card_number 로 manage_id_jp 조회
    func getManageIdJpByCardNumber(_ cardNumber: String) -> Int? {
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let cols = try tableColumns(db: db, table: "prints", fingerprint: nil)
                guard cols.contains("manage_id_jp") else { return nil }
                let stmt = try sqlitePrepare(db: db, sql: "SELECT manage_id_jp FROM prints WHERE card_number=?")
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.text(cardNumber)], to: stmt)
                guard sqlite3_step(stmt) == SQLITE_ROW else { return nil }
                if sqlite3_column_type(stmt, 0) == SQLITE_NULL { return nil }
                return Int(sqliteColumnInt64(stmt, index: 0))
            }
        } catch {
            return nil
        }
    }

    func loadMultiWordTags() -> [String] {
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                var allTags: [String] = []
                var seen = Set<String>()
                for table in ["tags", "tags_ja", "tags_ko"] {
                    guard try tableExists(db: db, table: table) else { continue }
                    let sql = "SELECT tag FROM \(table) WHERE tag LIKE '% %' ORDER BY LENGTH(tag) DESC"
                    let stmt = try sqlitePrepare(db: db, sql: sql)
                    defer { sqlite3_finalize(stmt) }
                    while sqlite3_step(stmt) == SQLITE_ROW {
                        var tag = sqliteColumnString(stmt, index: 0).trimmingCharacters(in: .whitespacesAndNewlines)
                        if !tag.isEmpty {
                            if !tag.hasPrefix("#") { tag = "#\(tag)" }
                            if seen.insert(tag).inserted {
                                allTags.append(tag)
                            }
                        }
                    }
                }
                return allTags.sorted { $0.count > $1.count }
            }
        } catch {
            return []
        }
    }

    func localDbDate() -> String? {
        let path = paths.dbURL.path
        let fm = FileManager.default

        guard fm.fileExists(atPath: path) else {
            return nil
        }

        do {
            let inDbDate: String? = try withSQLite(path: path, readOnly: true) { db in
                if try tableExists(db: db, table: "meta") {
                    for key in ["release_asset_updated_at", "release_published_at", "release_created_at"] {
                        let stmt = try sqlitePrepare(db: db, sql: "SELECT value FROM meta WHERE key=?")
                        defer { sqlite3_finalize(stmt) }
                        try sqliteBind([.text(key)], to: stmt)
                        if sqlite3_step(stmt) == SQLITE_ROW {
                            let value = sqliteColumnOptionalString(stmt, index: 0)
                            if let normalized = formatIsoDateOrNil(value) {
                                return normalized
                            }
                        }
                    }
                }

                for table in ["prints", "card_texts_ko", "card_texts_ja"] {
                    guard try tableExists(db: db, table: table) else {
                        continue
                    }
                    let stmt = try sqlitePrepare(
                        db: db,
                        sql: "SELECT MAX(updated_at) FROM \(table) WHERE updated_at IS NOT NULL AND updated_at <> ''",
                    )
                    defer { sqlite3_finalize(stmt) }
                    if sqlite3_step(stmt) == SQLITE_ROW {
                        let value = sqliteColumnOptionalString(stmt, index: 0)
                        if let normalized = formatIsoDateOrNil(value) {
                            return normalized
                        }
                    }
                }
                return nil
            }

            if let inDbDate {
                return inDbDate
            }
        } catch {
            // Fallback below.
        }

        guard let attrs = try? fm.attributesOfItem(atPath: path),
              let modified = attrs[.modificationDate] as? Date else {
            return nil
        }

        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: modified)
    }

    func localDbDigest() -> String? {
        let path = paths.dbURL.path
        let fm = FileManager.default
        guard fm.fileExists(atPath: path) else {
            return nil
        }

        do {
            return try withSQLite(path: path, readOnly: true) { db in
                guard try tableExists(db: db, table: "meta") else {
                    return nil
                }
                let stmt = try sqlitePrepare(db: db, sql: "SELECT value FROM meta WHERE key=?")
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.text("release_asset_digest")], to: stmt)
                if sqlite3_step(stmt) == SQLITE_ROW {
                    return normalizeHashText(sqliteColumnOptionalString(stmt, index: 0))
                }
                return nil
            }
        } catch {
            return nil
        }
    }

    private func normalizeHashText(_ raw: String?) -> String? {
        let value = (raw ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !value.isEmpty else { return nil }
        if value.hasPrefix("sha256:") {
            let trimmed = String(value.dropFirst("sha256:".count)).trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : trimmed
        }
        return value
    }

    private func dbFingerprint(path: String) -> DbFingerprint? {
        let fm = FileManager.default
        guard fm.fileExists(atPath: path) else {
            return nil
        }
        guard let attrs = try? fm.attributesOfItem(atPath: path),
              let sizeValue = attrs[.size] as? NSNumber else {
            return nil
        }
        let size = sizeValue.uint64Value
        guard size > 0 else {
            return nil
        }
        let modifiedAt = (attrs[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0
        return DbFingerprint(path: path, size: size, modifiedAt: modifiedAt)
    }

    private func clearCaches() {
        cacheLock.lock()
        dbHealthCache = nil
        schemaCache = nil
        snapshotCache = nil
        cacheLock.unlock()
    }

    private func cachedNeedsDbUpdate(for fingerprint: DbFingerprint) -> Bool? {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        guard let cache = dbHealthCache, cache.fingerprint == fingerprint else {
            return nil
        }
        return cache.needsUpdate
    }

    private func storeNeedsDbUpdate(_ needsUpdate: Bool, for fingerprint: DbFingerprint) {
        cacheLock.lock()
        dbHealthCache = DbHealthCache(fingerprint: fingerprint, needsUpdate: needsUpdate)
        cacheLock.unlock()
    }

    private func cachedSnapshot(printId: Int64, fingerprint: DbFingerprint) -> CardSnapshot? {
        cacheLock.lock()
        defer { cacheLock.unlock() }

        guard var cache = snapshotCache, cache.fingerprint == fingerprint else {
            return nil
        }
        guard let snapshot = cache.snapshots[printId] else {
            return nil
        }

        cache.lru.removeAll(where: { $0 == printId })
        cache.lru.append(printId)
        snapshotCache = cache
        return snapshot
    }

    private func storeSnapshot(_ snapshot: CardSnapshot, printId: Int64, fingerprint: DbFingerprint) {
        cacheLock.lock()
        defer { cacheLock.unlock() }

        var cache: SnapshotCache
        if let current = snapshotCache, current.fingerprint == fingerprint {
            cache = current
        } else {
            cache = SnapshotCache(fingerprint: fingerprint)
        }

        cache.snapshots[printId] = snapshot
        cache.lru.removeAll(where: { $0 == printId })
        cache.lru.append(printId)

        while cache.lru.count > snapshotCacheLimit {
            guard let oldest = cache.lru.first else { break }
            cache.lru.removeFirst()
            cache.snapshots.removeValue(forKey: oldest)
        }

        snapshotCache = cache
    }

    private func ensureSchemaCacheLocked(for fingerprint: DbFingerprint) {
        if schemaCache?.fingerprint != fingerprint {
            schemaCache = SchemaCache(fingerprint: fingerprint)
            if dbHealthCache?.fingerprint != fingerprint {
                dbHealthCache = nil
            }
        }
    }

    private func cachedTableColumns(for table: String, fingerprint: DbFingerprint) -> Set<String>? {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        guard let cache = schemaCache, cache.fingerprint == fingerprint else {
            return nil
        }
        return cache.tableColumns[table]
    }

    private func storeTableColumns(_ columns: Set<String>, for table: String, fingerprint: DbFingerprint) {
        cacheLock.lock()
        ensureSchemaCacheLocked(for: fingerprint)
        schemaCache?.tableColumns[table] = columns
        cacheLock.unlock()
    }

    private func cachedTagJoin(fingerprint: DbFingerprint) -> (resolved: Bool, sql: String?) {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        guard let cache = schemaCache, cache.fingerprint == fingerprint else {
            return (false, nil)
        }
        return (cache.tagJoinResolved, cache.tagJoinSql)
    }

    private func storeTagJoin(_ sql: String?, fingerprint: DbFingerprint) {
        cacheLock.lock()
        ensureSchemaCacheLocked(for: fingerprint)
        schemaCache?.tagJoinResolved = true
        schemaCache?.tagJoinSql = sql
        cacheLock.unlock()
    }

    private func runPrintRowsQuery(
        db: OpaquePointer,
        sql: String,
        params: [SQLiteBindValue],
    ) throws -> [PrintRow] {
        let stmt = try sqlitePrepare(db: db, sql: sql)
        defer { sqlite3_finalize(stmt) }
        try sqliteBind(params, to: stmt)

        var rows: [PrintRow] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            rows.append(
                PrintRow(
                    printId: sqliteColumnInt64(stmt, index: 0),
                    cardNumber: sqliteColumnString(stmt, index: 1),
                    nameJa: sqliteColumnString(stmt, index: 2),
                    nameKo: sqliteColumnString(stmt, index: 3),
                )
            )
        }
        return rows
    }

     private func loadTagsForPrint(
        db: OpaquePointer,
        printId: Int64,
        fingerprint: DbFingerprint? = nil,
    ) throws -> [String] {
        guard let tagJoinSql = try buildTagJoinSql(db: db, fingerprint: fingerprint) else {
            return []
        }

        // tags_ko 테이블이 있으면 한국어 태그를 우선 사용, 없으면 원본 태그 사용
        let hasTagsKo = (try? tableExists(db: db, table: "tags_ko")) ?? false
        let tagSelect = hasTagsKo ? "COALESCE(ko.tag, t.tag, '') AS tag" : "COALESCE(t.tag,'') AS tag"
        let koJoin = hasTagsKo ? "LEFT JOIN tags_ko ko ON ko.tag_id = t.tag_id" : ""

        let sql = """
        SELECT \(tagSelect)
        FROM prints p
        \(tagJoinSql)
        \(koJoin)
        WHERE p.print_id=?
        ORDER BY t.tag
        """

        let stmt = try sqlitePrepare(db: db, sql: sql)
        defer { sqlite3_finalize(stmt) }
        try sqliteBind([.int64(printId)], to: stmt)

        var tags: [String] = []
        var seen: Set<String> = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            var tag = sqliteColumnString(stmt, index: 0).trimmingCharacters(in: .whitespacesAndNewlines)
            guard !tag.isEmpty else {
                continue
            }
            if !tag.hasPrefix("#") {
                tag = "#\(tag)"
            }
            if seen.insert(tag).inserted {
                tags.append(tag)
            }
        }
        return tags
    }

    private func appendTagsIfNeeded(to text: String, tags: [String], sectionLabel: String) -> String {
        guard !tags.isEmpty else {
            return text
        }

        let lines = text
            .split(whereSeparator: { $0.isNewline })
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        let hasStandaloneTagSection = lines.contains(sectionLabel) || lines.contains { line in
            line.hasPrefix("#") &&
            line.split(whereSeparator: { $0.isWhitespace }).allSatisfy { $0.hasPrefix("#") }
        }
        if hasStandaloneTagSection {
            return text
        }

        let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let tagLine = tags.joined(separator: " ")
        if normalized.isEmpty {
            return "\(sectionLabel)\n\(tagLine)"
        }
        return "\(normalized)\n\(sectionLabel)\n\(tagLine)"
    }

    private func buildTagJoinSql(
        db: OpaquePointer,
        fingerprint: DbFingerprint? = nil,
    ) throws -> String? {
        let cacheFingerprint = fingerprint ?? dbFingerprint(path: paths.dbURL.path)
        if let cacheFingerprint {
            let cached = cachedTagJoin(fingerprint: cacheFingerprint)
            if cached.resolved {
                return cached.sql
            }
        }

        let printTagCols = try tableColumns(db: db, table: "print_tags", fingerprint: cacheFingerprint)
        let tagCols = try tableColumns(db: db, table: "tags", fingerprint: cacheFingerprint)

        let resolved: String?

        if printTagCols.contains("tag") && tagCols.contains("tag") {
            resolved = """
            LEFT JOIN print_tags pt ON pt.print_id = p.print_id
            LEFT JOIN tags t ON t.tag = pt.tag
            """
        } else if printTagCols.contains("tag_id") && tagCols.contains("tag_id") {
            resolved = """
            LEFT JOIN print_tags pt ON pt.print_id = p.print_id
            LEFT JOIN tags t ON t.tag_id = pt.tag_id
            """
        } else {
            resolved = nil
        }

        if let cacheFingerprint {
            storeTagJoin(resolved, fingerprint: cacheFingerprint)
        }
        return resolved
    }

    private func tableExists(db: OpaquePointer, table: String) throws -> Bool {
        let stmt = try sqlitePrepare(
            db: db,
            sql: "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        )
        defer { sqlite3_finalize(stmt) }
        try sqliteBind([.text(table)], to: stmt)
        return sqlite3_step(stmt) == SQLITE_ROW
    }

    private func tableColumns(
        db: OpaquePointer,
        table: String,
        fingerprint: DbFingerprint? = nil,
    ) throws -> Set<String> {
        let cacheFingerprint = fingerprint ?? dbFingerprint(path: paths.dbURL.path)
        if let cacheFingerprint,
           let cached = cachedTableColumns(for: table, fingerprint: cacheFingerprint) {
            return cached
        }

        let stmt = try sqlitePrepare(db: db, sql: "PRAGMA table_info(\(table))")
        defer { sqlite3_finalize(stmt) }

        var columns: Set<String> = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            let name = sqliteColumnString(stmt, index: 1)
            if !name.isEmpty {
                columns.insert(name)
            }
        }

        if let cacheFingerprint {
            storeTableColumns(columns, for: table, fingerprint: cacheFingerprint)
        }
        return columns
    }

    private func buildSearchTerms(_ query: String) -> [String] {
        let split = query
            .split(whereSeparator: { " ,|/\n\t\r".contains($0) })
            .map(String.init)
            .filter { normalizeTerm($0).count >= 3 }

        let base = unique([query] + split)
        var expanded = base

        for term in base {
            for (key, aliases) in tagAlias {
                let aliasTerms = [key] + aliases
                if aliasTerms.contains(where: { isRelatedTerm(term, $0) }) {
                    expanded.append(contentsOf: aliasTerms)
                }
            }
        }

        return unique(expanded)
    }

    private func unique(_ values: [String]) -> [String] {
        var seen: Set<String> = []
        var out: [String] = []
        for value in values {
            let v = value.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !v.isEmpty else { continue }
            guard !seen.contains(v) else { continue }
            seen.insert(v)
            out.append(v)
        }
        return out
    }

    private func normalizeTerm(_ text: String) -> String {
        var out = text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        [" ", "\t", "\n", "\r", "#", "_", "-", "/", "|", ",", "."].forEach {
            out = out.replacingOccurrences(of: $0, with: "")
        }
        return out
    }

    private func isRelatedTerm(_ a: String, _ b: String) -> Bool {
        let na = normalizeTerm(a)
        let nb = normalizeTerm(b)
        guard !na.isEmpty, !nb.isEmpty else {
            return false
        }
        if na == nb {
            return true
        }
        if na.count < 2 || nb.count < 2 {
            return false
        }
        return na.contains(nb) || nb.contains(na)
    }

    /// "rarity|manage_id_jp|image_url;;..." 형식의 CSV를 IllustrationOption 배열로 파싱
    private func parseIllustrationsCSV(_ csv: String) -> [IllustrationOption] {
        guard !csv.isEmpty else { return [] }
        return csv.components(separatedBy: ";;").compactMap { token -> IllustrationOption? in
            let parts = token.components(separatedBy: "|")
            guard parts.count >= 3 else { return nil }
            let rarity = parts[0].trimmingCharacters(in: .whitespaces)
            guard !rarity.isEmpty else { return nil }
            guard rarity.caseInsensitiveCompare("S") != .orderedSame else { return nil }
            let manageId = Int(parts[1])
            let imageUrl = parts[2].trimmingCharacters(in: .whitespaces)
            return IllustrationOption(rarity: rarity, manageIdJp: manageId, imageUrl: imageUrl)
        }.sorted { (lhs: IllustrationOption, rhs: IllustrationOption) in
            let left = rarityOrder.firstIndex(of: lhs.rarity.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()) ?? Int.max
            let right = rarityOrder.firstIndex(of: rhs.rarity.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()) ?? Int.max
            if left != right { return left < right }
            return lhs.rarity < rhs.rarity
        }
    }

    private func sqlNormalizeExpr(_ column: String) -> String {
        "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(COALESCE(\(column),'')), ' ', ''), char(9), ''), char(10), ''), char(13), ''), '#', ''), '_', ''), '-', ''), '/', ''), '|', ''), ',', ''), '.', '')"
    }

    /// Strip leading and trailing Unicode dashes from display name
    static func cleanDisplayName(_ name: String) -> String {
        var result = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let dashes: Set<Character> = ["-", "\u{2013}", "\u{2014}", "\u{2015}", "\u{30FC}"]
        while let last = result.last, dashes.contains(last) {
            result = String(result.dropLast()).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        while let first = result.first, dashes.contains(first) {
            result = String(result.dropFirst()).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        return result
    }
}

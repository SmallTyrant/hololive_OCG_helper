import Foundation
import SQLite3

private let tagAlias: [String: [String]] = [
    "동물귀": ["인권없음"],
    "인권없음": ["동물귀"],
]

final class DatabaseRepository {
    private let paths: AppPaths

    init(paths: AppPaths) {
        self.paths = paths
    }

    func needsDbUpdate() -> Bool {
        let dbPath = paths.dbURL.path
        let fm = FileManager.default
        guard fm.fileExists(atPath: dbPath) else {
            return true
        }
        guard let attrs = try? fm.attributesOfItem(atPath: dbPath),
              let size = attrs[.size] as? NSNumber,
              size.intValue > 0 else {
            return true
        }

        do {
            return try withSQLite(path: dbPath, readOnly: true) { db in
                guard try tableExists(db: db, table: "prints") else {
                    return true
                }
                let columns = try tableColumns(db: db, table: "prints")
                let required: Set<String> = ["print_id", "card_number", "name_ja", "image_url"]
                guard columns.isSuperset(of: required) else {
                    return true
                }
                let sql = "SELECT COUNT(1) FROM prints"
                let stmt = try sqlitePrepare(db: db, sql: sql)
                defer { sqlite3_finalize(stmt) }
                if sqlite3_step(stmt) == SQLITE_ROW {
                    return sqlite3_column_int64(stmt, 0) <= 0
                }
                return true
            }
        } catch {
            return true
        }
    }

    func querySuggest(_ query: String, limit: Int? = nil) -> [PrintRow] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return [] }

        let like = "%\(q)%"
        let terms = buildSearchTerms(q)
        let normalizedTerms = unique(terms.map(normalizeTerm).filter { !$0.isEmpty })

        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let joins = try buildTagJoinSql(db: db)
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
                let joins = try buildTagJoinSql(db: db)
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
                    return nil
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
        do {
            return try withSQLite(path: paths.dbURL.path, readOnly: true) { db in
                let sql = """
                SELECT
                    COALESCE(ko.effect_text,'') AS ko_text
                FROM prints p
                LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
                WHERE p.print_id=?
                """
                let stmt = try sqlitePrepare(db: db, sql: sql)
                defer { sqlite3_finalize(stmt) }
                try sqliteBind([.int64(printId)], to: stmt)
                guard sqlite3_step(stmt) == SQLITE_ROW else {
                    return nil
                }
                return CardDetail(koText: sqliteColumnString(stmt, index: 0))
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
                    SELECT
                        COALESCE(p.card_number,'') AS card_number,
                        COALESCE(p.image_url,'') AS image_url
                    FROM prints p
                    WHERE COALESCE(p.card_number,'') <> ''
                    ORDER BY p.card_number
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

    private func buildTagJoinSql(db: OpaquePointer) throws -> String? {
        let printTagCols = try tableColumns(db: db, table: "print_tags")
        let tagCols = try tableColumns(db: db, table: "tags")

        if printTagCols.contains("tag") && tagCols.contains("tag") {
            return """
            LEFT JOIN print_tags pt ON pt.print_id = p.print_id
            LEFT JOIN tags t ON t.tag = pt.tag
            """
        }

        if printTagCols.contains("tag_id") && tagCols.contains("tag_id") {
            return """
            LEFT JOIN print_tags pt ON pt.print_id = p.print_id
            LEFT JOIN tags t ON t.tag_id = pt.tag_id
            """
        }

        return nil
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

    private func tableColumns(db: OpaquePointer, table: String) throws -> Set<String> {
        let stmt = try sqlitePrepare(db: db, sql: "PRAGMA table_info(\(table))")
        defer { sqlite3_finalize(stmt) }

        var columns: Set<String> = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            let name = sqliteColumnString(stmt, index: 1)
            if !name.isEmpty {
                columns.insert(name)
            }
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

    private func sqlNormalizeExpr(_ column: String) -> String {
        "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(COALESCE(\(column),'')), ' ', ''), '#', ''), '_', ''), '-', ''), '/', ''), ',', '')"
    }
}

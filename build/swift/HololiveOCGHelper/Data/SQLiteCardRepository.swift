import Foundation
import SQLite3

final class SQLiteCardRepository: CardRepository {
    private let databaseProvider: DatabaseProvider

    init(databaseProvider: DatabaseProvider) {
        self.databaseProvider = databaseProvider
    }

    func searchCards(keyword: String, limit: Int = 40) throws -> [CardSummary] {
        let query = keyword.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return [] }
        let like = "%\(query)%"

        let conn = try databaseProvider.openConnection()
        defer { sqlite3_close(conn) }

        let sql = """
        SELECT DISTINCT p.print_id, p.card_number, COALESCE(p.name_ja, '') AS name_ja
        FROM prints p
        LEFT JOIN print_tags pt ON pt.print_id = p.print_id
        LEFT JOIN tags t ON t.tag = pt.tag
        WHERE UPPER(p.card_number) LIKE UPPER(?)
           OR COALESCE(p.name_ja, '') LIKE ?
           OR (t.tag IS NOT NULL AND (t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?))
        ORDER BY p.card_number
        LIMIT ?
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(conn, sql, -1, &statement, nil) == SQLITE_OK else {
            throw SQLiteError.prepare(String(cString: sqlite3_errmsg(conn)))
        }
        defer { sqlite3_finalize(statement) }

        bindText(like, to: statement, at: 1)
        bindText(like, to: statement, at: 2)
        bindText(like, to: statement, at: 3)
        bindText(like, to: statement, at: 4)
        sqlite3_bind_int(statement, 5, Int32(limit))

        var items: [CardSummary] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let printID = Int(sqlite3_column_int(statement, 0))
            let cardNumber = stringColumn(statement, index: 1)
            let nameJA = stringColumn(statement, index: 2)
            items.append(.init(id: printID, cardNumber: cardNumber, nameJA: nameJA))
        }

        return items
    }

    func loadDetail(printID: Int) throws -> CardDetail? {
        let conn = try databaseProvider.openConnection()
        defer { sqlite3_close(conn) }

        let sql = """
        SELECT p.print_id,
               p.card_number,
               COALESCE(p.name_ja, '') AS name_ja,
               COALESCE(ko.name, '') AS name_ko,
               COALESCE(ja.raw_text, '') AS raw_text,
               COALESCE(ko.effect_text, '') AS ko_text,
               COALESCE(p.image_url, '') AS image_url
        FROM prints p
        LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        WHERE p.print_id = ?
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(conn, sql, -1, &statement, nil) == SQLITE_OK else {
            throw SQLiteError.prepare(String(cString: sqlite3_errmsg(conn)))
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_int(statement, 1, Int32(printID))
        guard sqlite3_step(statement) == SQLITE_ROW else { return nil }

        return CardDetail(
            printID: Int(sqlite3_column_int(statement, 0)),
            cardNumber: stringColumn(statement, index: 1),
            nameJA: stringColumn(statement, index: 2),
            nameKO: stringColumn(statement, index: 3),
            rawTextJA: stringColumn(statement, index: 4),
            effectTextKO: stringColumn(statement, index: 5),
            imageURL: stringColumn(statement, index: 6)
        )
    }

    private func bindText(_ value: String, to statement: OpaquePointer?, at index: Int32) {
        value.withCString { pointer in
            sqlite3_bind_text(statement, index, pointer, -1, SQLITE_TRANSIENT)
        }
    }

    private func stringColumn(_ statement: OpaquePointer?, index: Int32) -> String {
        guard let cString = sqlite3_column_text(statement, index) else { return "" }
        return String(cString: cString)
    }
}

enum SQLiteError: Error {
    case prepare(String)
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

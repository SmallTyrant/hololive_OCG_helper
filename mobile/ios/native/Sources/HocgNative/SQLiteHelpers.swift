import Foundation
import SQLite3

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

enum SQLiteError: Error {
    case open(String)
    case prepare(String)
    case step(String)
    case execute(String)
}

enum SQLiteBindValue {
    case text(String)
    case int64(Int64)
}

func withSQLite<T>(path: String, readOnly: Bool, _ body: (OpaquePointer) throws -> T) throws -> T {
    var db: OpaquePointer?
    let flags = readOnly ? SQLITE_OPEN_READONLY : (SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE)
    if sqlite3_open_v2(path, &db, flags, nil) != SQLITE_OK {
        defer { sqlite3_close(db) }
        throw SQLiteError.open(sqliteErrorMessage(db))
    }
    guard let opened = db else {
        throw SQLiteError.open("sqlite handle is nil")
    }
    defer { sqlite3_close(opened) }
    return try body(opened)
}

func sqlitePrepare(db: OpaquePointer, sql: String) throws -> OpaquePointer {
    var stmt: OpaquePointer?
    if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) != SQLITE_OK {
        throw SQLiteError.prepare(sqliteErrorMessage(db))
    }
    guard let prepared = stmt else {
        throw SQLiteError.prepare("statement is nil")
    }
    return prepared
}

func sqliteBind(_ values: [SQLiteBindValue], to stmt: OpaquePointer) throws {
    for (idx, value) in values.enumerated() {
        let position = Int32(idx + 1)
        let rc: Int32
        switch value {
        case .text(let text):
            rc = sqlite3_bind_text(stmt, position, text, -1, SQLITE_TRANSIENT)
        case .int64(let intValue):
            rc = sqlite3_bind_int64(stmt, position, intValue)
        }
        if rc != SQLITE_OK {
            throw SQLiteError.execute("failed to bind value at \(position)")
        }
    }
}

func sqliteColumnString(_ stmt: OpaquePointer, index: Int32) -> String {
    guard let ptr = sqlite3_column_text(stmt, index) else {
        return ""
    }
    return String(cString: ptr)
}

func sqliteColumnOptionalString(_ stmt: OpaquePointer, index: Int32) -> String? {
    guard sqlite3_column_type(stmt, index) != SQLITE_NULL else {
        return nil
    }
    return sqliteColumnString(stmt, index: index)
}

func sqliteColumnInt64(_ stmt: OpaquePointer, index: Int32) -> Int64 {
    return sqlite3_column_int64(stmt, index)
}

func sqliteErrorMessage(_ db: OpaquePointer?) -> String {
    if let db {
        return String(cString: sqlite3_errmsg(db))
    }
    return "unknown sqlite error"
}

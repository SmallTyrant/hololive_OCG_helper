import Foundation
import SQLite3

final class DatabaseProvider {
    enum DatabaseError: Error {
        case dbNotBundled
        case openFailed(String)
    }

    private let fileManager = FileManager.default
    private let dbFileName = "hololive_ocg.sqlite"

    func openConnection() throws -> OpaquePointer {
        let dbURL = try prepareDatabase()
        var connection: OpaquePointer?
        if sqlite3_open_v2(dbURL.path, &connection, SQLITE_OPEN_READONLY, nil) != SQLITE_OK {
            let message = String(cString: sqlite3_errmsg(connection))
            sqlite3_close(connection)
            throw DatabaseError.openFailed(message)
        }
        guard let connection else {
            throw DatabaseError.openFailed("connection is nil")
        }
        return connection
    }

    private func prepareDatabase() throws -> URL {
        let appSupport = try fileManager.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let directory = appSupport.appendingPathComponent("HololiveOCGHelper", isDirectory: true)
        if !fileManager.fileExists(atPath: directory.path) {
            try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        }

        let target = directory.appendingPathComponent(dbFileName)
        if fileManager.fileExists(atPath: target.path) {
            return target
        }

        guard let bundleURL = Bundle.main.url(forResource: "hololive_ocg", withExtension: "sqlite") else {
            throw DatabaseError.dbNotBundled
        }
        try fileManager.copyItem(at: bundleURL, to: target)
        return target
    }
}

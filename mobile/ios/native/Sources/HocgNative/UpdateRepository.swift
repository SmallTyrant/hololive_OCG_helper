import Foundation
import SQLite3

private let githubRepo = "SmallTyrant/hololive_OCG_helper"
private let latestReleaseAPI = URL(string: "https://api.github.com/repos/\(githubRepo)/releases/latest")!
private let latestDbDirectURL = URL(string: "https://github.com/\(githubRepo)/releases/latest/download/hololive_ocg.sqlite")!

struct ReleaseDbInfo {
    let tag: String
    let assetName: String
    let assetURL: URL
    let assetUpdatedAt: String
    let publishedAt: String
    let createdAt: String
}

final class UpdateRepository {

    func latestReleaseDbInfo() async throws -> ReleaseDbInfo {
        var request = URLRequest(url: latestReleaseAPI)
        request.timeoutInterval = 20
        request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }

        let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let payload else {
            throw URLError(.cannotParseResponse)
        }
        return releaseInfo(from: payload)
    }

    func fetchRemoteDbDate() async -> String? {
        guard let info = try? await latestReleaseDbInfo() else {
            return nil
        }
        return formatIsoDateOrNil(
            !info.assetUpdatedAt.isEmpty
                ? info.assetUpdatedAt
                : (!info.publishedAt.isEmpty ? info.publishedAt : info.createdAt)
        )
    }

    func downloadLatestDb(to targetDBURL: URL) async throws -> ReleaseDbInfo {
        let releaseInfo: ReleaseDbInfo
        do {
            releaseInfo = try await latestReleaseDbInfo()
        } catch {
            releaseInfo = ReleaseDbInfo(
                tag: "latest",
                assetName: "hololive_ocg.sqlite",
                assetURL: latestDbDirectURL,
                assetUpdatedAt: "",
                publishedAt: "",
                createdAt: "",
            )
        }

        var request = URLRequest(url: releaseInfo.assetURL)
        request.timeoutInterval = 120
        request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
        request.setValue("application/octet-stream", forHTTPHeaderField: "Accept")

        let (tempDownloadedURL, response) = try await URLSession.shared.download(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }

        let fm = FileManager.default
        let tempTarget = targetDBURL.appendingPathExtension("download")
        if fm.fileExists(atPath: tempTarget.path) {
            try? fm.removeItem(at: tempTarget)
        }
        if fm.fileExists(atPath: targetDBURL.deletingLastPathComponent().path) == false {
            try fm.createDirectory(at: targetDBURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        }

        try fm.copyItem(at: tempDownloadedURL, to: tempTarget)

        do {
            try validateSQLite(fileURL: tempTarget)
            if fm.fileExists(atPath: targetDBURL.path) {
                try fm.removeItem(at: targetDBURL)
            }
            try fm.moveItem(at: tempTarget, to: targetDBURL)
            try writeReleaseMeta(dbURL: targetDBURL, info: releaseInfo)
            return releaseInfo
        } catch {
            try? fm.removeItem(at: tempTarget)
            throw error
        }
    }

    private func releaseInfo(from payload: [String: Any]) -> ReleaseDbInfo {
        let tag = payload["tag_name"] as? String ?? "latest"
        let publishedAt = payload["published_at"] as? String ?? ""
        let createdAt = payload["created_at"] as? String ?? ""

        let assets = payload["assets"] as? [[String: Any]] ?? []
        let asset = pickAsset(from: assets)

        let assetName = asset.name
        let assetURL = asset.url

        var assetUpdatedAt = ""
        for item in assets {
            let name = item["name"] as? String ?? ""
            let urlString = item["browser_download_url"] as? String ?? ""
            if (name == assetName || urlString == assetURL.absoluteString),
               let updated = item["updated_at"] as? String {
                assetUpdatedAt = updated
                break
            }
        }

        return ReleaseDbInfo(
            tag: tag,
            assetName: assetName,
            assetURL: assetURL,
            assetUpdatedAt: assetUpdatedAt,
            publishedAt: publishedAt,
            createdAt: createdAt,
        )
    }

    private func pickAsset(from assets: [[String: Any]]) -> (name: String, url: URL) {
        for item in assets {
            let name = item["name"] as? String ?? ""
            let urlString = item["browser_download_url"] as? String ?? ""
            if name == "hololive_ocg.sqlite", let url = URL(string: urlString) {
                return (name, url)
            }
        }

        for item in assets {
            let name = item["name"] as? String ?? ""
            let urlString = item["browser_download_url"] as? String ?? ""
            if [".sqlite", ".sqlite3", ".db"].contains(where: { name.hasSuffix($0) }),
               let url = URL(string: urlString) {
                return (name, url)
            }
        }

        return ("hololive_ocg.sqlite", latestDbDirectURL)
    }

    private func validateSQLite(fileURL: URL) throws {
        let data = try Data(contentsOf: fileURL, options: .mappedIfSafe)
        guard data.count > 16 else {
            throw URLError(.cannotDecodeContentData)
        }
        let header = Data("SQLite format 3\u{0}".utf8)
        guard data.prefix(16) == header else {
            throw URLError(.cannotDecodeContentData)
        }

        let hasPrints = try withSQLite(path: fileURL.path, readOnly: true) { db in
            let stmt = try sqlitePrepare(
                db: db,
                sql: "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prints'",
            )
            defer { sqlite3_finalize(stmt) }
            return sqlite3_step(stmt) == SQLITE_ROW
        }

        if !hasPrints {
            throw URLError(.cannotDecodeContentData)
        }
    }

    private func writeReleaseMeta(dbURL: URL, info: ReleaseDbInfo) throws {
        try withSQLite(path: dbURL.path, readOnly: false) { db in
            if sqlite3_exec(
                db,
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
                nil,
                nil,
                nil
            ) != SQLITE_OK {
                throw SQLiteError.execute(sqliteErrorMessage(db))
            }

            let values: [String: String] = [
                "release_tag": info.tag,
                "release_asset_name": info.assetName,
                "release_asset_updated_at": info.assetUpdatedAt,
                "release_published_at": info.publishedAt,
                "release_created_at": info.createdAt,
            ]

            sqlite3_exec(db, "BEGIN TRANSACTION", nil, nil, nil)
            do {
                for (key, value) in values where !value.isEmpty {
                    let stmt = try sqlitePrepare(
                        db: db,
                        sql: """
                        INSERT INTO meta(key, value)
                        VALUES(?, ?)
                        ON CONFLICT(key) DO UPDATE SET value = excluded.value
                        """,
                    )
                    defer { sqlite3_finalize(stmt) }
                    try sqliteBind([.text(key), .text(value)], to: stmt)
                    if sqlite3_step(stmt) != SQLITE_DONE {
                        throw SQLiteError.step(sqliteErrorMessage(db))
                    }
                }
                sqlite3_exec(db, "COMMIT", nil, nil, nil)
            } catch {
                sqlite3_exec(db, "ROLLBACK", nil, nil, nil)
                throw error
            }
        }
    }
}

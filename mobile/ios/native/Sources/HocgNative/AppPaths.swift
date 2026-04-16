import Foundation
import CryptoKit

private let appName = "hOCG_H"
private let dbFileName = "hololive_ocg.sqlite"
private let imageBaseURL = URL(string: "https://hololive-official-cardgame.com")!

final class AppPaths {
    private let fileManager: FileManager

    let rootURL: URL
    let dbURL: URL
    let imagesURL: URL
    let decksURL: URL

    init(fileManager: FileManager = .default) {
        self.fileManager = fileManager

        let base = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first!
        let root = base.appendingPathComponent(appName, isDirectory: true)
        let images = root.appendingPathComponent("images", isDirectory: true)
        let decks = root.appendingPathComponent("decks", isDirectory: true)

        try? fileManager.createDirectory(at: root, withIntermediateDirectories: true)
        try? fileManager.createDirectory(at: images, withIntermediateDirectories: true)
        try? fileManager.createDirectory(at: decks, withIntermediateDirectories: true)

        rootURL = root
        dbURL = root.appendingPathComponent(dbFileName)
        imagesURL = images
        decksURL = decks
    }

    var deckLibraryURL: URL {
        decksURL.appendingPathComponent("deck_library.json")
    }

    func localImageURL(cardNumber: String, variant: String = "", imageURL: String = "") -> URL {
        let safe = sanitizeCardNumber(cardNumber)
        let suffix = variant.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "" : "__\(sanitizeCardNumber(variant))"
        let resolved = resolveImageURL(imageURL)?.absoluteString ?? ""
        let urlSuffix = resolved.isEmpty ? "" : "__\(stableURLHash(resolved))"
        return imagesURL.appendingPathComponent("\(safe)\(suffix)\(urlSuffix).png")
    }

    func legacyLocalImageURL(cardNumber: String, variant: String = "") -> URL {
        let safe = sanitizeCardNumber(cardNumber)
        let suffix = variant.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "" : "__\(sanitizeCardNumber(variant))"
        return imagesURL.appendingPathComponent("\(safe)\(suffix).png")
    }

    func resolveImageURL(_ raw: String) -> URL? {
        let input = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !input.isEmpty else {
            return nil
        }
        if input.hasPrefix("http://") || input.hasPrefix("https://") {
            return URL(string: input)
        }
        if input.hasPrefix("/") {
            return URL(string: imageBaseURL.absoluteString + input)
        }
        return imageBaseURL.appendingPathComponent(input)
    }

    @discardableResult
    func copyBundledDbIfMissing() -> Bool {
        copyBundledDb(forceReplace: false)
    }

    @discardableResult
    func restoreBundledDb() -> Bool {
        copyBundledDb(forceReplace: true)
    }

    @discardableResult
    private func copyBundledDb(forceReplace: Bool) -> Bool {
        if fileManager.fileExists(atPath: dbURL.path),
           let attrs = try? fileManager.attributesOfItem(atPath: dbURL.path),
           let fileSize = attrs[.size] as? NSNumber,
           fileSize.intValue > 0,
           !forceReplace {
            return false
        }

        let bundled = Bundle.main.url(forResource: "hololive_ocg", withExtension: "sqlite")
            ?? Bundle.main.url(forResource: "hololive_ocg", withExtension: "sqlite", subdirectory: "Data")
        guard let bundled else {
            return false
        }

        let temp = dbURL.appendingPathExtension("tmp")
        do {
            if fileManager.fileExists(atPath: temp.path) {
                try fileManager.removeItem(at: temp)
            }
            try fileManager.copyItem(at: bundled, to: temp)
            if fileManager.fileExists(atPath: dbURL.path) {
                try fileManager.removeItem(at: dbURL)
            }
            try fileManager.moveItem(at: temp, to: dbURL)
            return true
        } catch {
            try? fileManager.removeItem(at: temp)
            return false
        }
    }

    private func sanitizeCardNumber(_ cardNumber: String) -> String {
        let trimmed = cardNumber.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return "unknown"
        }
        let replaced = trimmed.replacingOccurrences(of: "/", with: "_")
        let safe = replaced.replacingOccurrences(
            of: "[^A-Za-z0-9._-]+",
            with: "_",
            options: .regularExpression,
        )
        return safe.isEmpty ? "unknown" : safe
    }

    private func stableURLHash(_ text: String) -> String {
        let digest = SHA256.hash(data: Data(text.utf8))
        return digest.compactMap { String(format: "%02x", $0) }.joined().prefix(12).description
    }
}

final class DeckStorage {
    private let paths: AppPaths
    private let fileManager: FileManager
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(paths: AppPaths = AppPaths(), fileManager: FileManager = .default) {
        self.paths = paths
        self.fileManager = fileManager
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()

        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        decoder.dateDecodingStrategy = .iso8601
        encoder.dateEncodingStrategy = .iso8601
    }

    func loadLibrary() -> DeckLibraryRecord {
        let url = paths.deckLibraryURL
        guard fileManager.fileExists(atPath: url.path) else {
            return DeckLibraryRecord()
        }
        do {
            let data = try Data(contentsOf: url)
            return try decoder.decode(DeckLibraryRecord.self, from: data)
        } catch {
            let backup = url.appendingPathExtension("bak")
            guard fileManager.fileExists(atPath: backup.path),
                  let data = try? Data(contentsOf: backup),
                  let decoded = try? decoder.decode(DeckLibraryRecord.self, from: data) else {
                return DeckLibraryRecord()
            }
            return decoded
        }
    }

    @discardableResult
    func saveLibrary(_ library: DeckLibraryRecord) -> Bool {
        let url = paths.deckLibraryURL
        let tmp = url.appendingPathExtension("tmp")
        let backup = url.appendingPathExtension("bak")
        do {
            let data = try encoder.encode(library)
            try data.write(to: tmp, options: .atomic)
            if fileManager.fileExists(atPath: url.path) {
                if fileManager.fileExists(atPath: backup.path) {
                    try? fileManager.removeItem(at: backup)
                }
                try? fileManager.copyItem(at: url, to: backup)
            }
            if fileManager.fileExists(atPath: url.path) {
                try fileManager.removeItem(at: url)
            }
            try fileManager.moveItem(at: tmp, to: url)
            return true
        } catch {
            try? fileManager.removeItem(at: tmp)
            return false
        }
    }

    func exportData(for decks: [SavedDeckRecord]) -> Data? {
        try? encoder.encode(DeckLibraryRecord(decks: decks))
    }

    func importData(_ data: Data) -> [SavedDeckRecord] {
        guard let decoded = try? decoder.decode(DeckLibraryRecord.self, from: data) else {
            return []
        }
        return decoded.decks
    }
}

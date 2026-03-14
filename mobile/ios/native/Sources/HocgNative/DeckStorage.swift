import Foundation

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
            return DeckLibraryRecord()
        }
    }

    @discardableResult
    func saveLibrary(_ library: DeckLibraryRecord) -> Bool {
        let url = paths.deckLibraryURL
        let tmp = url.appendingPathExtension("tmp")
        do {
            let data = try encoder.encode(library)
            try data.write(to: tmp, options: .atomic)
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

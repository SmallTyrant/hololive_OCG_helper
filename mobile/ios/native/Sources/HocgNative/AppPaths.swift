import Foundation

private let appName = "hOCG_H"
private let dbFileName = "hololive_ocg.sqlite"
private let imageBaseURL = URL(string: "https://hololive-official-cardgame.com")!

final class AppPaths {
    private let fileManager: FileManager

    let rootURL: URL
    let dbURL: URL
    let imagesURL: URL

    init(fileManager: FileManager = .default) {
        self.fileManager = fileManager

        let base = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first!
        let root = base.appendingPathComponent(appName, isDirectory: true)
        let images = root.appendingPathComponent("images", isDirectory: true)

        try? fileManager.createDirectory(at: root, withIntermediateDirectories: true)
        try? fileManager.createDirectory(at: images, withIntermediateDirectories: true)

        rootURL = root
        dbURL = root.appendingPathComponent(dbFileName)
        imagesURL = images
    }

    func localImageURL(cardNumber: String) -> URL {
        let safe = sanitizeCardNumber(cardNumber)
        return imagesURL.appendingPathComponent("\(safe).png")
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
}

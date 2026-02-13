import Foundation

actor ImageDownloadTracker {
    private var running: Set<String> = []

    func start(_ key: String) -> Bool {
        if running.contains(key) {
            return false
        }
        running.insert(key)
        return true
    }

    func finish(_ key: String) {
        running.remove(key)
    }
}

final class ImageRepository {
    private let paths: AppPaths
    private let tracker = ImageDownloadTracker()

    init(paths: AppPaths) {
        self.paths = paths
    }

    func downloadIfNeeded(cardNumber: String, imageURL: String) async -> CardImageState {
        let trimmedCard = cardNumber.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedCard.isEmpty else {
            return .placeholder("이미지 없음")
        }

        let localURL = paths.localImageURL(cardNumber: trimmedCard)
        if FileManager.default.fileExists(atPath: localURL.path) {
            return .local(localURL)
        }

        guard let resolved = paths.resolveImageURL(imageURL) else {
            return .placeholder("이미지 URL 없음")
        }

        let shouldDownload = await tracker.start(trimmedCard)
        if !shouldDownload {
            return .remote(resolved)
        }

        defer {
            Task {
                await tracker.finish(trimmedCard)
            }
        }

        do {
            var request = URLRequest(url: resolved)
            request.timeoutInterval = 30
            request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
            let (tempFile, response) = try await URLSession.shared.download(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                return .error("이미지 로딩 실패")
            }

            let destination = localURL
            let tempDestination = destination.appendingPathExtension("tmp")
            let fm = FileManager.default
            if fm.fileExists(atPath: tempDestination.path) {
                try? fm.removeItem(at: tempDestination)
            }
            try fm.moveItem(at: tempFile, to: tempDestination)
            if fm.fileExists(atPath: destination.path) {
                try fm.removeItem(at: destination)
            }
            try fm.moveItem(at: tempDestination, to: destination)
            return .local(destination)
        } catch {
            return .error("이미지 로딩 실패")
        }
    }
}

import Foundation
import Network

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
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "hocg.network.monitor")
    private let offlineImageMessage = "네트워크 연결이 필요합니다.\n또는 캐시된 이미지가 없습니다."
    private let session: URLSession

    init(paths: AppPaths) {
        self.paths = paths
        let config = URLSessionConfiguration.ephemeral
        config.waitsForConnectivity = false
        config.timeoutIntervalForRequest = 20
        config.timeoutIntervalForResource = 25
        self.session = URLSession(configuration: config)
        monitor.start(queue: monitorQueue)
    }

    deinit {
        monitor.cancel()
    }

    private func shouldIgnoreLegacyCache(cardNumber: String) -> Bool {
        let normalized = cardNumber.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        return normalized.hasPrefix("HY")
    }

    private func cachedLocalURL(cardNumber: String, imageURL: String, variant: String) -> URL? {
        let current = paths.localImageURL(cardNumber: cardNumber, variant: variant, imageURL: imageURL)
        if FileManager.default.fileExists(atPath: current.path) {
            return current
        }
        if !shouldIgnoreLegacyCache(cardNumber: cardNumber) {
            let legacy = paths.legacyLocalImageURL(cardNumber: cardNumber, variant: variant)
            if FileManager.default.fileExists(atPath: legacy.path) {
                return legacy
            }
        }
        return nil
    }

    func downloadIfNeeded(cardNumber: String, imageURL: String, variant: String = "") async -> CardImageState {
        let trimmedCard = cardNumber.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedCard.isEmpty else {
            return .placeholder("이미지 없음")
        }

        if let localURL = cachedLocalURL(cardNumber: trimmedCard, imageURL: imageURL, variant: variant) {
            return .local(localURL)
        }

        guard let resolved = paths.resolveImageURL(imageURL) else {
            return .placeholder("이미지 URL 없음")
        }
        let localURL = paths.localImageURL(cardNumber: trimmedCard, variant: variant, imageURL: resolved.absoluteString)

        if monitor.currentPath.status == .unsatisfied {
            return .error(offlineImageMessage)
        }

        let shouldDownload = await tracker.start("\(trimmedCard)|\(variant)|\(resolved.absoluteString)")
        if !shouldDownload {
            return .remote(resolved)
        }

        defer {
            Task {
                await tracker.finish("\(trimmedCard)|\(variant)|\(resolved.absoluteString)")
            }
        }

        do {
            var request = URLRequest(url: resolved)
            request.timeoutInterval = 20
            request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
            let (tempFile, response) = try await session.download(for: request)
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
            if let urlError = error as? URLError {
                switch urlError.code {
                case .notConnectedToInternet,
                        .networkConnectionLost,
                        .cannotConnectToHost,
                        .cannotFindHost,
                        .dnsLookupFailed,
                        .timedOut:
                    return .error(offlineImageMessage)
                default:
                    break
                }
            }
            if monitor.currentPath.status == .unsatisfied {
                return .error(offlineImageMessage)
            }
            return .error("이미지 로딩 실패")
        }
    }
}

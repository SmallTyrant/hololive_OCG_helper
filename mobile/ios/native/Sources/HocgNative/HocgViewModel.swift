import Foundation

private let dbMissingToast = "DB파일이 존재하지 않습니다. 메뉴에서 DB 수동갱신을 실행해주세요"
private let dbUpdatingToast = "갱신중..."
private let dbUpdatedToast = "갱신완료"
private let dbRestoredToast = "번들 DB 복원완료"
private let bulkImageMaxConcurrency = 10
private let bulkImageRetryCount = 1
private let detailPrefetchLimit = 20
private let detailPrefetchMaxConcurrency = 4

@MainActor
final class HocgViewModel: ObservableObject {
    private struct BulkImageOutcome {
        let downloaded: Int
        let cached: Int
        let failed: Int
        let skipped: Int
    }

    @Published private(set) var state: HocgUiState
    @Published var toastMessage: String?

    private let paths: AppPaths
    private let dbRepository: DatabaseRepository
    private let imageRepository: ImageRepository
    private let updateRepository: UpdateRepository

    private var searchTask: Task<Void, Never>?
    private var detailTask: Task<Void, Never>?
    private var prefetchTask: Task<Void, Never>?
    private var remotePromptMarker: String?

    init(
        paths: AppPaths = AppPaths(),
        updateRepository: UpdateRepository = UpdateRepository(),
    ) {
        self.paths = paths
        self.dbRepository = DatabaseRepository(paths: paths)
        self.imageRepository = ImageRepository(paths: paths)
        self.updateRepository = updateRepository
        self.state = HocgUiState(dbPath: paths.dbURL.path)

        Task {
            await bootstrap()
        }
    }

    func onSearchQueryChanged(_ query: String) {
        state.searchQuery = query
        refreshList()
    }

    func onSelectPrint(_ printId: Int64) {
        if state.selectedPrintId == printId, state.detailLoading {
            return
        }
        showDetail(printId)
    }

    func onToggleImagePanel() {
        state.imageCollapsed.toggle()
    }

    func onSelectIllustration(rarity: String, imageURL: String) {
        guard let printId = state.selectedPrintId else { return }
        let cardNumber = state.selectedCardNumber.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cardNumber.isEmpty else { return }

        detailTask?.cancel()
        detailTask = Task {
            state.selectedRarity = rarity
            state.imageState = .loading
            let loaded = await imageRepository.downloadIfNeeded(cardNumber: cardNumber, imageURL: imageURL, variant: rarity)
            guard !Task.isCancelled, state.selectedPrintId == printId, state.selectedRarity == rarity else {
                return
            }
            state.imageState = loaded
        }
    }

    func onUpdateDialogDismiss() {
        state.updateDialog = nil
    }

    func onUpdateDialogConfirm() {
        state.updateDialog = nil
        onManualUpdate()
    }

    func onManualUpdate() {
        guard !state.updateRunning else {
            return
        }

        Task {
            guard !state.dbPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                state.updateStatus = "DB 경로가 비어 있습니다."
                state.updateStatusError = true
                pushToast("DB 경로가 비어 있습니다.")
                return
            }

            state.updateRunning = true
            state.updateStatus = "DB 갱신 중..."
            state.updateStatusError = false
            pushToast(dbUpdatingToast)

            do {
                _ = try await updateRepository.downloadLatestDb(to: paths.dbURL)
                state.updateStatus = "DB 갱신 완료"
                state.updateStatusError = false
                state.persistentMessage = nil
                pushToast(dbUpdatedToast)
                refreshList()
            } catch {
                var message = "DB 갱신 실패: \(error.localizedDescription)"
                
                if let urlError = error as? URLError {
                    switch urlError.code {
                    case .badServerResponse:
                        message = "DB 갱신 실패: 서버에서 DB 파일을 찾을 수 없습니다. 네트워크 연결을 확인하거나 나중에 다시 시도해주세요."
                    case .notConnectedToInternet:
                        message = "DB 갱신 실패: 인터넷에 연결되어 있지 않습니다."
                    case .timedOut:
                        message = "DB 갱신 실패: 요청 시간이 초과되었습니다."
                    case .cannotFindHost:
                        message = "DB 갱신 실패: 서버를 찾을 수 없습니다. 네트워크 연결을 확인해주세요."
                    case .cannotConnectToHost:
                        message = "DB 갱신 실패: 서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요."
                    case .networkConnectionLost:
                        message = "DB 갱신 실패: 네트워크 연결이 끊어졌습니다."
                    default:
                        break
                    }
                }
                
                state.updateStatus = message
                state.updateStatusError = true
                pushToast(message)

                let recovered = await runIO {
                    let missingBeforeRecover = self.dbRepository.needsDbUpdate()
                    guard missingBeforeRecover else {
                        return false
                    }
                    return self.paths.restoreBundledDb() && !self.dbRepository.needsDbUpdate()
                }
                if recovered {
                    state.updateStatus = "DB 복원 완료"
                    state.updateStatusError = false
                    state.persistentMessage = nil
                    pushToast(dbRestoredToast)
                    refreshList()
                } else {
                    let stillMissing = await runIO {
                        self.dbRepository.needsDbUpdate()
                    }
                    if stillMissing {
                        applyMissingDbState()
                    }
                }
            }

            state.updateRunning = false
        }
    }

    func onBulkImageDownload() {
        guard !state.updateRunning else {
            return
        }

        Task {
            guard !state.dbPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                state.updateStatus = "DB 경로가 비어 있습니다."
                state.updateStatusError = true
                pushToast("DB 경로가 비어 있습니다.")
                return
            }

            state.updateRunning = true
            state.updateStatus = "이미지 일괄 다운로드 준비 중..."
            state.updateStatusError = false
            pushToast("이미지 일괄 다운로드 시작")
            defer {
                state.updateRunning = false
            }

            let targets = await runIO {
                self.dbRepository.listImageTargets()
            }
            if targets.isEmpty {
                let message = "다운로드할 이미지가 없습니다."
                state.updateStatus = message
                state.updateStatusError = false
                pushToast(message)
                return
            }

            var downloaded = 0
            var alreadyCached = 0
            var failed = 0
            var skipped = 0
            var completed = 0

            state.updateStatus = "이미지 다운로드 중... (0/\(targets.count))"
            await withTaskGroup(of: BulkImageOutcome.self) { group in
                let initial = min(bulkImageMaxConcurrency, targets.count)
                var nextIndex = 0
                for _ in 0..<initial {
                    let target = targets[nextIndex]
                    group.addTask {
                        await self.downloadBulkImageTarget(target)
                    }
                    nextIndex += 1
                }

                while let outcome = await group.next() {
                    completed += 1
                    downloaded += outcome.downloaded
                    alreadyCached += outcome.cached
                    failed += outcome.failed
                    skipped += outcome.skipped
                    state.updateStatus = "이미지 다운로드 중... (\(completed)/\(targets.count))"

                    if nextIndex < targets.count {
                        let target = targets[nextIndex]
                        group.addTask {
                            await self.downloadBulkImageTarget(target)
                        }
                        nextIndex += 1
                    }
                }
            }

            let message = "이미지 다운로드 완료: 신규 \(downloaded) / 기존 \(alreadyCached) / 실패 \(failed) / 건너뜀 \(skipped)"
            state.updateStatus = message
            state.updateStatusError = failed > 0
            pushToast(message)

            if let selected = state.selectedPrintId {
                showDetail(selected)
            }
        }
    }

    private func bootstrap() async {
        _ = paths.copyBundledDbIfMissing()

        let missing = await runIO {
            self.dbRepository.needsDbUpdate()
        }

        if missing {
            // DB 파일이 없거나 스키마가 유효하지 않으면 자동으로 다운로드 시작.
            // 사용자가 수동으로 메뉴를 찾아야 하는 불편함 제거.
            pushToast("DB를 다운로드하는 중입니다...")
            onManualUpdate()
            // onManualUpdate() 내부에서 refreshList()를 호출하므로 여기서는 호출 불필요.
            return
        }

        refreshList()
        await checkRemoteUpdateOnce()
    }

    private func refreshList() {
        searchTask?.cancel()
        let query = state.searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)

        if query.isEmpty {
            prefetchTask?.cancel()
            state.results = []
            state.selectedPrintId = nil
            state.selectedCardNumber = ""
            state.selectedImageUrl = ""
            state.selectedRarity = ""
            state.selectedIllustrations = []
            state.detailKoText = ""
            state.detailJaText = ""
            state.detailLoading = false
            state.imageState = .placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다.")
            return
        }

        searchTask = Task {
            try? await Task.sleep(nanoseconds: 120_000_000)
            guard !Task.isCancelled else {
                return
            }

            let needsUpdate = await runIO {
                self.dbRepository.needsDbUpdate()
            }
            guard !Task.isCancelled else {
                return
            }
            if needsUpdate {
                prefetchTask?.cancel()
                applyMissingDbState()
                state.results = []
                state.selectedPrintId = nil
                state.selectedCardNumber = ""
                state.selectedImageUrl = ""
                state.selectedRarity = ""
                state.selectedIllustrations = []
                state.detailKoText = ""
                state.detailJaText = ""
                state.detailLoading = false
                state.imageState = .placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다.")
                return
            }

            let rows = await runIO {
                self.dbRepository.querySuggest(query)
            }
            guard !Task.isCancelled else {
                return
            }

            let selectedBefore = state.selectedPrintId
            state.results = rows
            state.persistentMessage = nil

            if let selectedBefore,
               rows.contains(where: { $0.printId == selectedBefore }) {
                showDetail(selectedBefore)
                prefetchCardDetails(rows: rows, excludingPrintId: selectedBefore)
                return
            }

            if let first = rows.first {
                showDetail(first.printId)
                prefetchCardDetails(rows: rows, excludingPrintId: first.printId)
            } else {
                prefetchTask?.cancel()
                state.selectedPrintId = nil
                state.selectedCardNumber = ""
                state.selectedImageUrl = ""
                state.selectedRarity = ""
                state.selectedIllustrations = []
                state.detailKoText = ""
                state.detailJaText = ""
                state.detailLoading = false
                state.imageState = .placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다.")
            }
        }
    }

    private func showDetail(_ printId: Int64) {
        detailTask?.cancel()
        detailTask = Task {
            state.selectedPrintId = printId
            state.selectedCardNumber = ""
            state.selectedImageUrl = ""
            state.selectedRarity = ""
            state.selectedIllustrations = []
            state.detailKoText = ""
            state.detailJaText = ""
            state.detailLoading = true
            let snapshot = await runIO {
                self.dbRepository.loadCardSnapshot(printId: printId)
            }

            guard !Task.isCancelled, state.selectedPrintId == printId else {
                return
            }

            guard let snapshot else {
                state.detailKoText = "[ERROR] 상세 로드 실패"
                state.detailJaText = ""
                state.detailLoading = false
                state.selectedCardNumber = ""
                state.selectedImageUrl = ""
                state.selectedRarity = ""
                state.selectedIllustrations = []
                state.imageState = .error("이미지 로딩 실패")
                return
            }

            state.detailKoText = snapshot.detail.koText
            state.detailJaText = snapshot.detail.jaText
            state.detailLoading = false

            let cardNumber = snapshot.brief.cardNumber.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !cardNumber.isEmpty else {
                state.imageState = .placeholder("이미지 없음")
                return
            }

            let defaultIllustration = snapshot.brief.illustrations.first
            let selectedRarity = defaultIllustration?.rarity ?? ""
            let selectedImageUrl = (defaultIllustration?.imageUrl.isEmpty == false ? defaultIllustration?.imageUrl : snapshot.brief.imageUrl) ?? snapshot.brief.imageUrl
            state.selectedCardNumber = cardNumber
            state.selectedImageUrl = selectedImageUrl
            state.selectedRarity = selectedRarity
            state.selectedIllustrations = snapshot.brief.illustrations

            state.imageState = .loading

            let loaded = await imageRepository.downloadIfNeeded(cardNumber: cardNumber, imageURL: selectedImageUrl, variant: selectedRarity)
            if state.selectedPrintId == printId {
                state.imageState = loaded
            }
        }
    }

    private func prefetchCardDetails(rows: [PrintRow], excludingPrintId: Int64?) {
        prefetchTask?.cancel()

        let targets = Array(
            rows
                .map(\.printId)
                .filter { id in
                    if let excludingPrintId {
                        return id != excludingPrintId
                    }
                    return true
                }
                .prefix(detailPrefetchLimit)
        )

        guard !targets.isEmpty else {
            return
        }

        prefetchTask = Task {
            var index = 0
            while index < targets.count {
                if Task.isCancelled {
                    return
                }

                let end = min(index + detailPrefetchMaxConcurrency, targets.count)
                let chunk = targets[index..<end]

                await withTaskGroup(of: Void.self) { group in
                    for printId in chunk {
                        group.addTask {
                            _ = await self.runIO {
                                self.dbRepository.loadCardSnapshot(printId: printId)
                            }
                        }
                    }
                }

                index = end
            }
        }
    }

    private func checkRemoteUpdateOnce() async {
        guard !state.dbPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        async let localDateTask: String? = runIO { self.dbRepository.localDbDate() }
        async let localDigestTask: String? = runIO { self.dbRepository.localDbDigest() }
        guard let remoteInfo = try? await updateRepository.latestReleaseDbInfo() else {
            return
        }
        let remoteDate = formatIsoDateOrNil(remoteInfo.effectiveDateSource)
        guard let remoteDate, !remoteDate.isEmpty else {
            return
        }
        let localDate = await localDateTask
        let localDigest = await localDigestTask
        let remoteDigest = remoteInfo.remoteDigestOrNil
        let remoteMarker = remoteInfo.updateMarker ?? remoteDate

        let needsPrompt: Bool = {
            if let remoteDigest, !remoteDigest.isEmpty {
                return remoteDigest != localDigest
            }
            return remoteDate != localDate
        }()
        guard needsPrompt else { return }
        guard remotePromptMarker != remoteMarker else { return }

        remotePromptMarker = remoteMarker
        state.updateDialog = UpdateDialogState(localDate: localDate, remoteDate: remoteDate, localDigest: localDigest, remoteDigest: remoteDigest)
    }

    private func applyMissingDbState() {
        state.persistentMessage = dbMissingToast
        pushToast(dbMissingToast)
    }

    func getManageIdJp(printId: Int64) -> Int? {
        dbRepository.getManageIdJp(printId: printId)
    }

    func searchDeckCards(_ query: String, limit: Int = 240) async -> [DeckCardCandidate] {
        await runIO {
            self.dbRepository.listDeckCards(query: query, limit: limit).map { row in
                DeckCardCandidate(
                    printId: row.printId,
                    cardNumber: row.cardNumber,
                    nameJa: row.nameJa,
                    nameKo: row.nameKo,
                    imageUrl: self.paths.resolveImageURL(row.imageUrl)?.absoluteString ?? row.imageUrl,
                    cardType: row.cardType,
                    color: row.color,
                    rarity: row.rarity,
                    koText: row.koText,
                    jaText: row.jaText,
                    illustrations: row.illustrations.map { ill in
                        IllustrationOption(
                            rarity: ill.rarity,
                            manageIdJp: ill.manageIdJp,
                            imageUrl: self.paths.resolveImageURL(ill.imageUrl)?.absoluteString ?? ill.imageUrl
                        )
                    }
                )
            }
        }
    }

    private func pushToast(_ message: String) {
        toastMessage = message
        Task {
            try? await Task.sleep(nanoseconds: 1_800_000_000)
            if self.toastMessage == message {
                self.toastMessage = nil
            }
        }
    }

    private func downloadBulkImageTarget(_ target: (cardNumber: String, imageURL: String)) async -> BulkImageOutcome {
        let localURL = paths.localImageURL(cardNumber: target.cardNumber, imageURL: target.imageURL)
        let existedBefore = FileManager.default.fileExists(atPath: localURL.path)

        var imageState = await imageRepository.downloadIfNeeded(
            cardNumber: target.cardNumber,
            imageURL: target.imageURL,
        )
        var retryCount = 0
        while retryCount < bulkImageRetryCount {
            guard case .error = imageState else {
                break
            }
            retryCount += 1
            imageState = await imageRepository.downloadIfNeeded(
                cardNumber: target.cardNumber,
                imageURL: target.imageURL,
            )
        }

        switch imageState {
        case .local:
            if existedBefore {
                return BulkImageOutcome(downloaded: 0, cached: 1, failed: 0, skipped: 0)
            }
            return BulkImageOutcome(downloaded: 1, cached: 0, failed: 0, skipped: 0)
        case .error:
            return BulkImageOutcome(downloaded: 0, cached: 0, failed: 1, skipped: 0)
        case .placeholder, .remote, .loading:
            return BulkImageOutcome(downloaded: 0, cached: 0, failed: 0, skipped: 1)
        }
    }

    private func runIO<T>(_ work: @escaping () -> T) async -> T {
        await withCheckedContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                continuation.resume(returning: work())
            }
        }
    }
}

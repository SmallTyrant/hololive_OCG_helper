import Foundation

private let dbMissingToast = "DB파일이 존재하지 않습니다. 메뉴에서 DB 수동갱신을 실행해주세요"
private let dbUpdatingToast = "갱신중..."
private let dbUpdatedToast = "갱신완료"
private let dbRestoredToast = "번들 DB 복원완료"

@MainActor
final class HocgViewModel: ObservableObject {
    @Published private(set) var state: HocgUiState
    @Published var toastMessage: String?

    private let paths: AppPaths
    private let dbRepository: DatabaseRepository
    private let imageRepository: ImageRepository
    private let updateRepository: UpdateRepository

    private var searchTask: Task<Void, Never>?
    private var detailTask: Task<Void, Never>?
    private var remotePromptShown = false

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
        showDetail(printId)
    }

    func onToggleImagePanel() {
        state.imageCollapsed.toggle()
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
                let message = "DB 갱신 실패: \(error.localizedDescription)"
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
            let fm = FileManager.default

            for (index, target) in targets.enumerated() {
                state.updateStatus = "이미지 다운로드 중... (\(index + 1)/\(targets.count))"

                let localURL = paths.localImageURL(cardNumber: target.cardNumber)
                let existedBefore = fm.fileExists(atPath: localURL.path)
                let imageState = await imageRepository.downloadIfNeeded(
                    cardNumber: target.cardNumber,
                    imageURL: target.imageURL,
                )
                switch imageState {
                case .local:
                    if existedBefore {
                        alreadyCached += 1
                    } else {
                        downloaded += 1
                    }
                case .error:
                    failed += 1
                case .placeholder, .remote, .loading:
                    skipped += 1
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
            applyMissingDbState()
        }

        refreshList()
        await checkRemoteUpdateOnce()
    }

    private func refreshList() {
        searchTask?.cancel()
        let query = state.searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)

        searchTask = Task {
            if query.isEmpty {
                state.results = []
                state.selectedPrintId = nil
                state.detailKoText = ""
                state.imageState = .placeholder("카드를 선택하세요")
                return
            }

            let needsUpdate = await runIO {
                self.dbRepository.needsDbUpdate()
            }
            if needsUpdate {
                applyMissingDbState()
                state.results = []
                state.selectedPrintId = nil
                state.detailKoText = ""
                state.imageState = .placeholder("카드를 선택하세요")
                return
            }

            let rows = await runIO {
                self.dbRepository.querySuggest(query)
            }

            state.results = rows
            state.persistentMessage = nil

            if let first = rows.first {
                showDetail(first.printId)
            } else {
                state.selectedPrintId = nil
                state.detailKoText = ""
                state.imageState = .placeholder("카드를 선택하세요")
            }
        }
    }

    private func showDetail(_ printId: Int64) {
        detailTask?.cancel()
        detailTask = Task {
            state.selectedPrintId = printId

            let brief = await runIO {
                self.dbRepository.getPrintBrief(printId: printId)
            }
            let detail = await runIO {
                self.dbRepository.loadCardDetail(printId: printId)
            }

            guard let brief else {
                state.detailKoText = "[ERROR] 상세 로드 실패"
                state.imageState = .error("이미지 로딩 실패")
                return
            }

            state.detailKoText = detail?.koText ?? ""

            let cardNumber = brief.cardNumber.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !cardNumber.isEmpty else {
                state.imageState = .placeholder("이미지 없음")
                return
            }

            state.imageState = .loading

            let loaded = await imageRepository.downloadIfNeeded(cardNumber: cardNumber, imageURL: brief.imageUrl)
            if state.selectedPrintId == printId {
                state.imageState = loaded
            }
        }
    }

    private func checkRemoteUpdateOnce() async {
        guard !remotePromptShown else {
            return
        }
        guard !state.dbPath.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        let localDate = await runIO {
            self.dbRepository.localDbDate()
        }
        let remoteDate = await updateRepository.fetchRemoteDbDate()

        guard let remoteDate, !remoteDate.isEmpty else {
            return
        }
        guard remoteDate != localDate else {
            return
        }

        remotePromptShown = true
        state.updateDialog = UpdateDialogState(localDate: localDate, remoteDate: remoteDate)
    }

    private func applyMissingDbState() {
        state.persistentMessage = dbMissingToast
        pushToast(dbMissingToast)
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

    private func runIO<T>(_ work: @escaping () -> T) async -> T {
        await withCheckedContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                continuation.resume(returning: work())
            }
        }
    }
}

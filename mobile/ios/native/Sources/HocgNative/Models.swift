import Foundation

enum SearchMode: String, CaseIterable {
    case partial
    case exact
}

struct PrintRow: Identifiable {
    let printId: Int64
    let cardNumber: String
    let nameJa: String
    let nameKo: String

    var id: Int64 { printId }
}

struct PrintBrief {
    let printId: Int64
    let cardNumber: String
    let nameJa: String
    let nameKo: String
    let imageUrl: String
}

struct CardDetail {
    let koText: String
    let jaText: String
}

struct CardSnapshot {
    let brief: PrintBrief
    let detail: CardDetail
}

/// 레어리티별 일러스트 정보 (card_illustrations 테이블)
struct IllustrationOption: Identifiable, Equatable {
    let rarity: String
    let manageIdJp: Int?
    let imageUrl: String   // 비어있으면 기본 imageUrl 사용

    var id: String { rarity }
}

struct DeckCardCandidate: Identifiable {
    let printId: Int64
    let cardNumber: String
    let nameJa: String
    let nameKo: String
    let imageUrl: String
    let cardType: String
    let color: String
    let rarity: String
    let koText: String
    let jaText: String
    /// 선택 가능한 레어리티 목록 (card_illustrations). 1개면 선택 UI 불필요.
    let illustrations: [IllustrationOption]

    var id: Int64 { printId }

    /// 레어리티 목록이 2개 이상일 때만 true
    var hasMultipleRarities: Bool { illustrations.count > 1 }
}

struct DeckEntryRecord: Codable {
    var printId: Int64
    var cardNumber: String
    var qty: Int
    /// 사용자가 선택한 레어리티. nil 이면 기본 레어리티 사용.
    var selectedRarity: String?
}

struct SavedDeckRecord: Codable, Identifiable {
    var id: UUID
    var title: String
    var entries: [DeckEntryRecord]
    var updatedAt: Date
}

struct DeckLibraryRecord: Codable {
    var version: Int
    var decks: [SavedDeckRecord]

    init(version: Int = 1, decks: [SavedDeckRecord] = []) {
        self.version = version
        self.decks = decks
    }
}

struct UpdateDialogState {
    let localDate: String?
    let remoteDate: String
}

enum CardImageState {
    case loading
    case local(URL)
    case remote(URL)
    case placeholder(String)
    case error(String)
}

struct HocgUiState {
    var dbPath: String = ""
    var searchQuery: String = ""
    var searchMode: SearchMode = .partial
    var results: [PrintRow] = []
    var selectedPrintId: Int64?
    var detailKoText: String = ""
    var detailJaText: String = ""
    var detailLoading: Bool = false
    var imageState: CardImageState = .placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다.")
    var imageCollapsed: Bool = false
    var updateRunning: Bool = false
    var updateStatus: String = ""
    var updateStatusError: Bool = false
    var persistentMessage: String?
    var updateDialog: UpdateDialogState?
}

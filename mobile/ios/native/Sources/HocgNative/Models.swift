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

    var id: Int64 { printId }
}

struct DeckEntryRecord: Codable {
    var printId: Int64
    var cardNumber: String
    var qty: Int
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

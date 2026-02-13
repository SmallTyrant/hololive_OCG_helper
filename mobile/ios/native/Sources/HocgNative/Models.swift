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
    var imageState: CardImageState = .placeholder("카드를 선택하세요")
    var imageCollapsed: Bool = false
    var updateRunning: Bool = false
    var updateStatus: String = ""
    var updateStatusError: Bool = false
    var persistentMessage: String?
    var updateDialog: UpdateDialogState?
}

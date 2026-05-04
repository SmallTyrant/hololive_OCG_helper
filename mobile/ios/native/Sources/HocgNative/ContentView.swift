import SwiftUI
import Foundation
import Photos
import UniformTypeIdentifiers

private let sectionLabels: [String] = [
    "서포트 / 아이템",
    "서포트 / 스태프",
    "서포트 / 이벤트",
    "서포트 / 툴",
    "서포트 / 마스코트",
    "서포트 / 팬",
    "SP 오시 스킬",
    "오시 스테이지 스킬",
    "오시 스킬",
    "콜라보 이펙트",
    "블룸 이펙트",
    "기프트",
    "태그",
    "카드 타입",
    "카드타입",
    "레어리티",
    "아츠",
    "엑스트라",
    "Bloom 레벨",
    "키워드",
    "속성",
    "레벨",
    "배턴 터치",
    "SP推しスキル",
    "推しステージスキル",
    "推しスキル",
    "カードタイプ",
    "タグ",
    "レアリティ",
    "能力テキスト",
    "色",
    "アーツ",
    "エクストラ",
    "Bloomレベル",
    "キーワード",
    "バトンタッチ",
    "LIFE",
    "HP",
]
private let detailPrefixPattern = #"^(?:(?:.+?)\s+)?(?:서포트|サポート)\s*[/／]\s*(?:아이템|스태프|이벤트|이벤타|툴|마스코트|팬|アイテム|スタッフ|イベント|ツール|マスコット|ファン)(?=$|\s|[/／:：(\[])"#
private let sectionLabelsSorted = sectionLabels.sorted { $0.count > $1.count }
private let japaneseCharPattern = "[\\u3040-\\u30ff\\u31f0-\\u31ff\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff々〆ヵヶ]"
private let koSectionMarkerRegex = try! NSRegularExpression(
    pattern: "서포트 / 아이템|서포트 / 스태프|서포트 / 이벤트|서포트 / 툴|서포트 / 마스코트|서포트 / 팬|SP 오시 스킬|오시 스테이지 스킬|오시 스킬|콜라보 이펙트|블룸 이펙트|기프트|엑스트라|아츠(?=\\s+(?![+\\-]\\d)\\S)|#"
)
private let jaSectionMarkerRegex = try! NSRegularExpression(
    pattern: "SP推しスキル|推しステージスキル|推しスキル|コラボエフェクト|ブルームエフェクト|ギフト|エクストラ|アーツ(?=\\s+(?![+\\-]\\d)\\S)|カードタイプ|タグ|レアリティ|能力テキスト|バトンタッチ|#"
)
private let tagTokenRegex = try! NSRegularExpression(pattern: "#[^\\s#]+")
private let koMetadataTokenSet: Set<String> = [
    "레벨",
    "속성",
    "hp",
    "life",
    "배턴",
    "터치",
    "배턴터치",
    "1st",
    "2nd",
    "debut",
    "buzz",
]
private let jaMetadataTokenSet: Set<String> = [
    "レベル",
    "hp",
    "life",
    "1st",
    "2nd",
    "debut",
    "buzz",
]
private let koDetailReplacements: [(String, String)] = [
    ("【콜라보 이펙트】", "콜라보 이펙트"),
    ("【블룸 이펙트】", "블룸 이펙트"),
    ("【기프트】", "기프트"),
]
private let jaDetailReplacements: [(String, String)] = [
    ("【SP推しスキル】", "SP推しスキル"),
    ("【推しスキル】", "推しスキル"),
    ("【コラボエフェクト】", "コラボエフェクト"),
    ("【ブルームエフェクト】", "ブルームエフェクト"),
    ("【ギフト】", "ギフト"),
    ("【エクストラ】", "エクストラ"),
    ("【アーツ】", "アーツ"),
    ("【カードタイプ】", "カードタイプ"),
    ("【タグ】", "タグ"),
    ("【レアリティ】", "レアリティ"),
    ("【能力テキスト】", "能力テキスト"),
    ("【バトンタッチ】", "バトンタッチ"),
    ("【色】", "色"),
]
private let koLineBreakRules: [(String, String)] = [
    ("\\s*SP 오시 스킬\\s*", "\nSP 오시 스킬\n"),
    ("\\s*오시 스테이지 스킬\\s*", "\n오시 스테이지 스킬\n"),
    ("\\s*(?<!SP )오시 스킬\\s*", "\n오시 스킬\n"),
    ("\\s*콜라보 이펙트\\s*", "\n콜라보 이펙트\n"),
    ("\\s*기프트\\s*", "\n기프트\n"),
    ("\\s*엑스트라\\s*", "\n엑스트라\n"),
    ("\\s*아츠(?=\\s+(?![+\\-]\\d)\\S)\\s*", "\n아츠\n"),
    ("\\s+#", "\n#"),
]
private let jaLineBreakRules: [(String, String)] = [
    ("\\s*SP推しスキル\\s*", "\nSP推しスキル\n"),
    ("\\s*推しステージスキル\\s*", "\n推しステージスキル\n"),
    ("\\s*(?<!SP)推しスキル\\s*", "\n推しスキル\n"),
    ("\\s*コラボエフェクト\\s*", "\nコラボエフェクト\n"),
    ("\\s*ブルームエフェクト\\s*", "\nブルームエフェクト\n"),
    ("\\s*ギフト\\s*", "\nギフト\n"),
    ("\\s*エクストラ\\s*", "\nエクストラ\n"),
    ("\\s*アーツ(?=\\s+(?![+\\-]\\d)\\S)\\s*", "\nアーツ\n"),
    ("\\s*カードタイプ\\s*", "\nカードタイプ\n"),
    ("\\s*タグ\\s*", "\nタグ\n"),
    ("\\s*レアリティ\\s*", "\nレアリティ\n"),
    ("\\s*能力テキスト\\s*", "\n能力テキスト\n"),
    ("\\s*バトンタッチ\\s*", "\nバトンタッチ\n"),
    ("(?:^|\\s)色(?=\\s+\\S)", "\n色\n"),
    ("\\s+#", "\n#"),
]
private let htmlTagPattern = "<[^>]+>"
private let widthArtifactPattern = "(?i)\\bwidth\\s*=\\s*\\d+%?>?"
private let detailPrefixRegex = try! NSRegularExpression(
    pattern: #"^(?:(?:.+?)\s+)?(?:서포트|サポート)\s*[/／]\s*(?:아이템|스태프|이벤트|이벤타|툴|마스코트|팬|アイテム|スタッフ|イベント|ツール|マスコット|ファン)(?=$|\s|[/／:：(\[])"#
)
private let jaTagObjectSplitRegex = try! NSRegularExpression(
    pattern: #"^(#[^\s#を]+(?:\s+[^\s#を]+)*)(を.+)$"#
)
private let scalarMetadataPattern = try! NSRegularExpression(
    pattern: #"^(hp\s*\d{2,3}|(1st|2nd)\s*\d{2,3})$"#,
    options: .caseInsensitive
)
private let digitTokenPattern = try! NSRegularExpression(pattern: #"^\d{2,3}$"#)
private let koMwTagCompiledPatterns: [NSRegularExpression] = [
    try! NSRegularExpression(pattern: "#ID\\s+\\d+기생"),
    try! NSRegularExpression(pattern: "#[^\\s#]+['\\u2019]s\\s+[^\\s#]+"),
]

private enum AppThemeMode: String, CaseIterable, Identifiable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var label: String {
        switch self {
        case .system:
            "시스템 기본"
        case .light:
            "라이트 모드"
        case .dark:
            "다크 모드"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system:
            nil
        case .light:
            .light
        case .dark:
            .dark
        }
    }
}

private enum PreferredLanguage: String, CaseIterable, Identifiable {
    case korean = "ko"
    case japanese = "ja"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .korean:
            "한국어"
        case .japanese:
            "일본어"
        }
    }

    static var defaultFromSystem: PreferredLanguage {
        let preferred = Locale.preferredLanguages.first?.lowercased() ?? "ko"
        return preferred.hasPrefix("ja") ? .japanese : .korean
    }
}

private enum DetailTextLanguage {
    case korean
    case japanese
}

struct ContentView: View {
    @StateObject private var viewModel = HocgViewModel()
    @State private var showingMenu = false
    @State private var imageExpanded = false
    @State private var koExpanded = true
    @State private var jaExpanded = false
    @State private var showingDeckList = false
    @State private var showingDeckEditor = false
    @State private var editingDeckID: UUID?
    @State private var deckTitle = "새 덱"
    @State private var deckEntries: [DeckEntryState] = []
    @State private var savedDecks: [SavedDeckState] = []
    @State private var deckSearchQuery = ""
    @State private var deckCandidates: [DeckCardCandidate] = []
    @State private var showingDeckImportSheet = false
    @State private var deckImportText = ""
    @State private var deckImportMode: DeckImportMode = .holoDuel
    @State private var showingDeckJsonFileImporter = false
    @State private var exportFileItem: ExportFileItem?

    private enum DeckImportMode: String, CaseIterable {
        case holoDuel = "홀로듀얼"
        case holoDelta = "홀로델타"
        case bushiroad = "부시나비"
    }
    @State private var deckToastMessage: String?
    @State private var renamingDeckID: UUID?
    /// 레어리티 선택 시트를 위해 대기 중인 카드 (2개 이상 레어리티 보유 시)
    @State private var pendingCardForRarity: DeckCardCandidate?
    /// 이미 덱에 있는 엔트리의 레어리티 변경 시 대상 entryId
    @State private var pendingRarityChangeEntryId: Int64?
    @State private var renamingDeckTitle = ""
    @State private var multiWordTags: [String] = []
    @AppStorage("theme_mode") private var themeModeRawValue: String = AppThemeMode.system.rawValue
    @AppStorage("preferred_language") private var preferredLanguageRawValue: String = PreferredLanguage.defaultFromSystem.rawValue

    // Cached tag token regex — rebuilt only when multiWordTags changes
    @State private var cachedTagRegexKey: [String] = []
    @State private var cachedTagRegex: NSRegularExpression = tagTokenRegex
    @State private var cachedHighlightRegex: NSRegularExpression = tagTokenRegex

    private var tagRegexForHighlight: NSRegularExpression {
        cachedHighlightRegex
    }

    // Cached detail lines — computed off main thread
    @State private var cachedKoLines: [String] = []
    @State private var cachedJaLines: [String] = []
    @State private var cachedDetailKey: String = ""

    private struct DeckEntryState: Identifiable {
        let id: Int64
        let card: DeckCardCandidate
        var qty: Int
        let maxPerCard: Int
        /// 사용자가 선택한 레어리티. nil 이면 기본값(card.rarity) 사용.
        var selectedRarity: String?

        /// 현재 선택된 레어리티의 이미지 URL
        var effectiveImageUrl: String {
            guard let rarity = selectedRarity,
                  let option = card.selectableIllustrations.first(where: { $0.rarity == rarity }),
                  !option.imageUrl.isEmpty else {
                return card.imageUrl
            }
            return option.imageUrl
        }

        /// 현재 선택된 레어리티의 manage_id (DeckLog 내보내기용)
        var effectiveManageId: Int? {
            guard let rarity = selectedRarity else {
                return card.selectableIllustrations.first(where: { $0.rarity == card.rarity })?.manageIdJp
                    ?? card.illustrations.first(where: { $0.rarity == card.rarity })?.manageIdJp
            }
            return card.selectableIllustrations.first(where: { $0.rarity == rarity })?.manageIdJp
                ?? card.illustrations.first(where: { $0.rarity == rarity })?.manageIdJp
        }

        /// 현재 선택된 레어리티 표시 문자열
        var displayRarity: String {
            selectedRarity ?? card.selectableIllustrations.first?.rarity ?? ""
        }
    }

    private struct SavedDeckState: Identifiable {
        var id: UUID
        var title: String
        var entries: [DeckEntryState]
    }

    private struct ExportFileItem: Identifiable {
        let id = UUID()
        let url: URL
    }

    private func isOshi(_ card: DeckCardCandidate) -> Bool {
        card.cardType.contains("오시") || card.cardType.contains("推し")
    }

    private func isYell(_ card: DeckCardCandidate) -> Bool {
        if card.cardNumber.uppercased().hasPrefix("HY") {
            return true
        }
        let c = card.color.lowercased()
        let t = card.cardType.lowercased()
        return c.contains("옐") || c.contains("yell") || c.contains("エール") || t.contains("yell") || t.contains("エール")
    }

    private func hasUnlimitedPerCardRule(_ card: DeckCardCandidate) -> Bool {
        let normalizedKo = card.koText
            .lowercased()
            .replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "　", with: "")
        let normalizedJa = card.jaText
            .replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "　", with: "")
        return normalizedKo.contains("이카드는갯수제한이없다")
            || normalizedKo.contains("이카드는수량제한이없다")
            || normalizedKo.contains("갯수제한이없다")
            || normalizedKo.contains("수량제한이없다")
            || normalizedKo.contains("몇장이라도넣을수있다")
            || normalizedKo.contains("갯수상관없이여러장넣을수있다")
            || normalizedKo.contains("수량상관없이여러장넣을수있다")
            || (normalizedJa.contains("何枚でも") && normalizedJa.contains("入れられる"))
    }

    private func hasOneCopyByRarity(_ card: DeckCardCandidate) -> Bool {
        var rarities = Set<String>()
        let base = card.rarity.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if !base.isEmpty {
            rarities.insert(base)
        }
        for option in card.illustrations {
            let rarity = option.rarity.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
            if !rarity.isEmpty {
                rarities.insert(rarity)
            }
        }
        return rarities.contains("OUR") || rarities.contains("OSR")
    }

    private func maxPerCard(_ card: DeckCardCandidate) -> Int {
        if isOshi(card) { return 1 }
        if hasOneCopyByRarity(card) { return 1 }
        if isYell(card) { return Int.max }
        if hasUnlimitedPerCardRule(card) { return Int.max }
        return 4
    }

    private var deckOshiCount: Int {
        deckEntries.filter { isOshi($0.card) }.map(\.qty).reduce(0, +)
    }

    private var deckYellCount: Int {
        deckEntries.filter { isYell($0.card) }.map(\.qty).reduce(0, +)
    }

    private var deckMainCount: Int {
        deckEntries.filter { !isOshi($0.card) && !isYell($0.card) }.map(\.qty).reduce(0, +)
    }

    private var deckTotalCount: Int {
        deckEntries.map(\.qty).reduce(0, +)
    }

    private func openDeckBuilder() {
        showingDeckList = false
        showingDeckEditor = true
        Task { deckCandidates = await viewModel.searchDeckCards(deckSearchQuery) }
    }

    private func deckQuantity(for card: DeckCardCandidate) -> Int {
        deckEntries.first(where: { $0.id == card.printId })?.qty ?? 0
    }

    private func blockReason(for card: DeckCardCandidate) -> String? {
        let qty = deckQuantity(for: card)
        let perCardLimit = maxPerCard(card)
        if perCardLimit != .max, qty >= perCardLimit {
            return "이 카드는 최대 \(perCardLimit)장까지만 편성 가능합니다."
        }
        if isOshi(card), deckOshiCount >= 1 {
            return "오시는 1장만 편성 가능합니다."
        }
        if isYell(card), deckYellCount >= 20 {
            return "옐 슬롯이 가득 찼습니다 (20/20)."
        }
        if !isOshi(card) && !isYell(card) && deckMainCount >= 50 {
            return "덱이 가득 찼습니다 (50/50)."
        }
        return nil
    }

    private func showDeckToast(_ message: String) {
        deckToastMessage = message
        Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            if deckToastMessage == message {
                deckToastMessage = nil
            }
        }
    }

    private func addCardToDeck(_ card: DeckCardCandidate) {
        if let reason = blockReason(for: card) {
            showDeckToast(reason)
            return
        }
        // 이미 덱에 있으면 수량만 증가
        if let idx = deckEntries.firstIndex(where: { $0.id == card.printId }) {
            deckEntries[idx].qty += 1
            return
        }
        // 레어리티가 2개 이상이면 선택 시트를 먼저 표시
        if card.hasMultipleRarities {
            pendingRarityChangeEntryId = nil
            pendingCardForRarity = card
            return
        }
        // 레어리티가 1개이면 즉시 추가
        deckEntries.append(
            DeckEntryState(
                id: card.printId,
                card: card,
                qty: 1,
                maxPerCard: maxPerCard(card),
                selectedRarity: nil
            )
        )
    }

    private func addCardToDeckWithRarity(_ card: DeckCardCandidate, rarity: String) {
        pendingCardForRarity = nil
        if let reason = blockReason(for: card) {
            showDeckToast(reason)
            return
        }
        if let idx = deckEntries.firstIndex(where: { $0.id == card.printId }) {
            deckEntries[idx].qty += 1
            deckEntries[idx].selectedRarity = rarity
            return
        }
        deckEntries.append(
            DeckEntryState(
                id: card.printId,
                card: card,
                qty: 1,
                maxPerCard: maxPerCard(card),
                selectedRarity: rarity
            )
        )
    }

    private func changeEntryRarity(entryId: Int64, rarity: String) {
        pendingCardForRarity = nil
        pendingRarityChangeEntryId = nil
        guard let idx = deckEntries.firstIndex(where: { $0.id == entryId }) else { return }
        deckEntries[idx].selectedRarity = rarity
    }

    private func deckThumbnail(url: String, qty: Int, width: CGFloat, height: CGFloat) -> some View {
        ZStack(alignment: .topTrailing) {
            AsyncImage(url: AppPaths().resolveImageURL(url)) { phase in
                remotePhaseView(phase)
            }
            .frame(width: width, height: height)

            if qty > 0 {
                Text("\(qty)")
                    .font(.caption2.weight(.bold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(Color.black.opacity(0.75), in: Capsule())
                    .padding(4)
            }
        }
    }

    private var deckStorage: DeckStorage {
        DeckStorage(paths: AppPaths())
    }

    private func makeDeckRecords(from decks: [SavedDeckState]) -> [SavedDeckRecord] {
        decks.map { deck in
            SavedDeckRecord(
                id: deck.id,
                title: deck.title,
                entries: deck.entries.map {
                    DeckEntryRecord(
                        printId: $0.card.printId,
                        cardNumber: $0.card.cardNumber,
                        qty: $0.qty,
                        selectedRarity: $0.selectedRarity
                    )
                },
                updatedAt: Date()
            )
        }
    }

    private func unresolvedDeckCard(for entry: DeckEntryRecord) -> DeckCardCandidate {
        let cardNumber = entry.cardNumber.isEmpty ? "UNKNOWN-\(entry.printId)" : entry.cardNumber
        let inferredType = cardNumber.uppercased().hasPrefix("HY") ? "エール" : ""
        let inferredRarity = entry.selectedRarity ?? ""
        let inferredId = entry.printId > 0 ? entry.printId : Int64(-abs(cardNumber.hashValue == 0 ? 1 : cardNumber.hashValue))
        return DeckCardCandidate(
            printId: inferredId,
            cardNumber: cardNumber,
            nameJa: cardNumber,
            nameKo: "미복원 카드",
            imageUrl: "",
            cardType: inferredType,
            color: inferredType.isEmpty ? "" : "엘",
            rarity: inferredRarity,
            koText: "업데이트 후 현재 DB와 매칭되지 않아 원본 덱 엔트리를 보존한 카드입니다.",
            jaText: "",
            illustrations: []
        )
    }

    private func resolveDeckStates(from records: [SavedDeckRecord], cards: [DeckCardCandidate]) -> [SavedDeckState] {
        let byPrintId = Dictionary(uniqueKeysWithValues: cards.map { ($0.printId, $0) })
        let byCardNumber = Dictionary(uniqueKeysWithValues: cards.map { ($0.cardNumber.uppercased(), $0) })
        return records.compactMap { record in
            let resolvedEntries = record.entries.compactMap { entry -> DeckEntryState? in
                guard entry.qty > 0 else { return nil }
                let card = byPrintId[entry.printId] ?? byCardNumber[entry.cardNumber.uppercased()] ?? unresolvedDeckCard(for: entry)
                let qty = max(1, entry.qty)
                let selectedRarity = entry.selectedRarity?.trimmingCharacters(in: .whitespacesAndNewlines)
                let resolvedRarity = selectedRarity.flatMap { rarity in
                    card.selectableIllustrations.isEmpty || card.selectableIllustrations.contains(where: { $0.rarity == rarity }) ? rarity : nil
                }
                return DeckEntryState(
                    id: card.printId,
                    card: card,
                    qty: {
                        let limit = maxPerCard(card)
                        if limit == .max { return qty }
                        return min(qty, limit)
                    }(),
                    maxPerCard: maxPerCard(card),
                    selectedRarity: resolvedRarity
                )
            }
            guard !resolvedEntries.isEmpty else { return nil }
            return SavedDeckState(
                id: record.id,
                title: record.title,
                entries: resolvedEntries
            )
        }
    }

    private func persistSavedDecks() {
        let records = makeDeckRecords(from: savedDecks)
        _ = deckStorage.saveLibrary(DeckLibraryRecord(decks: records))
    }

    private func loadSavedDecks() async {
        let library = deckStorage.loadLibrary()
        let cards = await viewModel.searchDeckCards("", limit: 5000)
        let resolved = resolveDeckStates(from: library.decks, cards: cards)
        savedDecks = resolved
    }

    private func mergeImportedDecks(_ records: [SavedDeckRecord]) async -> Int {
        guard !records.isEmpty else { return 0 }
        let cards = await viewModel.searchDeckCards("", limit: 5000)
        let importedStates = resolveDeckStates(from: records, cards: cards)
        guard !importedStates.isEmpty else { return 0 }
        for deck in importedStates {
            if let idx = savedDecks.firstIndex(where: { $0.id == deck.id }) {
                savedDecks[idx] = deck
            } else {
                savedDecks.append(deck)
            }
        }
        persistSavedDecks()
        return importedStates.count
    }

    private func importDeckLibraryFromText() {
        let raw = deckImportText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else {
            showDeckToast("가져오기 코드가 비어 있습니다.")
            return
        }

        switch deckImportMode {
        case .holoDuel:
            importHoloDuelCode(raw)
        case .holoDelta:
            importHoloDeltaCode(raw)
        case .bushiroad:
            importBushiroadCode(raw)
        }
    }

    private func importDeckFromJsonFile(_ url: URL) {
        let canAccess = url.startAccessingSecurityScopedResource()
        defer {
            if canAccess {
                url.stopAccessingSecurityScopedResource()
            }
        }

        do {
            let data = try Data(contentsOf: url)
            guard let text = String(data: data, encoding: .utf8) else {
                showDeckToast("JSON 파일 인코딩을 읽을 수 없습니다.")
                return
            }
            deckImportText = text
            importDeckLibraryFromText()
        } catch {
            showDeckToast("JSON 파일을 읽지 못했습니다.")
        }
    }

    private func importHoloDuelCode(_ raw: String) {
        // 1) HoloDuel Base64 시도
        if let holoDuelDeck = DeckCodeConverter.importHoloDuel(raw) {
            showingDeckImportSheet = false
            deckImportText = ""
            Task {
                let merged = await mergeHoloDuelDeck(holoDuelDeck)
                if merged {
                    showDeckToast("홀로듀얼 덱 가져오기가 완료되었습니다.")
                } else {
                    showDeckToast("카드 정보를 찾을 수 없습니다.")
                }
            }
            return
        }
        // 2) 폴백: 기존 앱 JSON 형식
        guard let data = raw.data(using: .utf8) else {
            showDeckToast("코드 형식이 올바르지 않습니다.")
            return
        }
        let imported = deckStorage.importData(data)
        guard !imported.isEmpty else {
            showDeckToast("가져올 수 있는 덱이 없습니다.")
            return
        }
        showingDeckImportSheet = false
        deckImportText = ""
        Task {
            let merged = await mergeImportedDecks(imported)
            showDeckToast(merged > 0 ? "덱 가져오기가 완료되었습니다." : "가져온 코드에서 유효한 덱을 찾지 못했습니다.")
        }
    }

    private func importBushiroadCode(_ raw: String) {
        showingDeckImportSheet = false
        deckImportText = ""
        Task {
            await MainActor.run { showDeckToast("부시나비에서 덱 정보를 불러오는 중...") }
            do {
                let bushiDeck = try await DeckCodeConverter.fetchBushiDeck(codeOrURL: raw)
                let merged = await mergeBushiDeck(bushiDeck)
                await MainActor.run {
                    showDeckToast(merged ? "부시나비 덱 가져오기가 완료되었습니다." : "카드 정보를 찾을 수 없습니다.")
                }
            } catch {
                await MainActor.run {
                    showDeckToast("부시나비 불러오기 실패: \(error.localizedDescription)")
                }
            }
        }
    }

    private func importHoloDeltaCode(_ raw: String) {
        guard let holoDeltaDeck = DeckCodeConverter.importHoloDelta(raw) else {
            showDeckToast("홀로델타 코드 형식이 올바르지 않습니다.")
            return
        }
        showingDeckImportSheet = false
        deckImportText = ""
        Task {
            let merged = await mergeHoloDeltaDeck(holoDeltaDeck)
            if merged {
                showDeckToast("홀로델타 덱 가져오기가 완료되었습니다.")
            } else {
                showDeckToast("카드 정보를 찾을 수 없습니다.")
            }
        }
    }

    private func convertDeckCodeFromText() {
        let raw = deckImportText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else {
            showDeckToast("변환할 코드가 비어 있습니다.")
            return
        }

        Task {
            switch deckImportMode {
            case .holoDuel:
                await convertHoloDuelToHoloDelta(raw)
            case .holoDelta:
                await convertHoloDeltaToBushiroad(raw)
            case .bushiroad:
                await convertBushiroadToHoloDuel(raw)
            }
        }
    }

    private func convertHoloDuelToHoloDelta(_ raw: String) async {
        guard let holoDuelDeck = DeckCodeConverter.importHoloDuel(raw) else {
            await MainActor.run {
                showDeckToast("홀로듀얼 코드 형식이 올바르지 않습니다.")
            }
            return
        }

        let allCards = await viewModel.searchDeckCards("", limit: 5000)
        let byCardNumber = Dictionary(uniqueKeysWithValues: allCards.map { ($0.cardNumber.uppercased(), $0) })

        var entries: [(cardNumber: String, qty: Int, card: DeckCardCandidate)] = []
        if let card = byCardNumber[holoDuelDeck.oshiCardNumber.uppercased()] {
            entries.append((card.cardNumber, 1, card))
        }
        for (cn, qty) in holoDuelDeck.deckEntries {
            if let card = byCardNumber[cn.uppercased()] {
                entries.append((card.cardNumber, qty, card))
            }
        }
        for (cn, qty) in holoDuelDeck.cheerEntries {
            if let card = byCardNumber[cn.uppercased()] {
                entries.append((card.cardNumber, qty, card))
            }
        }

        guard !entries.isEmpty else {
            await MainActor.run {
                showDeckToast("카드 정보를 찾을 수 없습니다.")
            }
            return
        }

        await MainActor.run { showDeckToast("홀로델타 코드로 변환 중...") }
        guard let holoDeltaCode = DeckCodeConverter.exportHoloDelta(entries: entries, title: "변환 덱") else {
            await MainActor.run {
                showDeckToast("변환 실패: 오시 카드가 없습니다.")
            }
            return
        }

        await MainActor.run {
            UIPasteboard.general.string = holoDeltaCode
            showDeckToast("홀로델타 코드가 클립보드에 복사되었습니다.")
            showingDeckImportSheet = false
            deckImportText = ""
        }
    }

    private func convertHoloDeltaToBushiroad(_ raw: String) async {
        guard let holoDeltaDeck = DeckCodeConverter.importHoloDelta(raw) else {
            await MainActor.run {
                showDeckToast("홀로델타 코드 형식이 올바르지 않습니다.")
            }
            return
        }

        let allCards = await viewModel.searchDeckCards("", limit: 5000)
        let byCardNumber = Dictionary(uniqueKeysWithValues: allCards.map { ($0.cardNumber.uppercased(), $0) })
        var entries: [(cardNumber: String, qty: Int, card: DeckCardCandidate)] = []

        if let card = byCardNumber[holoDeltaDeck.oshiCardNumber.uppercased()] {
            entries.append((card.cardNumber, 1, card))
        }
        for row in holoDeltaDeck.deckEntries {
            if let card = byCardNumber[row.cardNumber.uppercased()] {
                entries.append((card.cardNumber, row.qty, card))
            }
        }
        for row in holoDeltaDeck.cheerEntries {
            if let card = byCardNumber[row.cardNumber.uppercased()] {
                entries.append((card.cardNumber, row.qty, card))
            }
        }

        guard !entries.isEmpty else {
            await MainActor.run {
                showDeckToast("카드 정보를 찾을 수 없습니다.")
            }
            return
        }

        await MainActor.run { showDeckToast("부시나비 코드로 변환 중...") }
        do {
            let url = try await DeckCodeConverter.publishBushiDeck(
                entries: entries,
                title: holoDeltaDeck.deckName ?? "변환 덱",
                manageIdLookup: { printId in viewModel.getManageIdJp(printId: printId) }
            )
            await MainActor.run {
                UIPasteboard.general.string = url
                showDeckToast("부시나비 URL이 클립보드에 복사되었습니다.")
                showingDeckImportSheet = false
                deckImportText = ""
            }
        } catch {
            await MainActor.run {
                showDeckToast("변환 실패: \(error.localizedDescription)")
            }
        }
    }

    private func convertBushiroadToHoloDuel(_ raw: String) async {
        await MainActor.run { showDeckToast("홀로듀얼 코드로 변환 중...") }
        do {
            let bushiDeck = try await DeckCodeConverter.fetchBushiDeck(codeOrURL: raw)
            let allCards = await viewModel.searchDeckCards("", limit: 5000)
            let byCardNumber = Dictionary(uniqueKeysWithValues: allCards.map { ($0.cardNumber.uppercased(), $0) })
            let entries: [(cardNumber: String, qty: Int, card: DeckCardCandidate)] =
                (bushiDeck.pList + bushiDeck.list + bushiDeck.subList).compactMap { bc in
                    guard let card = byCardNumber[bc.cardNumber.uppercased()] else { return nil }
                    return (card.cardNumber, bc.num, card)
                }

            guard let code = DeckCodeConverter.exportHoloDuel(entries: entries) else {
                await MainActor.run {
                    showDeckToast("변환 실패: 오시 카드가 없습니다.")
                }
                return
            }

            await MainActor.run {
                UIPasteboard.general.string = code
                showDeckToast("홀로듀얼 코드가 클립보드에 복사되었습니다.")
                showingDeckImportSheet = false
                deckImportText = ""
            }
        } catch {
            await MainActor.run {
                showDeckToast("변환 실패: \(error.localizedDescription)")
            }
        }
    }

    private func mergeHoloDuelDeck(_ holoDuelDeck: DeckCodeConverter.HoloDuelDeck) async -> Bool {
        let allCards = await viewModel.searchDeckCards("", limit: 5000)
        let byCardNumber = Dictionary(uniqueKeysWithValues: allCards.map { ($0.cardNumber.uppercased(), $0) })

        var entries: [DeckEntryState] = []

        // 오시
        if let card = byCardNumber[holoDuelDeck.oshiCardNumber.uppercased()] {
            entries.append(DeckEntryState(id: card.printId, card: card, qty: 1, maxPerCard: maxPerCard(card)))
        }
        // 메인덱
        for (cn, qty) in holoDuelDeck.deckEntries {
            if let card = byCardNumber[cn.uppercased()] {
                entries.append(DeckEntryState(id: card.printId, card: card, qty: qty, maxPerCard: maxPerCard(card)))
            }
        }
        // 치어덱
        for (cn, qty) in holoDuelDeck.cheerEntries {
            if let card = byCardNumber[cn.uppercased()] {
                entries.append(DeckEntryState(id: card.printId, card: card, qty: qty, maxPerCard: maxPerCard(card)))
            }
        }

        guard !entries.isEmpty else { return false }

        let newDeck = SavedDeckState(id: UUID(), title: "가져온 덱", entries: entries)
        savedDecks.append(newDeck)
        persistSavedDecks()
        return true
    }

    private func mergeBushiDeck(_ bushiDeck: DeckCodeConverter.BushiDeck) async -> Bool {
        let allCards = await viewModel.searchDeckCards("", limit: 5000)
        let byCardNumber = Dictionary(uniqueKeysWithValues: allCards.map { ($0.cardNumber.uppercased(), $0) })

        var entries: [DeckEntryState] = []
        for bc in bushiDeck.pList + bushiDeck.list + bushiDeck.subList {
            if let card = byCardNumber[bc.cardNumber.uppercased()] {
                entries.append(DeckEntryState(id: card.printId, card: card, qty: bc.num, maxPerCard: maxPerCard(card)))
            }
        }

        guard !entries.isEmpty else { return false }

        let title = bushiDeck.title.isEmpty ? "부시나비 덱" : bushiDeck.title
        let newDeck = SavedDeckState(id: UUID(), title: title, entries: entries)
        savedDecks.append(newDeck)
        persistSavedDecks()
        return true
    }

    private func mergeHoloDeltaDeck(_ holoDeltaDeck: DeckCodeConverter.HoloDeltaDeck) async -> Bool {
        let allCards = await viewModel.searchDeckCards("", limit: 5000)
        let byCardNumber = Dictionary(uniqueKeysWithValues: allCards.map { ($0.cardNumber.uppercased(), $0) })

        func selectedRarity(for card: DeckCardCandidate, artIndex: Int) -> String? {
            guard artIndex >= 0, artIndex < card.illustrations.count else { return nil }
            let rarity = card.illustrations[artIndex].rarity
            return rarity.isEmpty ? nil : rarity
        }

        var entries: [DeckEntryState] = []

        if let card = byCardNumber[holoDeltaDeck.oshiCardNumber.uppercased()] {
            entries.append(
                DeckEntryState(
                    id: card.printId,
                    card: card,
                    qty: 1,
                    maxPerCard: maxPerCard(card),
                    selectedRarity: selectedRarity(for: card, artIndex: holoDeltaDeck.oshiArtIndex)
                )
            )
        }

        for row in holoDeltaDeck.deckEntries {
            if let card = byCardNumber[row.cardNumber.uppercased()] {
                entries.append(
                    DeckEntryState(
                        id: card.printId,
                        card: card,
                        qty: row.qty,
                        maxPerCard: maxPerCard(card),
                        selectedRarity: selectedRarity(for: card, artIndex: row.artIndex)
                    )
                )
            }
        }

        for row in holoDeltaDeck.cheerEntries {
            if let card = byCardNumber[row.cardNumber.uppercased()] {
                entries.append(
                    DeckEntryState(
                        id: card.printId,
                        card: card,
                        qty: row.qty,
                        maxPerCard: maxPerCard(card),
                        selectedRarity: selectedRarity(for: card, artIndex: row.artIndex)
                    )
                )
            }
        }

        guard !entries.isEmpty else { return false }
        let title = (holoDeltaDeck.deckName ?? "홀로델타 덱").trimmingCharacters(in: .whitespacesAndNewlines)
        let newDeck = SavedDeckState(id: UUID(), title: title.isEmpty ? "홀로델타 덱" : title, entries: entries)
        savedDecks.append(newDeck)
        persistSavedDecks()
        return true
    }

    // MARK: - 홀로듀얼 코드 내보내기
    private func exportHoloDuelCodeToClipboard(_ deck: SavedDeckState) {
        let entries = deck.entries.map { (cardNumber: $0.card.cardNumber, qty: $0.qty, card: $0.card) }
        guard let code = DeckCodeConverter.exportHoloDuel(entries: entries) else {
            showDeckToast("오시 카드가 없습니다. 덱을 확인해 주세요.")
            return
        }
        UIPasteboard.general.string = code
        showDeckToast("홀로듀얼 코드가 클립보드에 복사되었습니다.")
    }

    private func exportHoloDeltaCodeToClipboard(_ deck: SavedDeckState) {
        let entries = deck.entries.map { (cardNumber: $0.card.cardNumber, qty: $0.qty, card: $0.card) }
        guard let code = DeckCodeConverter.exportHoloDelta(entries: entries, title: deck.title) else {
            showDeckToast("오시 카드가 없습니다. 덱을 확인해 주세요.")
            return
        }
        let safeName = sanitizeDeckFilename(deck.title)
        let fileURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("deck_\(safeName)_\(Int(Date().timeIntervalSince1970)).json")

        do {
            try code.write(to: fileURL, atomically: true, encoding: .utf8)
            exportFileItem = ExportFileItem(url: fileURL)
            showDeckToast("홀로델타 .json 파일 저장 위치를 선택해 주세요.")
        } catch {
            showDeckToast("홀로델타 .json 파일 생성에 실패했습니다.")
        }
    }

    private func sanitizeDeckFilename(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "deck" }
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._-가-힣"))
        let mapped = trimmed.unicodeScalars.map { allowed.contains($0) ? Character($0) : "_" }
        let value = String(mapped)
        return value.isEmpty ? "deck" : value
    }

    // MARK: - 부시나비 코드 내보내기 (비동기, DeckLog 업로드)
    private func exportBushiroadCodeToClipboard(_ deck: SavedDeckState) {
        Task {
            await MainActor.run { showDeckToast("부시나비에 업로드 중...") }
            let entries = deck.entries.map { (cardNumber: $0.card.cardNumber, qty: $0.qty, card: $0.card) }
            do {
                let url = try await DeckCodeConverter.publishBushiDeck(
                    entries: entries,
                    title: deck.title,
                    manageIdLookup: { printId in
                        viewModel.getManageIdJp(printId: printId)
                    }
                )
                await MainActor.run {
                    UIPasteboard.general.string = url
                    showDeckToast("부시나비 URL이 클립보드에 복사되었습니다.")
                }
            } catch {
                await MainActor.run {
                    showDeckToast("부시나비 업로드 실패: \(error.localizedDescription)")
                }
            }
        }
    }

    private func exportDeckImage(_ deck: SavedDeckState) {
        Task {
            await MainActor.run {
                showDeckToast("덱 이미지를 생성하는 중입니다...")
            }
            let images = await loadDeckImages(for: deck)
            guard let image = buildDeckGridImage(deck: deck, images: images) else {
                await MainActor.run {
                    showDeckToast("덱 이미지 생성에 실패했습니다.")
                }
                return
            }
            let saved = await saveDeckImageToGallery(image)
            await MainActor.run {
                showDeckToast(saved ? "덱 이미지가 갤러리에 저장되었습니다." : "갤러리 저장 권한이 없거나 저장에 실패했습니다.")
            }
        }
    }

    private func requestPhotoLibraryAddPermission() async -> PHAuthorizationStatus {
        let status = PHPhotoLibrary.authorizationStatus(for: .addOnly)
        if status == .notDetermined {
            return await withCheckedContinuation { continuation in
                PHPhotoLibrary.requestAuthorization(for: .addOnly) { updatedStatus in
                    continuation.resume(returning: updatedStatus)
                }
            }
        }
        return status
    }

    private func saveDeckImageToGallery(_ image: UIImage) async -> Bool {
        let status = await requestPhotoLibraryAddPermission()
        guard status == .authorized || status == .limited else {
            return false
        }
        return await withCheckedContinuation { continuation in
            PHPhotoLibrary.shared().performChanges({
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            }) { success, _ in
                continuation.resume(returning: success)
            }
        }
    }

    private func loadDeckImages(for deck: SavedDeckState) async -> [Int64: UIImage] {
        let unique = Dictionary(uniqueKeysWithValues: deck.entries.map { ($0.card.printId, $0.effectiveImageUrl) })
        return await withTaskGroup(of: (Int64, UIImage?).self) { group in
            for (printId, imageURL) in unique {
                group.addTask {
                    guard let url = URL(string: imageURL) else {
                        return (printId, nil)
                    }
                    guard let (data, _) = try? await URLSession.shared.data(from: url),
                          let image = UIImage(data: data) else {
                        return (printId, nil)
                    }
                    return (printId, image)
                }
            }
            var result: [Int64: UIImage] = [:]
            for await (printId, image) in group {
                if let image {
                    result[printId] = image
                }
            }
            return result
        }
    }

    private func buildDeckGridImage(deck: SavedDeckState, images: [Int64: UIImage]) -> UIImage? {
        let entries = deck.entries
        guard !entries.isEmpty else { return nil }

        let oshiEntries = entries.filter { isOshi($0.card) }
        let yellEntries = entries.filter { !isOshi($0.card) && isYell($0.card) }
        // 오시 홀로멤 → 옐 → 홀로멤 → 서포트 순 정렬
        func mainSortOrder(_ card: DeckCardCandidate) -> Int {
            let ct = card.cardType.lowercased()
            if ct.contains("홀로멤") || ct.contains("holomem") || ct.contains("ホロメン") { return 0 }
            return 1 // 서포트
        }
        let mainEntries = entries
            .filter { !isOshi($0.card) && !isYell($0.card) }
            .sorted { mainSortOrder($0.card) < mainSortOrder($1.card) }

        let mainColumns = 5
        let sideColumns = 2
        let cardWidth: CGFloat = 140
        let cardHeight: CGFloat = 196
        let gridSpacing: CGFloat = 12
        let padding: CGFloat = 18
        let sideGap: CGFloat = 16
        let titleHeight: CGFloat = 44
        let sectionLabelHeight: CGFloat = 24
        let sectionSubLabelHeight: CGFloat = 24
        let sectionSpacing: CGFloat = 16
        let separatorHeight: CGFloat = 1
        let minEmptySectionHeight: CGFloat = 36

        let canvasWidth = padding * 2 + CGFloat(mainColumns) * cardWidth + CGFloat(mainColumns - 1) * gridSpacing
        let contentWidth = canvasWidth - padding * 2
        let sideWidth = (contentWidth - sideGap) / 2
        let sideGridWidth = CGFloat(sideColumns) * cardWidth + CGFloat(sideColumns - 1) * gridSpacing
        let sideGridOffset = max(0, (sideWidth - sideGridWidth) / 2)

        let oshiRows = Int(ceil(Double(oshiEntries.count) / Double(sideColumns)))
        let yellRows = Int(ceil(Double(yellEntries.count) / Double(sideColumns)))
        let sideRows = max(oshiRows, yellRows)
        let sideGridHeight = sideRows > 0
            ? CGFloat(sideRows) * cardHeight + CGFloat(max(0, sideRows - 1)) * gridSpacing
            : minEmptySectionHeight

        let mainRows = Int(ceil(Double(mainEntries.count) / Double(mainColumns)))
        let mainGridHeight = mainRows > 0
            ? CGFloat(mainRows) * cardHeight + CGFloat(max(0, mainRows - 1)) * gridSpacing
            : minEmptySectionHeight

        let canvasHeight = padding +
            titleHeight +
            sectionSpacing +
            sectionLabelHeight +
            sectionSubLabelHeight +
            sectionSpacing +
            sideGridHeight +
            sectionSpacing +
            separatorHeight +
            sectionSpacing +
            sectionLabelHeight +
            sectionSpacing +
            mainGridHeight +
            padding
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: canvasWidth, height: canvasHeight))

        return renderer.image { context in
            let cg = context.cgContext
            UIColor.white.setFill()
            context.fill(CGRect(x: 0, y: 0, width: canvasWidth, height: canvasHeight))

            let title = deck.title.isEmpty ? "덱" : deck.title
            let titleAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.boldSystemFont(ofSize: 28),
                .foregroundColor: UIColor.black,
            ]
            let sectionAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 20, weight: .bold),
                .foregroundColor: UIColor.black,
            ]
            let subSectionAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 16, weight: .semibold),
                .foregroundColor: UIColor.darkGray,
            ]
            let emptyAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 16, weight: .medium),
                .foregroundColor: UIColor.gray,
            ]
            let fallbackAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: 12, weight: .medium),
                .foregroundColor: UIColor.secondaryLabel,
            ]
            let qtyAttrs: [NSAttributedString.Key: Any] = [
                .font: UIFont.boldSystemFont(ofSize: 16),
                .foregroundColor: UIColor.white,
            ]

            func drawCenteredText(_ text: String, in rect: CGRect, attrs: [NSAttributedString.Key: Any]) {
                let textSize = (text as NSString).size(withAttributes: attrs)
                let textRect = CGRect(
                    x: rect.midX - textSize.width / 2,
                    y: rect.midY - textSize.height / 2,
                    width: textSize.width,
                    height: textSize.height
                )
                (text as NSString).draw(in: textRect, withAttributes: attrs)
            }

            func drawCard(_ entry: DeckEntryState, in frame: CGRect) {
                if let image = images[entry.card.printId] {
                    image.draw(in: frame)
                } else {
                    UIColor.secondarySystemFill.setFill()
                    UIBezierPath(roundedRect: frame, cornerRadius: 10).fill()
                    (entry.card.cardNumber as NSString).draw(
                        in: frame.insetBy(dx: 6, dy: 6),
                        withAttributes: fallbackAttrs
                    )
                }

                let qtyText = "\(entry.qty)"
                let qtySize = (qtyText as NSString).size(withAttributes: qtyAttrs)
                let badgeW = max(28, qtySize.width + 14)
                let badgeH: CGFloat = 24
                let badgeRect = CGRect(
                    x: frame.maxX - badgeW - 6,
                    y: frame.minY + 6,
                    width: badgeW,
                    height: badgeH
                )
                UIColor.black.withAlphaComponent(0.8).setFill()
                UIBezierPath(roundedRect: badgeRect, cornerRadius: badgeH / 2).fill()
                let textRect = CGRect(
                    x: badgeRect.midX - qtySize.width / 2,
                    y: badgeRect.midY - qtySize.height / 2,
                    width: qtySize.width,
                    height: qtySize.height
                )
                (qtyText as NSString).draw(in: textRect, withAttributes: qtyAttrs)
            }

            (title as NSString).draw(
                in: CGRect(x: padding, y: padding, width: canvasWidth - padding * 2, height: titleHeight),
                withAttributes: titleAttrs
            )

            let leftSectionX = padding
            let rightSectionX = padding + sideWidth + sideGap
            let splitX = padding + sideWidth + sideGap / 2

            var currentY = padding + titleHeight + sectionSpacing
            let sideLabelTop = currentY

            drawCenteredText(
                "오시",
                in: CGRect(x: leftSectionX, y: currentY, width: sideWidth, height: sectionLabelHeight),
                attrs: sectionAttrs
            )
            drawCenteredText(
                "옐",
                in: CGRect(x: rightSectionX, y: currentY, width: sideWidth, height: sectionLabelHeight),
                attrs: sectionAttrs
            )
            currentY += sectionLabelHeight

            drawCenteredText(
                "오시 카드",
                in: CGRect(x: leftSectionX, y: currentY, width: sideWidth, height: sectionSubLabelHeight),
                attrs: subSectionAttrs
            )
            drawCenteredText(
                "옐 카드",
                in: CGRect(x: rightSectionX, y: currentY, width: sideWidth, height: sectionSubLabelHeight),
                attrs: subSectionAttrs
            )
            currentY += sectionSubLabelHeight + sectionSpacing

            let sideCardsTop = currentY
            if oshiEntries.isEmpty {
                drawCenteredText(
                    "카드 없음",
                    in: CGRect(x: leftSectionX, y: sideCardsTop, width: sideWidth, height: sideGridHeight),
                    attrs: emptyAttrs
                )
            } else {
                for (index, entry) in oshiEntries.enumerated() {
                    let row = index / sideColumns
                    let col = index % sideColumns
                    let x = leftSectionX + sideGridOffset + CGFloat(col) * (cardWidth + gridSpacing)
                    let y = sideCardsTop + CGFloat(row) * (cardHeight + gridSpacing)
                    drawCard(entry, in: CGRect(x: x, y: y, width: cardWidth, height: cardHeight))
                }
            }

            if yellEntries.isEmpty {
                drawCenteredText(
                    "카드 없음",
                    in: CGRect(x: rightSectionX, y: sideCardsTop, width: sideWidth, height: sideGridHeight),
                    attrs: emptyAttrs
                )
            } else {
                for (index, entry) in yellEntries.enumerated() {
                    let row = index / sideColumns
                    let col = index % sideColumns
                    let x = rightSectionX + sideGridOffset + CGFloat(col) * (cardWidth + gridSpacing)
                    let y = sideCardsTop + CGFloat(row) * (cardHeight + gridSpacing)
                    drawCard(entry, in: CGRect(x: x, y: y, width: cardWidth, height: cardHeight))
                }
            }

            let sideBottom = sideCardsTop + sideGridHeight
            cg.setStrokeColor(UIColor(white: 0.82, alpha: 1).cgColor)
            cg.setLineWidth(1)
            cg.move(to: CGPoint(x: splitX, y: sideLabelTop))
            cg.addLine(to: CGPoint(x: splitX, y: sideBottom))
            cg.strokePath()

            currentY = sideBottom + sectionSpacing
            cg.setStrokeColor(UIColor(white: 0.82, alpha: 1).cgColor)
            cg.setLineWidth(separatorHeight)
            cg.move(to: CGPoint(x: padding, y: currentY))
            cg.addLine(to: CGPoint(x: canvasWidth - padding, y: currentY))
            cg.strokePath()

            currentY += sectionSpacing
            ("덱 카드" as NSString).draw(
                in: CGRect(x: padding, y: currentY, width: contentWidth, height: sectionLabelHeight),
                withAttributes: sectionAttrs
            )
            currentY += sectionLabelHeight + sectionSpacing

            if mainEntries.isEmpty {
                drawCenteredText(
                    "카드 없음",
                    in: CGRect(x: padding, y: currentY, width: contentWidth, height: mainGridHeight),
                    attrs: emptyAttrs
                )
            } else {
                for (index, entry) in mainEntries.enumerated() {
                    let row = index / mainColumns
                    let col = index % mainColumns
                    let x = padding + CGFloat(col) * (cardWidth + gridSpacing)
                    let y = currentY + CGFloat(row) * (cardHeight + gridSpacing)
                    drawCard(entry, in: CGRect(x: x, y: y, width: cardWidth, height: cardHeight))
                }
            }
        }
    }

    private func startRenameDeck(_ deck: SavedDeckState) {
        renamingDeckID = deck.id
        renamingDeckTitle = deck.title
    }

    private func commitRenameDeck() {
        guard let id = renamingDeckID else { return }
        let title = renamingDeckTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else {
            renamingDeckID = nil
            return
        }
        if let idx = savedDecks.firstIndex(where: { $0.id == id }) {
            savedDecks[idx].title = title
            persistSavedDecks()
        }
        renamingDeckID = nil
    }

    private func removeDeck(_ id: UUID) {
        savedDecks.removeAll { $0.id == id }
        if editingDeckID == id {
            editingDeckID = nil
            deckEntries = []
            deckTitle = "새 덱"
        }
        persistSavedDecks()
    }

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .top) {
                if showingDeckList {
                    deckListLayout
                } else if showingDeckEditor {
                    deckEditorLayout
                } else {
                    mobileLayout(screenHeight: geo.size.height)
                }

                if imageExpanded {
                    expandedImageOverlay
                }

                if let toast = deckToastMessage ?? viewModel.toastMessage {
                    Text(toast)
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(Color.black.opacity(0.88), in: Capsule())
                        .padding(.top, 14)
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .simultaneousGesture(
                TapGesture().onEnded {
                    dismissKeyboard()
                },
                including: .all
            )
            .sheet(isPresented: Binding(
                get: { showingMenu },
                set: { showingMenu = $0 }
            )) {
                MenuSheet(
                    state: viewModel.state,
                    themeMode: selectedThemeModeBinding,
                    preferredLanguage: selectedPreferredLanguageBinding,
                    onBulkImageDownload: {
                        showingMenu = false
                        viewModel.onBulkImageDownload()
                    },
                    onManualUpdate: {
                        showingMenu = false
                        viewModel.onManualUpdate()
                    }
                )
            }
            .alert(
                "DB 업데이트",
                isPresented: Binding(
                    get: { viewModel.state.updateDialog != nil },
                    set: { newValue in
                        if !newValue {
                            viewModel.onUpdateDialogDismiss()
                        }
                    }
                ),
                presenting: viewModel.state.updateDialog,
            ) { _ in
                Button("나중에", role: .cancel) {
                    viewModel.onUpdateDialogDismiss()
                }
                Button("업데이트") {
                    viewModel.onUpdateDialogConfirm()
                }
            } message: { dialog in
                Text(
                    "DB 업데이트가 있습니다. 업데이트 하시겠습니까?\n로컬 DB 날짜: \(dialog.localDate ?? "없음")\nGitHub DB 날짜: \(dialog.remoteDate)\(dialog.remoteDigest.map { "\nGitHub DB 식별자: \($0.prefix(8))" } ?? "")"
                )
            }
            .onChange(of: viewModel.state.detailKoText) { _ in
                refreshDetailLines()
            }
            .onChange(of: viewModel.state.detailJaText) { _ in
                refreshDetailLines()
            }
            .onChange(of: preferredLanguageRawValue) { _ in
                refreshDetailLines()
            }
            .onChange(of: multiWordTags) { tags in
                rebuildTagRegexCache(tags)
                refreshDetailLines()
            }
            .sheet(isPresented: $showingDeckImportSheet) {
                NavigationStack {
                    VStack(alignment: .leading, spacing: 12) {
                        Picker("가져오기 방식", selection: $deckImportMode) {
                            ForEach(DeckImportMode.allCases, id: \.self) { mode in
                                Text(mode.rawValue).tag(mode)
                            }
                        }
                        .pickerStyle(.segmented)

                        Text(
                            deckImportMode == .holoDuel
                            ? "홀로듀얼 덱 코드(Base64)를 붙여넣어 주세요."
                            : deckImportMode == .holoDelta
                                ? "홀로델타 코드(JSON 또는 Base64 URL-safe)를 붙여넣어 주세요."
                                : "부시나비 URL 또는 코드를 붙여넣어 주세요.\n예: 6ADJR (URL 전체 입력 불필요)"
                        )
                            .font(.subheadline)
                            .foregroundColor(.secondary)

                        TextEditor(text: $deckImportText)
                            .font(.system(.footnote, design: .monospaced))
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            .padding(8)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.secondary.opacity(0.35), lineWidth: 1)
                            )

                        if deckImportMode == .holoDelta {
                            Button("홀로델타 JSON 파일 선택") {
                                showingDeckJsonFileImporter = true
                            }
                            .buttonStyle(.bordered)
                        }

                        Button(
                            deckImportMode == .holoDuel
                            ? "홀로델타 코드로 변환"
                            : deckImportMode == .holoDelta
                                ? "부시나비 코드로 변환"
                                : "홀로듀얼 코드로 변환"
                        ) {
                            convertDeckCodeFromText()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                    .padding(14)
                    .navigationTitle("덱 가져오기")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("취소") {
                                showingDeckImportSheet = false
                            }
                        }
                        ToolbarItem(placement: .confirmationAction) {
                            Button("가져오기") {
                                importDeckLibraryFromText()
                            }
                        }
                    }
                }
            }
            .sheet(item: $exportFileItem) { item in
                ActivityShareSheet(activityItems: [item.url])
            }
            .fileImporter(
                isPresented: $showingDeckJsonFileImporter,
                allowedContentTypes: [.json],
                allowsMultipleSelection: false
            ) { result in
                switch result {
                case .success(let urls):
                    if let url = urls.first {
                        importDeckFromJsonFile(url)
                    }
                case .failure:
                    showDeckToast("JSON 파일 선택에 실패했습니다.")
                }
            }
            // 레어리티 선택 시트
            .sheet(item: $pendingCardForRarity) { card in
                RarityPickerSheet(
                    card: card,
                    currentRarity: pendingRarityChangeEntryId.flatMap { eid in
                        deckEntries.first(where: { $0.id == eid })?.selectedRarity
                    } ?? card.selectableIllustrations.first?.rarity ?? "",
                    onSelect: { rarity in
                        if let eid = pendingRarityChangeEntryId {
                            changeEntryRarity(entryId: eid, rarity: rarity)
                        } else {
                            addCardToDeckWithRarity(card, rarity: rarity)
                        }
                    },
                    onCancel: {
                        pendingCardForRarity = nil
                        pendingRarityChangeEntryId = nil
                    }
                )
                .presentationDetents([.medium])
            }
            .alert(
                "덱 이름 수정",
                isPresented: Binding(
                    get: { renamingDeckID != nil },
                    set: { newValue in
                        if !newValue {
                            renamingDeckID = nil
                        }
                    }
                )
            ) {
                TextField("덱 이름", text: $renamingDeckTitle)
                Button("취소", role: .cancel) {
                    renamingDeckID = nil
                }
                Button("저장") {
                    commitRenameDeck()
                }
            } message: {
                Text("변경할 덱 이름을 입력하세요.")
            }
            .animation(.easeInOut(duration: 0.2), value: viewModel.toastMessage)
            .animation(.easeInOut(duration: 0.2), value: deckToastMessage)
            .task {
                let tags = await Task.detached {
                    DatabaseRepository(paths: AppPaths()).loadMultiWordTags()
                }.value
                multiWordTags = tags
                await loadSavedDecks()
            }
            .preferredColorScheme(selectedThemeMode.colorScheme)
        }
    }

    private var selectedThemeMode: AppThemeMode {
        AppThemeMode(rawValue: themeModeRawValue) ?? .system
    }

    private var selectedThemeModeBinding: Binding<AppThemeMode> {
        Binding(
            get: { selectedThemeMode },
            set: { themeModeRawValue = $0.rawValue }
        )
    }

    private var selectedPreferredLanguage: PreferredLanguage {
        PreferredLanguage(rawValue: preferredLanguageRawValue) ?? .defaultFromSystem
    }

    private var selectedPreferredLanguageBinding: Binding<PreferredLanguage> {
        Binding(
            get: { selectedPreferredLanguage },
            set: { preferredLanguageRawValue = $0.rawValue }
        )
    }

    private func resetDetailExpansion() {
        let hasKo = !cachedKoLines.isEmpty
        let hasJa = !cachedJaLines.isEmpty

        guard hasKo || hasJa else {
            koExpanded = false
            jaExpanded = false
            return
        }

        if hasKo && hasJa {
            koExpanded = selectedPreferredLanguage == .korean
            jaExpanded = selectedPreferredLanguage == .japanese
        } else {
            koExpanded = hasKo
            jaExpanded = hasJa
        }
    }

    private func refreshDetailLines() {
        let koText = viewModel.state.detailKoText
        let jaText = viewModel.state.detailJaText
        let lang = selectedPreferredLanguage
        let tags = multiWordTags
        let key = "\(koText.hashValue)|\(jaText.hashValue)|\(lang.rawValue)|\(tags.count)"
        guard key != cachedDetailKey else { return }
        cachedDetailKey = key

        // Capture value-type copy of self so computation runs off main thread safely
        let snapshot = self
        Task.detached(priority: .userInitiated) {
            let ko = snapshot.splitDetailLines(koText, language: .korean)
            let ja = snapshot.splitDetailLines(jaText, language: .japanese)
            await MainActor.run {
                self.cachedKoLines = ko
                self.cachedJaLines = ja
                self.resetDetailExpansion()
            }
        }
    }

    private func rebuildTagRegexCache(_ tags: [String]) {
        var parts: [String] = tags.map { NSRegularExpression.escapedPattern(for: $0) }
        for pat in Self.koMwTagPatterns {
            parts.append(pat)
        }
        parts.append("#[^\\s#]+")
        let pattern = parts.joined(separator: "|")
        let base = (try? NSRegularExpression(pattern: pattern)) ?? tagTokenRegex
        let highlightPattern = "\(pattern)|블룸 이펙트|ブルームエフェクト"
        let highlight = (try? NSRegularExpression(pattern: highlightPattern)) ?? base
        cachedTagRegex = base
        cachedHighlightRegex = highlight
    }

    private func mobileLayout(screenHeight: CGFloat) -> some View {
        let rawListHeight = scaledHeight(screenHeight: screenHeight, ratio: 0.30, minHeight: 190, maxHeight: 360)
        let listHeight = snappedListPanelHeight(rawListHeight)
        let imageHeight = scaledHeight(screenHeight: screenHeight, ratio: 0.45, minHeight: 240, maxHeight: 560)

        return ScrollView {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    TextField(
                        "카드번호 / 이름 / 태그 / 한국어 본문 검색",
                        text: Binding(
                            get: { viewModel.state.searchQuery },
                            set: { viewModel.onSearchQueryChanged($0) }
                        )
                    )
                    .textFieldStyle(.plain)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 9)
                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).stroke(Color(.separator), lineWidth: 1))
                    .disabled(viewModel.state.updateRunning)

                    ModernActionButton("덱빌딩", compact: true, action: openDeckBuilder)
                        .disabled(viewModel.state.updateRunning)

                    Button {
                        dismissKeyboard()
                        showingMenu = true
                    } label: {
                        Image(systemName: "line.3.horizontal")
                            .font(.title3)
                    }
                    .disabled(viewModel.state.updateRunning)
                }

                updateStatusBlock

                Divider()

                Text("목록")
                    .font(.headline)
                panel(height: listHeight) {
                    resultsList
                }

                HStack {
                    Text("이미지")
                        .font(.headline)
                    Spacer()
                    ModernActionButton(viewModel.state.imageCollapsed ? "이미지 펼치기" : "이미지 접기", compact: true) {
                        viewModel.onToggleImagePanel()
                    }
                }

                if viewModel.state.imageCollapsed {
                    Text("이미지를 접었습니다.")
                        .font(.footnote)
                        .foregroundColor(.secondary)
                } else {
                    searchRaritySelector
                    panel(height: imageHeight) {
                        imagePanel
                    }
                }

                Text("효과")
                    .font(.headline)
                panel(height: nil) {
                    detailPanel(scrollable: false)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
        }
    }

    private var updateStatusBlock: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !viewModel.state.updateStatus.isEmpty {
                Text(viewModel.state.updateStatus)
                    .font(.footnote)
                    .foregroundColor(viewModel.state.updateStatusError ? .red : .green)
            }

            if let message = viewModel.state.persistentMessage, !message.isEmpty {
                Text(message)
                    .font(.footnote)
                    .foregroundColor(.red)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.red.opacity(0.13), in: RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    private var resultsList: some View {
        Group {
            if viewModel.state.results.isEmpty {
                Text("검색 결과가 없습니다.")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 4) {
                        ForEach(viewModel.state.results) { row in
                            let isSelected = viewModel.state.selectedPrintId == row.printId
                            let displayName: String = {
                                switch selectedPreferredLanguage {
                                case .korean:
                                    let k = DatabaseRepository.cleanDisplayName(row.nameKo)
                                    return k.isEmpty ? (row.nameJa.isEmpty ? "(이름 없음)" : row.nameJa) : k
                                case .japanese:
                                    return row.nameJa.isEmpty ? (row.nameKo.isEmpty ? "(이름 없음)" : DatabaseRepository.cleanDisplayName(row.nameKo)) : row.nameJa
                                }
                            }()
                            HStack(spacing: 0) {
                                Rectangle()
                                    .fill(isSelected ? Color.accentColor : Color.clear)
                                    .frame(width: 3)
                                    .clipShape(UnevenRoundedRectangle(topLeadingRadius: 8, bottomLeadingRadius: 8))
                                HStack(spacing: 6) {
                                    if !row.cardNumber.isEmpty {
                                        Text(row.cardNumber)
                                            .font(.caption2)
                                            .padding(.horizontal, 6)
                                            .padding(.vertical, 2)
                                            .background(Color.blue.opacity(0.18), in: RoundedRectangle(cornerRadius: 8))
                                    }
                                    Text(displayName)
                                        .font(.body)
                                        .fontWeight(isSelected ? .semibold : .regular)
                                        .lineLimit(1)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                                .padding(.horizontal, 8)
                                .padding(.vertical, 9)
                            }
                            .background(isSelected ? Color.blue.opacity(0.20) : Color.clear, in: RoundedRectangle(cornerRadius: 8))
                            .contentShape(Rectangle())
                            .onTapGesture { viewModel.onSelectPrint(row.printId) }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                // 내부 ScrollView 스크롤이 외부 ScrollView(전체 페이지)로 전파되는 것을 방지
                .simultaneousGesture(DragGesture(), including: .all)
            }
        }
    }

    private var imagePanel: some View {
        cardImageContent
            .contentShape(Rectangle())
            .onTapGesture { imageExpanded = true }
            .simultaneousGesture(raritySwipeGesture)
    }

    private var expandedImageOverlay: some View {
        ZStack {
            Color.black.opacity(0.92)
                .ignoresSafeArea()

            cardImageContent
                .padding(16)
                .contentShape(Rectangle())
                .onTapGesture { imageExpanded = false }
                .simultaneousGesture(raritySwipeGesture)
        }
        .zIndex(10)
    }

    private var raritySwipeGesture: some Gesture {
        DragGesture(minimumDistance: 24)
            .onEnded { value in
                if value.translation.width <= -48 {
                    selectAdjacentIllustration(direction: 1)
                } else if value.translation.width >= 48 {
                    selectAdjacentIllustration(direction: -1)
                }
            }
    }

    private func selectAdjacentIllustration(direction: Int) {
        let options = viewModel.state.selectedIllustrations
        guard options.count > 1, direction != 0 else { return }
        let currentIndex = options.firstIndex { $0.rarity == viewModel.state.selectedRarity } ?? 0
        let nextIndex = (currentIndex + direction).positiveModulo(options.count)
        let option = options[nextIndex]
        let imageURL = option.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? viewModel.state.selectedImageUrl : option.imageUrl
        viewModel.onSelectIllustration(rarity: option.rarity, imageURL: imageURL)
    }

    @ViewBuilder
    private var cardImageContent: some View {
        switch viewModel.state.imageState {
        case .loading:
            VStack(spacing: 8) {
                ProgressView()
                Text("이미지 로딩 중...")
                    .font(.footnote)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

        case .local(let url):
            AsyncImage(url: url) { phase in
                imagePhaseView(phase)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

        case .remote(let url):
            AsyncImage(url: url) { phase in
                imagePhaseView(phase)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

        case .placeholder(let message):
            placeholder(message: message, error: false)

        case .error(let message):
            placeholder(message: message, error: true)
        }
    }

    @ViewBuilder
    private var searchRaritySelector: some View {
        let options = viewModel.state.selectedIllustrations
        if options.count > 1 {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(options) { option in
                        let selected = option.rarity == viewModel.state.selectedRarity
                        Button {
                            let imageURL = option.imageUrl.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? viewModel.state.selectedImageUrl : option.imageUrl
                            viewModel.onSelectIllustration(rarity: option.rarity, imageURL: imageURL)
                        } label: {
                            Text(option.rarity)
                                .font(.caption.bold())
                                .padding(.horizontal, 10)
                                .padding(.vertical, 5)
                                .background(selected ? Color.accentColor : Color.secondary.opacity(0.16))
                                .foregroundColor(selected ? .white : .primary)
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func detailPanel(scrollable: Bool) -> some View {
        let koLines = cachedKoLines
        let jaLines = cachedJaLines

        return Group {
            if scrollable {
                ScrollView {
                    detailLinesView(koLines: koLines, jaLines: jaLines)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            } else {
                detailLinesView(koLines: koLines, jaLines: jaLines)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private func detailLinesView(koLines: [String], jaLines: [String]) -> some View {
        let hasKo = !koLines.isEmpty
        let hasJa = !jaLines.isEmpty

        return VStack(alignment: .leading, spacing: 6) {
            if !hasKo && !hasJa {
                if viewModel.state.detailLoading {
                    HStack(spacing: 8) {
                        ProgressView()
                            .controlSize(.small)
                        Text("(본문 로딩 중...)")
                            .foregroundColor(.secondary)
                    }
                } else {
                    Text("(본문 없음)")
                }
            } else if hasKo && hasJa {
                detailSection(title: "한국어", lines: koLines, expanded: $koExpanded)
                detailSection(title: "일본어", lines: jaLines, expanded: $jaExpanded)
            } else if hasKo {
                sectionChip("한국어")
                ForEach(Array(koLines.enumerated()), id: \.offset) { item in
                    detailLine(item.element)
                }
            } else {
                sectionChip("일본어")
                ForEach(Array(jaLines.enumerated()), id: \.offset) { item in
                    detailLine(item.element)
                }
            }
        }
    }

    private func splitDetailLines(_ text: String, language: DetailTextLanguage) -> [String] {
        let payload: String
        switch language {
        case .korean:
            payload = prettifyKoDetailText(text)
        case .japanese:
            payload = prettifyJaDetailText(text)
        }

        let lines = payload
            .split(whereSeparator: { $0.isNewline })
            .map { sanitizeDetailLine(String($0)) }
            .map(normalizeInlineWhitespace)
            .filter { !$0.isEmpty }

        return mergeBrokenTagLines(lines)
    }

    private func mergeBrokenTagLines(_ lines: [String]) -> [String] {
        var output: [String] = []
        var index = 0

        while index < lines.count {
            let line = lines[index].trimmingCharacters(in: .whitespacesAndNewlines)
            if line == "태그" || line == "タグ" {
                var tags: [String] = []
                var cursor = index

                while cursor < lines.count {
                    let current = lines[cursor].trimmingCharacters(in: .whitespacesAndNewlines)
                    if current == line,
                       cursor + 1 < lines.count,
                       lines[cursor + 1].trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("#") {
                        tags.append(lines[cursor + 1].trimmingCharacters(in: .whitespacesAndNewlines))
                        cursor += 2
                        continue
                    }
                    if current.hasPrefix("#") {
                        tags.append(current)
                        cursor += 1
                        continue
                    }
                    break
                }

                if !tags.isEmpty {
                    output.append("\(line) \(tags.joined(separator: " "))")
                    index = cursor
                    continue
                }
            }

            output.append(lines[index])
            index += 1
        }

        return output
    }

    private func sanitizeDetailLine(_ line: String) -> String {
        let noHtml = line.replacingOccurrences(of: htmlTagPattern, with: " ", options: .regularExpression)
        let noWidth = noHtml.replacingOccurrences(of: widthArtifactPattern, with: " ", options: .regularExpression)
        let trimmed = noWidth.trimmingCharacters(in: .whitespacesAndNewlines)
        let fullRange = NSRange(location: 0, length: trimmed.utf16.count)
        if !trimmed.isEmpty, let match = detailPrefixRegex.firstMatch(in: trimmed, range: fullRange), match.range.location == 0, match.range.length == fullRange.length {
            return trimmed
        }
        let range = NSRange(location: 0, length: trimmed.utf16.count)
        return detailPrefixRegex.stringByReplacingMatches(in: trimmed, range: range, withTemplate: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func prettifyKoDetailText(_ text: String) -> String {
        return prettifyDetailText(
            text,
            replacements: koDetailReplacements,
            sectionMarkerRegex: koSectionMarkerRegex,
            lineBreakRules: koLineBreakRules,
            sectionBreakOnceLabels: ["블룸 이펙트"],
            tagLabel: "태그",
            metadataTokens: koMetadataTokenSet,
            stripJapaneseCharacters: true,
            multiWordTags: multiWordTags
        )
    }

    private func prettifyJaDetailText(_ text: String) -> String {
        return prettifyDetailText(
            text,
            replacements: jaDetailReplacements,
            sectionMarkerRegex: jaSectionMarkerRegex,
            lineBreakRules: jaLineBreakRules,
            sectionBreakOnceLabels: ["ブルームエフェクト"],
            tagLabel: "タグ",
            metadataTokens: jaMetadataTokenSet,
            multiWordTags: multiWordTags
        )
    }

    private func prettifyDetailText(
        _ text: String,
        replacements: [(String, String)],
        sectionMarkerRegex: NSRegularExpression,
        lineBreakRules: [(String, String)],
        sectionBreakOnceLabels: [String],
        tagLabel: String,
        metadataTokens: Set<String>,
        stripJapaneseCharacters: Bool = false,
        multiWordTags: [String] = []
    ) -> String {
        var normalized = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if normalized.isEmpty {
            return ""
        }

        for (before, after) in replacements {
            normalized = normalized.replacingOccurrences(of: before, with: after)
        }
        if stripJapaneseCharacters {
            normalized = normalized.replacingOccurrences(of: japaneseCharPattern, with: " ", options: .regularExpression)
        }

        var lines = normalized
            .split(whereSeparator: { $0.isNewline })
            .map { normalizeInlineWhitespace(String($0)) }
            .filter { !$0.isEmpty }

        if lines.count <= 2 {
            var merged = normalizeInlineWhitespace(lines.joined(separator: " "))
            if let markerRange = firstSectionRange(in: merged, regex: sectionMarkerRegex), markerRange.lowerBound > merged.startIndex {
                let markerChar = merged[markerRange.lowerBound]
                if markerChar != "#" && !matchesDetailPrefix(merged) {
                    merged = String(merged[markerRange.lowerBound...])
                }
            }

            merged = protectMultiWordTags(merged, tags: multiWordTags)
            for label in sectionBreakOnceLabels {
                merged = insertSectionBreakOnce(merged, label: label)
            }
            for (pattern, replacement) in lineBreakRules {
                merged = merged.replacingOccurrences(of: pattern, with: replacement, options: .regularExpression)
            }
            merged = restoreMultiWordTags(merged)

            lines = merged
                .split(whereSeparator: { $0.isNewline })
                .map { normalizeInlineWhitespace(String($0)) }
                .filter { !$0.isEmpty }
        }

        let expanded = lines

        let markerIndex = expanded.firstIndex(where: { splitSectionLabel($0) != nil })
        let trimmed = markerIndex.map { Array(expanded[$0...]) } ?? expanded
        let filtered = trimmed.filter { !isNoiseMetadataLine($0, metadataTokens: metadataTokens) }

        var result: [String] = []
        for line in filtered {
            if isStandaloneTagMetadataLine(line) {
                if result.last != tagLabel {
                    result.append(tagLabel)
                }
                result.append(normalizeTagLine(line))
                continue
            }
            if line == tagLabel, result.last == tagLabel {
                continue
            }
            if result.last == line, sectionLabels.contains(line) {
                continue
            }
            result.append(line)
        }

        return result.joined(separator: "\n")
    }

    private func detailSection(title: String, lines: [String], expanded: Binding<Bool>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                sectionChip(title)
                Spacer()
                Button(expanded.wrappedValue ? "접기" : "펼치기") {
                    expanded.wrappedValue.toggle()
                }
                .buttonStyle(.plain)
                .foregroundColor(.blue)
                .font(.caption)
            }
            if expanded.wrappedValue {
                ForEach(Array(lines.enumerated()), id: \.offset) { item in
                    detailLine(item.element)
                }
            }
        }
    }

    @ViewBuilder
    private func imagePhaseView(_ phase: AsyncImagePhase) -> some View {
        switch phase {
        case .success(let image):
            image
                .resizable()
                .scaledToFit()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .failure:
            placeholder(message: "이미지 로딩 실패", error: true)
        case .empty:
            ProgressView()
        @unknown default:
            placeholder(message: "이미지 없음", error: false)
        }
    }

    @ViewBuilder
    private func remotePhaseView(_ phase: AsyncImagePhase) -> some View {
        switch phase {
        case .success(let image):
            image
                .resizable()
                .scaledToFill()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipped()
                .cornerRadius(6)
        case .failure:
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.secondary.opacity(0.12))
                .overlay(
                    Image(systemName: "exclamationmark.triangle")
                        .font(.caption)
                        .foregroundColor(.secondary)
                )
        case .empty:
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.secondary.opacity(0.1))
                .overlay(ProgressView().controlSize(.small))
        @unknown default:
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.secondary.opacity(0.1))
        }
    }

    private func placeholder(message: String, error: Bool) -> some View {
        VStack(spacing: 8) {
            Image(systemName: error ? "photo.badge.exclamationmark" : "photo")
                .font(.system(size: 28))
                .foregroundColor(.secondary)
            Text(message)
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func detailLine(_ line: String) -> AnyView {
        if let (label, rest) = splitSectionLabel(line) {
            if rest.isEmpty {
                return AnyView(
                    Text(label)
                        .font(.caption)
                        .fontWeight(.bold)
                )
            }
            return AnyView(
                VStack(alignment: .leading, spacing: 4) {
                    Text(label)
                        .font(.caption)
                        .fontWeight(.bold)
                    highlightedTagText(rest)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            )
        }

        if line.hasPrefix("#") {
            return AnyView(
                tagStyledText(line)
                    .frame(maxWidth: .infinity, alignment: .leading)
            )
        }

        return AnyView(
            highlightedTagText(line)
                .frame(maxWidth: .infinity, alignment: .leading)
        )
    }

    private func highlightedTagText(_ text: String) -> Text {
        let regex = cachedHighlightRegex

        let ns = text as NSString
        let matches = regex.matches(in: text, range: NSRange(location: 0, length: ns.length))
        if matches.isEmpty {
            return Text(text)
        }

        var result = Text("")
        var cursor = 0
        for match in matches {
            if match.range.location > cursor {
                let plain = ns.substring(with: NSRange(location: cursor, length: match.range.location - cursor))
                result = result + Text(plain)
            }
            let tag = ns.substring(with: match.range)
            result = result + Text(tag).foregroundColor(.blue).fontWeight(.semibold)
            cursor = match.range.location + match.range.length
        }
        if cursor < ns.length {
            let tail = ns.substring(with: NSRange(location: cursor, length: ns.length - cursor))
            result = result + Text(tail)
        }
        return result
    }

    private func insertSectionBreakOnce(_ text: String, label: String) -> String {
        let escaped = NSRegularExpression.escapedPattern(for: label)
        guard let regex = try? NSRegularExpression(pattern: "\\s*\(escaped)\\s*") else {
            return text
        }
        let ns = text as NSString
        let range = NSRange(location: 0, length: ns.length)
        guard let first = regex.firstMatch(in: text, range: range) else {
            return text
        }
        return ns.replacingCharacters(in: first.range, with: "\n\(label)\n")
    }

    private func splitSectionLabel(_ line: String) -> (String, String)? {
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        let separators = [" ", ":", "：", "[", "(", "【"]
        for label in sectionLabelsSorted {
            if trimmed == label {
                return (label, "")
            }
            guard trimmed.hasPrefix(label) else {
                continue
            }
            let suffix = String(trimmed.dropFirst(label.count))
            let rest = suffix.trimmingCharacters(in: .whitespacesAndNewlines)
            if rest.isEmpty {
                return (label, "")
            }
            if separators.contains(where: { suffix.hasPrefix($0) }) {
                return (label, rest)
            }
        }
        return nil
    }

    /// Japanese tag-object boundary: split `#TAG を...` into (tag, rest)
    private func jaTagObjectSplit(_ text: String) -> (tag: String, rest: String)? {
        let nsText = text as NSString
        let range = NSRange(location: 0, length: nsText.length)
        guard let match = jaTagObjectSplitRegex.firstMatch(in: text, range: range), match.numberOfRanges == 3 else {
            return nil
        }
        let tag = nsText.substring(with: match.range(at: 1))
        let rest = nsText.substring(with: match.range(at: 2))
        return (tag, rest)
    }

    /// Recursive helper for expanding tag lines with Japanese boundary handling
    private func expandTagLinesHelper(_ lines: [String], tagLabel: String) -> [String] {
        var result: [String] = []
        for line in lines {
            guard line.contains("#") else {
                result.append(line)
                continue
            }
            if let jaMatch = jaTagObjectSplit(line) {
                result.append(tagLabel)
                result.append(normalizeInlineWhitespace(jaMatch.tag))
                let tail = normalizeInlineWhitespace(jaMatch.rest)
                if !tail.isEmpty {
                    if tail.contains("#") {
                        result.append(contentsOf: expandTagLinesHelper([tail], tagLabel: tagLabel))
                    } else {
                        result.append(tail)
                    }
                }
            } else {
                result.append(line)
            }
        }
        return result
    }

    private func normalizeInlineWhitespace(_ text: String) -> String {
        text
            .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func isStandaloneTagMetadataLine(_ line: String) -> Bool {
        let normalized = normalizeInlineWhitespace(line)
        guard normalized.hasPrefix("#") else {
            return false
        }

        let dynamicRegex = cachedTagRegex
        let nsRange = NSRange(normalized.startIndex..., in: normalized)
        let matches = dynamicRegex.matches(in: normalized, options: [], range: nsRange)
        guard !matches.isEmpty else {
            return false
        }

        var remainder = normalized
        for match in matches.reversed() {
            guard let range = Range(match.range, in: remainder) else {
                continue
            }
            remainder.replaceSubrange(range, with: " ")
        }
        return normalizeInlineWhitespace(remainder).isEmpty
    }

    private func firstSectionRange(in text: String, regex: NSRegularExpression) -> Range<String.Index>? {
        let range = NSRange(text.startIndex..., in: text)
        guard let match = regex.firstMatch(in: text, options: [], range: range) else {
            return nil
        }
        return Range(match.range, in: text)
    }

    private func matchesDetailPrefix(_ text: String) -> Bool {
        let range = NSRange(text.startIndex..., in: text)
        guard let match = detailPrefixRegex.firstMatch(in: text, options: [], range: range) else {
            return false
        }
        return match.range.location == 0
    }

    private func normalizeTagLine(_ line: String) -> String {
        let dynamicRegex = cachedTagRegex
        let nsRange = NSRange(line.startIndex..., in: line)
        let matches = dynamicRegex.matches(in: line, options: [], range: nsRange)
        guard !matches.isEmpty else {
            return normalizeInlineWhitespace(line)
        }

        let tags = matches.compactMap { match -> String? in
            guard let range = Range(match.range, in: line) else {
                return nil
            }
            return String(line[range])
        }

        var remainder = line
        for tag in tags {
            remainder = remainder.replacingOccurrences(of: tag, with: " ")
        }
        let tail = normalizeInlineWhitespace(remainder)
        if tail.isEmpty {
            return tags.joined(separator: " ")
        }
        return "\(tags.joined(separator: " ")) \(tail)"
    }

    private func isNoiseMetadataLine(_ line: String, metadataTokens: Set<String>) -> Bool {
        let normalized = normalizeInlineWhitespace(line)
        if normalized.isEmpty {
            return true
        }

        let lowered = normalized.lowercased()
        let nsLowered = lowered as NSString
        let fullRange = NSRange(location: 0, length: nsLowered.length)
        if scalarMetadataPattern.firstMatch(in: lowered, range: fullRange) != nil {
            return true
        }

        let tokens = lowered.split(separator: " ").map(String.init)
        if !tokens.isEmpty && tokens.allSatisfy({ token in
            if metadataTokens.contains(token) { return true }
            let nsToken = token as NSString
            return digitTokenPattern.firstMatch(in: token, range: NSRange(location: 0, length: nsToken.length)) != nil
        }) {
            return true
        }

        return false
    }

    private func tagStyledText(_ line: String) -> Text {
        let dynamicRegex = cachedTagRegex
        let nsRange = NSRange(line.startIndex..., in: line)
        let matches = dynamicRegex.matches(in: line, options: [], range: nsRange)
        guard !matches.isEmpty else {
            return Text(line)
        }

        var composed = Text("")
        var cursor = line.startIndex
        for match in matches {
            guard let range = Range(match.range, in: line) else {
                continue
            }
            if cursor < range.lowerBound {
                composed = composed + Text(String(line[cursor..<range.lowerBound]))
            }
            composed = composed + Text(String(line[range]))
                .fontWeight(.semibold)
                .foregroundColor(.blue)
            cursor = range.upperBound
        }
        if cursor < line.endIndex {
            composed = composed + Text(String(line[cursor...]))
        }
        return composed
    }

    private func sectionChip(_ text: String) -> some View {
        Text(text)
            .font(.caption.weight(.bold))
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(Color.blue.opacity(0.15), in: Capsule())
            .overlay(Capsule().stroke(Color.blue.opacity(0.35), lineWidth: 1))
    }

    private func panel<Content: View>(height: CGFloat?, fillHeight: Bool = false, @ViewBuilder content: () -> Content) -> some View {
        Group {
            if let height {
                content()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .frame(height: height, alignment: .top)
            } else if fillHeight {
                content()
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            } else {
                content()
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(10)
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.secondary.opacity(0.35), lineWidth: 1)
        )
    }

    private func scaledHeight(screenHeight: CGFloat, ratio: CGFloat, minHeight: CGFloat, maxHeight: CGFloat) -> CGFloat {
        let scaled = screenHeight * ratio
        return Swift.min(Swift.max(scaled, minHeight), maxHeight)
    }

    private func snappedListPanelHeight(_ rawHeight: CGFloat) -> CGFloat {
        let panelVerticalPadding: CGFloat = 20
        let rowHeight: CGFloat = 38
        let rowSpacing: CGFloat = 4
        let rowStride = rowHeight + rowSpacing

        let available = Swift.max(rawHeight - panelVerticalPadding + rowSpacing, rowStride)
        let fullRows = Swift.max(1, Int((available / rowStride).rounded(.down)))
        let snappedInnerHeight = CGFloat(fullRows) * rowStride - rowSpacing
        return snappedInnerHeight + panelVerticalPadding
    }

    private func resultTitle(_ row: PrintRow) -> String {
        let displayName: String
        switch selectedPreferredLanguage {
        case .korean:
            let cleanKo = DatabaseRepository.cleanDisplayName(row.nameKo)
            displayName = !cleanKo.isEmpty ? cleanKo : (!row.nameJa.isEmpty ? row.nameJa : "(이름 없음)")
        case .japanese:
            displayName = !row.nameJa.isEmpty ? row.nameJa : (!row.nameKo.isEmpty ? DatabaseRepository.cleanDisplayName(row.nameKo) : "(이름 없음)")
        }
        if !row.cardNumber.isEmpty {
            return "\(row.cardNumber) | \(displayName)"
        }
        return displayName
    }

    private var deckListLayout: some View {
        VStack(spacing: 8) {
            ZStack {
                HStack(spacing: 8) {
                    ModernActionButton("뒤로", compact: true) { showingDeckList = false }
                    ModernActionButton("가져오기", compact: true) {
                        deckImportText = ""
                        showingDeckImportSheet = true
                    }
                    Spacer()
                    ModernIconButton(systemName: "plus", accessibilityLabel: "덱 추가") {
                        deckTitle = "새 덱"
                        deckEntries = []
                        editingDeckID = nil
                        openDeckBuilder()
                    }
                }
                Text("덱 리스트")
                    .font(.headline.weight(.bold))
                    .frame(maxWidth: .infinity, alignment: .center)
                    .allowsHitTesting(false)
            }
            List {
                ForEach(savedDecks) { deck in
                    HStack(spacing: 10) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(deck.title).bold()
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 8) {
                                    ForEach(deck.entries.prefix(8)) { entry in
                                        deckThumbnail(
                                            url: entry.effectiveImageUrl,
                                            qty: entry.qty,
                                            width: 42,
                                            height: 58
                                        )
                                    }
                                }
                            }
                        }
                        .contentShape(Rectangle())
                        .onTapGesture {
                            editingDeckID = deck.id
                            deckTitle = deck.title
                            deckEntries = deck.entries
                            openDeckBuilder()
                        }
                        Spacer()
                        Menu {
                            Button("이름 수정") {
                                startRenameDeck(deck)
                            }
                            Menu("코드로 내보내기") {
                                Button("홀로듀얼 코드") {
                                    exportHoloDuelCodeToClipboard(deck)
                                }
                                Button("홀로델타 .json 파일") {
                                    exportHoloDeltaCodeToClipboard(deck)
                                }
                                Button("부시나비 코드") {
                                    exportBushiroadCodeToClipboard(deck)
                                }
                            }
                            Button("이미지로 내보내기") {
                                exportDeckImage(deck)
                            }
                            Button("삭제", role: .destructive) {
                                removeDeck(deck.id)
                            }
                        } label: {
                            Image(systemName: "ellipsis.circle")
                                .padding(.vertical, 8)
                                .padding(.leading, 8)
                        }
                    }
                }
            }
            .listStyle(.plain)
        }
        .padding(10)
    }

    private var deckEditorLayout: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                ModernActionButton("취소", compact: true) { showingDeckEditor = false }
                TextField("덱 이름", text: $deckTitle)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).stroke(Color(.separator), lineWidth: 1))
                ModernActionButton("덱 목록", compact: true) {
                    showingDeckEditor = false
                    showingDeckList = true
                }
                ModernActionButton("저장", compact: true) {
                    let normalized = deckEntries
                        .filter { $0.qty > 0 }
                        .map {
                            DeckEntryState(
                                id: $0.id,
                                card: $0.card,
                                qty: $0.qty,
                                maxPerCard: $0.maxPerCard,
                                selectedRarity: $0.selectedRarity
                            )
                        }
                    let targetID = editingDeckID ?? UUID()
                    let snapshot = SavedDeckState(
                        id: targetID,
                        title: deckTitle.isEmpty ? "덱" : deckTitle,
                        entries: normalized
                    )
                    if let idx = savedDecks.firstIndex(where: { $0.id == targetID }) {
                        savedDecks[idx] = snapshot
                    } else {
                        savedDecks.append(snapshot)
                    }
                    editingDeckID = targetID
                    persistSavedDecks()
                    showingDeckEditor = false
                    showingDeckList = true
                }
            }
            HStack {
                Text("오시 \(deckOshiCount)/1")
                Text("옐 \(deckYellCount)/20")
                Text("덱 \(deckMainCount)/50")
                Text("합계 \(deckTotalCount)")
                Spacer()
            }
            .font(.footnote)

            HStack(spacing: 8) {
                TextField("카드 검색", text: $deckSearchQuery)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).stroke(Color(.separator), lineWidth: 1))
                    .onChange(of: deckSearchQuery) { _ in
                        Task { deckCandidates = await viewModel.searchDeckCards(deckSearchQuery) }
                    }
                Button(action: dismissKeyboard) {
                    Image(systemName: "keyboard.chevron.compact.down")
                        .foregroundColor(.secondary)
                        .padding(8)
                        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                }
            }

            panel(height: 280) {
                if deckCandidates.isEmpty {
                    Text("검색 결과가 없습니다.")
                        .foregroundColor(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 4) {
                            ForEach(deckCandidates) { card in
                                let qty = deckQuantity(for: card)
                                let maxQty = deckEntries.first(where: { $0.id == card.printId })?.maxPerCard ?? maxPerCard(card)
                                let blockedReason = blockReason(for: card)
                                Button {
                                    addCardToDeck(card)
                                } label: {
                                    HStack(spacing: 8) {
                                        deckThumbnail(
                                            url: card.selectableIllustrations.first?.imageUrl ?? card.imageUrl,
                                            qty: qty,
                                            width: 36,
                                            height: 50
                                        )
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text("\(card.cardNumber) | \((card.nameKo.isEmpty ? card.nameJa : card.nameKo))")
                                                .lineLimit(1)
                                            // 복수 레어리티 카드에는 선택 가능한 레어리티 칩 표시
                                            if card.hasMultipleRarities {
                                                HStack(spacing: 4) {
                                                    ForEach(card.selectableIllustrations) { option in
                                                        let isSelected = option.rarity == (deckEntries.first(where: { $0.id == card.printId })?.displayRarity ?? card.selectableIllustrations.first?.rarity ?? "")
                                                        Text(option.rarity)
                                                            .font(.caption2.bold())
                                                            .padding(.horizontal, 6).padding(.vertical, 2)
                                                            .background(isSelected ? Color.accentColor : Color.secondary.opacity(0.2))
                                                            .foregroundColor(isSelected ? .white : .primary)
                                                            .clipShape(Capsule())
                                                    }
                                                }
                                            } else {
                                                let rarity = (card.selectableIllustrations.first?.rarity ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                                                if !rarity.isEmpty {
                                                    Text("레어리티 \(rarity)")
                                                        .font(.caption2)
                                                        .foregroundColor(.secondary)
                                                }
                                            }
                                        }
                                        Spacer()
                                        Text(maxQty == Int.max ? "\(qty)/∞" : "\(qty)/\(maxQty)")
                                            .font(.caption2.monospacedDigit())
                                            .foregroundColor(blockedReason == nil ? .secondary : .orange)
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 4)
                                }
                                .buttonStyle(.plain)
                                .opacity(blockedReason == nil ? 1 : 0.45)
                            }
                        }
                    }
                    .simultaneousGesture(DragGesture(), including: .all)
                }
            }

            Text("선택 카드")
                .font(.headline)

            ScrollView {
                VStack(spacing: 8) {
                    ForEach(deckEntries.indices, id: \.self) { i in
                        HStack {
                            deckThumbnail(
                                url: deckEntries[i].effectiveImageUrl,
                                qty: deckEntries[i].qty,
                                width: 50,
                                height: 70
                            )
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(deckEntries[i].card.cardNumber) | \((deckEntries[i].card.nameKo.isEmpty ? deckEntries[i].card.nameJa : deckEntries[i].card.nameKo))")
                                    .lineLimit(1)
                                // 복수 레어리티이면 변경 버튼 표시
                                if deckEntries[i].card.hasMultipleRarities {
                                    Button {
                                        pendingRarityChangeEntryId = deckEntries[i].id
                                        pendingCardForRarity = deckEntries[i].card
                                    } label: {
                                        HStack(spacing: 4) {
                                            Text(deckEntries[i].displayRarity)
                                                .font(.caption2.bold())
                                            Image(systemName: "chevron.down")
                                                .font(.caption2)
                                        }
                                        .padding(.horizontal, 6).padding(.vertical, 2)
                                        .background(Color.accentColor.opacity(0.15))
                                        .foregroundColor(.accentColor)
                                        .clipShape(Capsule())
                                    }
                                    .buttonStyle(.plain)
                                } else {
                                    let r = deckEntries[i].displayRarity
                                    if !r.isEmpty {
                                        Text(r).font(.caption2).foregroundColor(.secondary)
                                    }
                                }
                            }
                            Spacer()
                            Button("-") { deckEntries[i].qty -= 1; if deckEntries[i].qty <= 0 { deckEntries.remove(at: i) } }
                            Button("+") {
                                let card = deckEntries[i].card
                                if let reason = blockReason(for: card) {
                                    showDeckToast(reason)
                                } else {
                                    deckEntries[i].qty += 1
                                }
                            }
                        }
                    }
                }
            }
        }
        .padding(10)
        .task(id: showingDeckEditor) {
            guard showingDeckEditor else { return }
            deckCandidates = await viewModel.searchDeckCards(deckSearchQuery)
        }
    }

    private func dismissKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }

    // MARK: - Multi-word tag helpers

    private static let mwPlaceholder = "\u{FFFF}"

    // Korean multi-word tag patterns (regex fragments)
    private static let koMwTagPatterns = [
        "#ID\\s+\\d+기생",     // #ID 1기생, #ID 2기생, #ID 3기생
        "#[^\\s#]+['’]s\\s+[^\\s#]+", // #시라카미's 캐릭터
        "#비밀\\s+결사\\s+[Hh]oloX", // #비밀 결사 holoX
        "#FLOW\\s+GLOW", // #FLOW GLOW
    ]

    private func buildTagTokenRegex(multiWordTags: [String]) -> NSRegularExpression {
        var parts: [String] = []
        for tag in multiWordTags {
            parts.append(NSRegularExpression.escapedPattern(for: tag))
        }
        for pat in Self.koMwTagPatterns {
            parts.append(pat)
        }
        parts.append("#[^\\s#]+")
        let pattern = parts.joined(separator: "|")
        return (try? NSRegularExpression(pattern: pattern)) ?? tagTokenRegex
    }

    private func protectMultiWordTags(_ text: String, tags: [String]) -> String {
        var result = text
        for tag in tags {
            result = result.replacingOccurrences(of: tag, with: tag.replacingOccurrences(of: " ", with: Self.mwPlaceholder))
        }
        // Also protect Korean multi-word tag patterns
        for regex in koMwTagCompiledPatterns {
            let nsRange = NSRange(result.startIndex..., in: result)
            let matches = regex.matches(in: result, range: nsRange).reversed()
            for match in matches {
                if let range = Range(match.range, in: result) {
                    let matched = String(result[range])
                    result = result.replacingCharacters(in: range, with: matched.replacingOccurrences(of: " ", with: Self.mwPlaceholder))
                }
            }
        }
        return result
    }

    private func restoreMultiWordTags(_ text: String) -> String {
        text.replacingOccurrences(of: Self.mwPlaceholder, with: " ")
    }
}

private struct MenuSheet: View {
    let state: HocgUiState
    @Binding var themeMode: AppThemeMode
    @Binding var preferredLanguage: PreferredLanguage
    let onBulkImageDownload: () -> Void
    let onManualUpdate: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    ModernActionButton("이미지 일괄 다운로드 (오프라인)", maxWidth: true) {
                        onBulkImageDownload()
                    }
                    .disabled(state.updateRunning)
                    .listRowBackground(Color.clear)

                    ModernActionButton("DB 수동갱신", maxWidth: true, action: onManualUpdate)
                        .disabled(state.updateRunning)
                        .listRowBackground(Color.clear)
                }

                Section("테마") {
                    Picker(selection: $themeMode) {
                        ForEach(AppThemeMode.allCases) { mode in
                            Text(mode.label).tag(mode)
                        }
                    } label: {
                        EmptyView()
                    }
                    .labelsHidden()
                    .pickerStyle(.inline)
                }

                Section("선호 언어") {
                    Picker(selection: $preferredLanguage) {
                        ForEach(PreferredLanguage.allCases) { language in
                            Text(language.label).tag(language)
                        }
                    } label: {
                        EmptyView()
                    }
                    .labelsHidden()
                    .pickerStyle(.inline)
                }

                Section("About") {
                    Text("Deck conversion uses hocg-deck-convert.")
                        .font(.footnote)
                    Text("Licensed under MIT.")
                        .font(.footnote)
                        .foregroundColor(.secondary)
                    Link("hocg-deck-convert GitHub", destination: URL(string: "https://github.com/Qrimpuff/hocg-deck-convert")!)
                    Link("MIT License", destination: URL(string: "https://github.com/Qrimpuff/hocg-deck-convert/blob/main/LICENSE")!)
                }
            }
            .navigationTitle("메뉴")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

// MARK: - 레어리티 선택 시트

private struct RarityPickerSheet: View {
    let card: DeckCardCandidate
    let currentRarity: String
    let onSelect: (String) -> Void
    let onCancel: () -> Void

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Text(card.nameKo.isEmpty ? card.nameJa : card.nameKo)
                    .font(.headline)
                    .padding(.vertical, 8)
                Text("레어리티를 선택하세요")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.bottom, 12)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(card.selectableIllustrations) { option in
                            RarityOptionCell(
                                option: option,
                                fallbackImageUrl: card.imageUrl,
                                isSelected: option.rarity == currentRarity,
                                onTap: { onSelect(option.rarity) }
                            )
                        }
                    }
                    .padding(.horizontal, 16)
                }
            }
            .padding(.vertical, 12)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("취소", action: onCancel)
                }
            }
        }
    }
}

private struct RarityOptionCell: View {
    let option: IllustrationOption
    let fallbackImageUrl: String
    let isSelected: Bool
    let onTap: () -> Void

    private var imageUrl: URL? {
        let raw = option.imageUrl.isEmpty ? fallbackImageUrl : option.imageUrl
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed)
    }

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 6) {
                if let imageUrl {
                    AsyncImage(url: imageUrl) { phase in
                        switch phase {
                        case .success(let image):
                            image.resizable().aspectRatio(400.0/558.0, contentMode: .fit)
                        case .failure:
                            Rectangle()
                                .fill(Color.secondary.opacity(0.2))
                                .aspectRatio(400.0/558.0, contentMode: .fit)
                                .overlay(
                                    Image(systemName: "photo.badge.exclamationmark")
                                        .foregroundColor(.secondary)
                                )
                        case .empty:
                            Rectangle()
                                .fill(Color.secondary.opacity(0.2))
                                .aspectRatio(400.0/558.0, contentMode: .fit)
                                .overlay(ProgressView())
                        @unknown default:
                            Rectangle()
                                .fill(Color.secondary.opacity(0.2))
                                .aspectRatio(400.0/558.0, contentMode: .fit)
                                .overlay(
                                    Image(systemName: "photo")
                                        .foregroundColor(.secondary)
                                )
                        }
                    }
                    .frame(width: 100)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 3)
                    )
                } else {
                    Rectangle()
                        .fill(Color.secondary.opacity(0.2))
                        .aspectRatio(400.0/558.0, contentMode: .fit)
                        .frame(width: 100)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                        .overlay(
                            Image(systemName: "photo")
                                .foregroundColor(.secondary)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 3)
                        )
                }

                Text(option.rarity)
                    .font(.caption.bold())
                    .foregroundColor(isSelected ? .accentColor : .primary)

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.accentColor)
                        .font(.caption)
                }
            }
        }
        .buttonStyle(.plain)
    }
}


private struct ModernActionButton: View {
    let title: String
    var compact: Bool = false
    var maxWidth: Bool = false
    let action: () -> Void

    init(_ title: String, compact: Bool = false, maxWidth: Bool = false, action: @escaping () -> Void) {
        self.title = title
        self.compact = compact
        self.maxWidth = maxWidth
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            Text(title)
                .font((compact ? Font.caption : Font.subheadline).weight(.semibold))
                .lineLimit(1)
                .minimumScaleFactor(0.82)
                .foregroundColor(.white)
                .padding(.horizontal, compact ? 10 : 14)
                .padding(.vertical, compact ? 7 : 10)
                .frame(maxWidth: maxWidth ? .infinity : nil)
                .background(Color.blue.opacity(0.22), in: RoundedRectangle(cornerRadius: compact ? 9 : 12, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: compact ? 9 : 12, style: .continuous)
                        .stroke(Color.blue.opacity(0.20), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
    }
}

private struct ModernIconButton: View {
    let systemName: String
    let accessibilityLabel: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.headline.weight(.semibold))
                .foregroundColor(.white)
                .frame(width: 34, height: 34)
                .background(Color.blue.opacity(0.22), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(Color.blue.opacity(0.20), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabel)
    }
}

private struct ActivityShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

private extension Int {
    func positiveModulo(_ modulus: Int) -> Int {
        ((self % modulus) + modulus) % modulus
    }
}

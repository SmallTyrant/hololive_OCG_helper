import SwiftUI
import UIKit
import Foundation

private let sectionLabels: [String] = [
    "SP 오시 스킬",
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
    pattern: "SP 오시 스킬|오시 스킬|콜라보 이펙트|블룸 이펙트|기프트|엑스트라|아츠(?=\\s+(?![+\\-]\\d)\\S)|#"
)
private let jaSectionMarkerRegex = try! NSRegularExpression(
    pattern: "SP推しスキル|推しスキル|コラボエフェクト|ブルームエフェクト|ギフト|エクストラ|アーツ(?=\\s+(?![+\\-]\\d)\\S)|カードタイプ|タグ|レアリティ|能力テキスト|バトンタッチ|#"
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
    ("\\s*(?<!SP )오시 스킬\\s*", "\n오시 스킬\n"),
    ("\\s*콜라보 이펙트\\s*", "\n콜라보 이펙트\n"),
    ("\\s*기프트\\s*", "\n기프트\n"),
    ("\\s*엑스트라\\s*", "\n엑스트라\n"),
    ("\\s*아츠(?=\\s+(?![+\\-]\\d)\\S)\\s*", "\n아츠\n"),
    ("\\s+#", "\n#"),
]
private let jaLineBreakRules: [(String, String)] = [
    ("\\s*SP推しスキル\\s*", "\nSP推しスキル\n"),
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
    @State private var koExpanded = true
    @State private var jaExpanded = false
    @State private var showingDeckList = false
    @State private var showingDeckEditor = false
    @State private var showingCardPicker = false
    @State private var deckTitle = "새 덱"
    @State private var deckEntries: [DeckEntryState] = []
    @State private var savedDecks: [SavedDeckState] = []
    @State private var deckSearchQuery = ""
    @State private var deckCandidates: [DeckCardCandidate] = []
    @State private var multiWordTags: [String] = []
    @AppStorage("theme_mode") private var themeModeRawValue: String = AppThemeMode.system.rawValue
    @AppStorage("preferred_language") private var preferredLanguageRawValue: String = PreferredLanguage.defaultFromSystem.rawValue

    private struct DeckEntryState: Identifiable {
        let id: Int64
        let card: DeckCardCandidate
        var qty: Int
        let maxPerCard: Int
    }

    private struct SavedDeckState: Identifiable {
        let id = UUID()
        var title: String
        var entries: [DeckEntryState]
    }

    private func isOshi(_ card: DeckCardCandidate) -> Bool {
        card.cardType.contains("오시") || card.cardType.contains("推し")
    }

    private func isYell(_ card: DeckCardCandidate) -> Bool {
        let c = card.color.lowercased()
        let t = card.cardType.lowercased()
        return c.contains("옐") || c.contains("yell") || c.contains("エール") || t.contains("yell")
    }

    private func maxPerCard(_ card: DeckCardCandidate) -> Int {
        if isOshi(card) { return 1 }
        if card.koText.contains("리미티드") || card.koText.lowercased().contains("limited") { return 1 }
        let patterns = ["(\\d+)장만", "최대\\s*(\\d+)장", "(\\d+)장까지"]
        for p in patterns {
            if let regex = try? NSRegularExpression(pattern: p), let match = regex.firstMatch(in: card.koText, range: NSRange(location: 0, length: card.koText.utf16.count)), let r = Range(match.range(at: 1), in: card.koText), let n = Int(card.koText[r]) { return max(1, n) }
        }
        return 4
    }

    private func canAddToDeck(_ card: DeckCardCandidate) -> Bool {
        let oshi = deckEntries.filter { isOshi($0.card) }.map(\.qty).reduce(0, +)
        let yell = deckEntries.filter { isYell($0.card) }.map(\.qty).reduce(0, +)
        let main = deckEntries.filter { !isOshi($0.card) && !isYell($0.card) }.map(\.qty).reduce(0, +)
        if isOshi(card) { return oshi < 1 }
        if isYell(card) { return yell < 20 }
        return main < 50
    }

    var body: some View {
        GeometryReader { geo in
            let isMobileLayout = geo.size.width < 900

            ZStack(alignment: .top) {
                if showingDeckList {
                    deckListLayout
                } else if showingDeckEditor {
                    deckEditorLayout
                } else if isMobileLayout {
                    mobileLayout(screenHeight: geo.size.height)
                } else {
                    desktopLayout()
                }

                if let toast = viewModel.toastMessage {
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
            .simultaneousGesture(
                DragGesture(minimumDistance: 0).onChanged { _ in
                    dismissKeyboard()
                },
                including: .all
            )
            .sheet(isPresented: Binding(
                get: { showingMenu && isMobileLayout },
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
                Text("DB 업데이트가 있습니다. 업데이트 하시겠습니까?\n로컬 DB 날짜: \(dialog.localDate ?? "없음")\nGitHub DB 날짜: \(dialog.remoteDate)")
            }
            .onChange(of: viewModel.state.detailKoText) { _ in
                resetDetailExpansion()
            }
            .onChange(of: viewModel.state.detailJaText) { _ in
                resetDetailExpansion()
            }
            .onChange(of: preferredLanguageRawValue) { _ in
                resetDetailExpansion()
            }
            .animation(.easeInOut(duration: 0.2), value: viewModel.toastMessage)
            .task {
                let tags = await Task.detached {
                    DatabaseRepository(paths: AppPaths()).loadMultiWordTags()
                }.value
                multiWordTags = tags
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
        let koLines = splitDetailLines(viewModel.state.detailKoText, language: .korean)
        let jaLines = splitDetailLines(viewModel.state.detailJaText, language: .japanese)
        let hasKo = !koLines.isEmpty
        let hasJa = !jaLines.isEmpty

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
                    .textFieldStyle(.roundedBorder)
                    .disabled(viewModel.state.updateRunning)

                    Button {
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
                    Button(viewModel.state.imageCollapsed ? "이미지 펼치기" : "이미지 접기") {
                        viewModel.onToggleImagePanel()
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.blue)
                }

                if viewModel.state.imageCollapsed {
                    Text("이미지를 접었습니다.")
                        .font(.footnote)
                        .foregroundColor(.secondary)
                } else {
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

    private func desktopLayout() -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                TextField(
                    "DB",
                    text: .constant(viewModel.state.dbPath)
                )
                .textFieldStyle(.roundedBorder)
                .disabled(true)

                if viewModel.state.updateRunning {
                    ProgressView()
                        .controlSize(.small)
                }
            }

            TextField(
                "카드번호 / 이름 / 태그 / 한국어 본문 검색",
                text: Binding(
                    get: { viewModel.state.searchQuery },
                    set: { viewModel.onSearchQueryChanged($0) }
                )
            )
            .textFieldStyle(.roundedBorder)
            .disabled(viewModel.state.updateRunning)

            updateStatusBlock
            Divider()

            GeometryReader { bodyGeo in
                let totalWidth = max(bodyGeo.size.width - 2, 0)
                let leftWidth = totalWidth * (3.0 / 13.0)
                let middleWidth = totalWidth * (6.0 / 13.0)
                let rightWidth = totalWidth * (4.0 / 13.0)

                HStack(spacing: 0) {
                    desktopColumn(title: "목록", width: leftWidth) {
                        resultsList
                    }

                    Rectangle()
                        .fill(Color.secondary.opacity(0.35))
                        .frame(width: 1)

                    desktopColumn(title: "이미지", width: middleWidth) {
                        imagePanel
                    }

                    Rectangle()
                        .fill(Color.secondary.opacity(0.35))
                        .frame(width: 1)

                    desktopColumn(title: "효과", width: rightWidth) {
                        detailPanel(scrollable: true)
                    }
                }
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
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

    private func desktopColumn<Content: View>(title: String, width: CGFloat, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(title)
                .font(.headline)
                .padding(.leading, 10)
                .padding(.top, 4)

            panel(height: nil, fillHeight: true) {
                content()
            }
            .frame(maxHeight: .infinity)
        }
        .frame(width: width, alignment: .topLeading)
        .frame(maxHeight: .infinity, alignment: .topLeading)
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
                            let title = resultTitle(row)
                            Text(title)
                                .font(.body)
                                .lineLimit(1)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 9)
                                .background(
                                    (viewModel.state.selectedPrintId == row.printId
                                        ? Color.blue.opacity(0.20)
                                        : Color.clear),
                                    in: RoundedRectangle(cornerRadius: 8),
                                )
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    viewModel.onSelectPrint(row.printId)
                                }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    @ViewBuilder
    private var imagePanel: some View {
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

    private func detailPanel(scrollable: Bool) -> some View {
        let koLines = splitDetailLines(viewModel.state.detailKoText, language: .korean)
        let jaLines = splitDetailLines(viewModel.state.detailJaText, language: .japanese)

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
        guard let regex = try? NSRegularExpression(pattern: detailPrefixPattern) else {
            return trimmed
        }
        let range = NSRange(location: 0, length: trimmed.utf16.count)
        return regex.stringByReplacingMatches(in: trimmed, range: range, withTemplate: "")
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

        var expanded: [String] = []
        for line in lines {
            guard line.contains("#") else {
                expanded.append(line)
                continue
            }

            // Japanese tag boundary: split at を after tag
            if let jaMatch = jaTagObjectSplit(line) {
                expanded.append(tagLabel)
                expanded.append(normalizeInlineWhitespace(jaMatch.tag))
                let tail = normalizeInlineWhitespace(jaMatch.rest)
                if !tail.isEmpty {
                    if tail.contains("#") {
                        expanded.append(contentsOf: expandTagLinesHelper([tail], tagLabel: tagLabel))
                    } else {
                        expanded.append(tail)
                    }
                }
                continue
            }

            guard let hashIndex = line.firstIndex(of: "#"), hashIndex != line.startIndex else {
                expanded.append(line)
                continue
            }

            let prefix = normalizeInlineWhitespace(String(line[..<hashIndex]))
            let tagText = normalizeInlineWhitespace(String(line[hashIndex...]))

            // Check if the tag portion has a Japanese boundary
            if let jaMatch = jaTagObjectSplit(tagText) {
                if !prefix.isEmpty { expanded.append(prefix) }
                expanded.append(tagLabel)
                expanded.append(normalizeInlineWhitespace(jaMatch.tag))
                let tail = normalizeInlineWhitespace(jaMatch.rest)
                if !tail.isEmpty {
                    if tail.contains("#") {
                        expanded.append(contentsOf: expandTagLinesHelper([tail], tagLabel: tagLabel))
                    } else {
                        expanded.append(tail)
                    }
                }
            } else {
                if !prefix.isEmpty { expanded.append(prefix) }
                if !tagText.isEmpty { expanded.append(tagText) }
            }
        }

        let markerIndex = expanded.firstIndex(where: { splitSectionLabel($0) != nil })
        let trimmed = markerIndex.map { Array(expanded[$0...]) } ?? expanded
        let filtered = trimmed.filter { !isNoiseMetadataLine($0, metadataTokens: metadataTokens) }

        var result: [String] = []
        for line in filtered {
            if line.hasPrefix("#") {
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
                return AnyView(sectionChip(label))
            }
            return AnyView(
                VStack(alignment: .leading, spacing: 4) {
                    sectionChip(label)
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
        let tagRegex = buildTagTokenRegex(multiWordTags: multiWordTags)
        let pattern = "\(tagRegex.pattern)|블룸 이펙트|ブルームエフェクト"
        let regex = (try? NSRegularExpression(pattern: pattern)) ?? tagRegex

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
            let rest = String(trimmed.dropFirst(label.count)).trimmingCharacters(in: .whitespacesAndNewlines)
            if rest.isEmpty {
                return (label, "")
            }
            if separators.contains(where: { rest.hasPrefix($0) }) {
                return (label, rest)
            }
        }
        return nil
    }

    /// Japanese tag-object boundary: split `#TAG を...` into (tag, rest)
    private func jaTagObjectSplit(_ text: String) -> (tag: String, rest: String)? {
        guard let regex = try? NSRegularExpression(pattern: "^(#[^\\s#を]+(?:\\s+[^\\s#を]+)*)(を.+)$") else {
            return nil
        }
        let nsText = text as NSString
        let range = NSRange(location: 0, length: nsText.length)
        guard let match = regex.firstMatch(in: text, range: range), match.numberOfRanges == 3 else {
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

    private func firstSectionRange(in text: String, regex: NSRegularExpression) -> Range<String.Index>? {
        let range = NSRange(text.startIndex..., in: text)
        guard let match = regex.firstMatch(in: text, options: [], range: range) else {
            return nil
        }
        return Range(match.range, in: text)
    }

    private func matchesDetailPrefix(_ text: String) -> Bool {
        guard let regex = try? NSRegularExpression(pattern: detailPrefixPattern) else {
            return false
        }
        let range = NSRange(text.startIndex..., in: text)
        guard let match = regex.firstMatch(in: text, options: [], range: range) else {
            return false
        }
        return match.range.location == 0
    }

    private func normalizeTagLine(_ line: String) -> String {
        let dynamicRegex = buildTagTokenRegex(multiWordTags: multiWordTags)
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
        let scalarPattern = "^(hp\\s*\\d{2,3}|(1st|2nd)\\s*\\d{2,3})$"
        if lowered.range(of: scalarPattern, options: .regularExpression) != nil {
            return true
        }

        let tokens = lowered.split(separator: " ").map(String.init)
        if !tokens.isEmpty && tokens.allSatisfy({ token in
            metadataTokens.contains(token) || token.range(of: "^\\d{2,3}$", options: .regularExpression) != nil
        }) {
            return true
        }

        return false
    }

    private func tagStyledText(_ line: String) -> Text {
        let dynamicRegex = buildTagTokenRegex(multiWordTags: multiWordTags)
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
            HStack {
                Button("뒤로") { showingDeckList = false }
                Spacer()
                Text("덱 리스트").font(.headline)
                Spacer()
                Button {
                    deckTitle = "새 덱"
                    deckEntries = []
                    showingDeckList = false
                    showingDeckEditor = true
                } label: { Image(systemName: "plus") }
            }
            ScrollView {
                VStack(spacing: 8) {
                    ForEach(savedDecks) { deck in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(deck.title).bold()
                            ForEach(deck.entries.prefix(5)) { e in
                                HStack {
                                    AsyncImage(url: URL(string: e.card.imageUrl)) { phase in remotePhaseView(phase) }
                                        .frame(width: 42, height: 58)
                                    Text("x \(e.qty)")
                                }
                            }
                        }
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.secondary.opacity(0.3)))
                        .onTapGesture {
                            deckTitle = deck.title
                            deckEntries = deck.entries
                            showingDeckList = false
                            showingDeckEditor = true
                        }
                    }
                }
            }
        }.padding(10)
    }

    private var deckEditorLayout: some View {
        VStack(spacing: 8) {
            HStack {
                Button("취소") { showingDeckEditor = false }
                TextField("덱 이름", text: $deckTitle).textFieldStyle(.roundedBorder)
                Button("저장") {
                    savedDecks.removeAll { $0.title == deckTitle }
                    savedDecks.append(SavedDeckState(title: deckTitle.isEmpty ? "덱" : deckTitle, entries: deckEntries))
                    showingDeckEditor = false
                    showingDeckList = true
                }
            }
            HStack {
                Text("오시 \(deckEntries.filter { isOshi($0.card) }.map(\.qty).reduce(0,+))/1")
                Text("옐 \(deckEntries.filter { isYell($0.card) }.map(\.qty).reduce(0,+))/20")
                Text("기타 \(deckEntries.filter { !isOshi($0.card) && !isYell($0.card) }.map(\.qty).reduce(0,+))/50")
                Spacer()
                Button { showingCardPicker = true; Task { deckCandidates = await viewModel.searchDeckCards(deckSearchQuery) } } label: { Image(systemName: "plus") }
            }
            ScrollView {
                VStack(spacing: 8) {
                    ForEach(deckEntries.indices, id: \.self) { i in
                        HStack {
                            AsyncImage(url: URL(string: deckEntries[i].card.imageUrl)) { phase in remotePhaseView(phase) }.frame(width: 50, height: 70)
                            Text("\(deckEntries[i].card.cardNumber) | \((deckEntries[i].card.nameKo.isEmpty ? deckEntries[i].card.nameJa : deckEntries[i].card.nameKo)) x \(deckEntries[i].qty)")
                            Spacer()
                            Button("-") { deckEntries[i].qty -= 1; if deckEntries[i].qty <= 0 { deckEntries.remove(at: i) } }
                            Button("+") {
                                if deckEntries[i].qty < deckEntries[i].maxPerCard && canAddToDeck(deckEntries[i].card) {
                                    deckEntries[i].qty += 1
                                }
                            }
                        }
                    }
                }
            }
        }
        .padding(10)
        .sheet(isPresented: $showingCardPicker) {
            NavigationStack {
                VStack {
                    TextField("카드 검색", text: $deckSearchQuery)
                        .textFieldStyle(.roundedBorder)
                        .onChange(of: deckSearchQuery) { _ in Task { deckCandidates = await viewModel.searchDeckCards(deckSearchQuery) } }
                    List(deckCandidates) { card in
                        Button {
                            if let idx = deckEntries.firstIndex(where: { $0.id == card.printId }) {
                                if deckEntries[idx].qty < deckEntries[idx].maxPerCard && canAddToDeck(deckEntries[idx].card) {
                                    deckEntries[idx].qty += 1
                                }
                            } else {
                                if canAddToDeck(card) {
                                    deckEntries.append(DeckEntryState(id: card.printId, card: card, qty: 1, maxPerCard: maxPerCard(card)))
                                }
                            }
                        } label: {
                            HStack {
                                AsyncImage(url: URL(string: card.imageUrl)) { phase in remotePhaseView(phase) }.frame(width: 34, height: 46)
                                Text("\(card.cardNumber) | \((card.nameKo.isEmpty ? card.nameJa : card.nameKo))")
                            }
                        }
                    }
                }
                .padding(10)
                .navigationTitle("카드 선택")
            }
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
        for pat in Self.koMwTagPatterns {
            if let regex = try? NSRegularExpression(pattern: pat) {
                let nsRange = NSRange(result.startIndex..., in: result)
                let matches = regex.matches(in: result, range: nsRange).reversed()
                for match in matches {
                    if let range = Range(match.range, in: result) {
                        let matched = String(result[range])
                        result = result.replacingCharacters(in: range, with: matched.replacingOccurrences(of: " ", with: Self.mwPlaceholder))
                    }
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
                    Button("이미지 일괄 다운로드 (오프라인)") {
                        onBulkImageDownload()
                    }
                    .disabled(state.updateRunning)

                    Button("DB 수동갱신", action: onManualUpdate)
                        .disabled(state.updateRunning)
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
            }
            .navigationTitle("메뉴")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

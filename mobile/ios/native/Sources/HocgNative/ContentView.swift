import SwiftUI
import UIKit

private let sectionLabels: [String] = [
    "SP 오시 스킬",
    "오시 스킬",
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
    "レアリティ",
    "アーツ",
    "エクストラ",
    "Bloomレベル",
    "キーワード",
    "LIFE",
    "HP",
]
private let detailPrefixPattern = #"^(?:.+?)\s+(?:서포트|サポート)\s*[/／]\s*(?:아이템|스태프|이벤트|이벤타|アイテム|スタッフ|イベント)\s+"#

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
                        .foregroundStyle(.white)
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
                    },
                    onDeckList: {
                        showingMenu = false
                        showingDeckList = true
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
        let hasKo = !splitDetailLines(viewModel.state.detailKoText).isEmpty
        let hasJa = !splitDetailLines(viewModel.state.detailJaText).isEmpty

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
        let listHeight = scaledHeight(screenHeight: screenHeight, ratio: 0.30, minHeight: 190, maxHeight: 360)
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
                    .foregroundStyle(.blue)
                }

                if viewModel.state.imageCollapsed {
                    Text("이미지를 접었습니다.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
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
                    .foregroundStyle(viewModel.state.updateStatusError ? .red : .green)
            }

            if let message = viewModel.state.persistentMessage, !message.isEmpty {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.red)
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
                    .foregroundStyle(.secondary)
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
                    .foregroundStyle(.secondary)
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
        let koLines = splitDetailLines(viewModel.state.detailKoText)
        let jaLines = splitDetailLines(viewModel.state.detailJaText)

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
                Text("(본문 없음)")
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

    private func splitDetailLines(_ text: String) -> [String] {
        let lines = text
            .split(whereSeparator: { $0.isNewline })
            .map { sanitizeDetailLine(String($0)) }
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
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let regex = try? NSRegularExpression(pattern: detailPrefixPattern) else {
            return trimmed
        }
        let range = NSRange(location: 0, length: trimmed.utf16.count)
        return regex.stringByReplacingMatches(in: trimmed, range: range, withTemplate: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
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
                .foregroundStyle(.blue)
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

    private func placeholder(message: String, error: Bool) -> some View {
        VStack(spacing: 8) {
            Image(systemName: error ? "photo.badge.exclamationmark" : "photo")
                .font(.system(size: 28))
                .foregroundStyle(.secondary)
            Text(message)
                .font(.footnote)
                .foregroundStyle(.secondary)
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

        return AnyView(
            highlightedTagText(line)
                .frame(maxWidth: .infinity, alignment: .leading)
        )
    }

    private func highlightedTagText(_ text: String) -> Text {
        let pattern = #"#[\p{L}\p{N}_]+"#
        guard let regex = try? NSRegularExpression(pattern: pattern) else {
            return Text(text)
        }

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
            result = result + Text(tag).foregroundStyle(.blue).fontWeight(.semibold)
            cursor = match.range.location + match.range.length
        }
        if cursor < ns.length {
            let tail = ns.substring(with: NSRange(location: cursor, length: ns.length - cursor))
            result = result + Text(tail)
        }
        return result
    }

    private func splitSectionLabel(_ line: String) -> (String, String)? {
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        let separators = [" ", ":", "：", "[", "(", "【"]
        for label in sectionLabels {
            if label == "태그" || label == "タグ" {
                continue
            }
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

    private func resultTitle(_ row: PrintRow) -> String {
        let displayName: String
        switch selectedPreferredLanguage {
        case .korean:
            displayName = !row.nameKo.isEmpty ? row.nameKo : (!row.nameJa.isEmpty ? row.nameJa : "(이름 없음)")
        case .japanese:
            displayName = !row.nameJa.isEmpty ? row.nameJa : (!row.nameKo.isEmpty ? row.nameKo : "(이름 없음)")
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
                Button { deckTitle = "새 덱"; deckEntries = []; showingDeckEditor = true } label: { Image(systemName: "plus") }
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
                        .onTapGesture { deckTitle = deck.title; deckEntries = deck.entries; showingDeckEditor = true }
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
                            Button("+") { if deckEntries[i].qty < deckEntries[i].maxPerCard { deckEntries[i].qty += 1 } }
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
                                if deckEntries[idx].qty < deckEntries[idx].maxPerCard { deckEntries[idx].qty += 1 }
                            } else {
                                deckEntries.append(DeckEntryState(id: card.printId, card: card, qty: 1, maxPerCard: maxPerCard(card)))
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
}

private struct MenuSheet: View {
    let state: HocgUiState
    @Binding var themeMode: AppThemeMode
    @Binding var preferredLanguage: PreferredLanguage
    let onBulkImageDownload: () -> Void
    let onManualUpdate: () -> Void
    let onDeckList: () -> Void

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

                    Button("덱리스트(테스트)", action: onDeckList)
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

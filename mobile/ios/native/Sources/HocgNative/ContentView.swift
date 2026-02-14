import SwiftUI
import UIKit

private let sectionLabels: [String] = [
    "カードタイプ",
    "タグ",
    "レアリティ",
    "推しスキル",
    "SP推しスキル",
    "アーツ",
    "エクストラ",
    "Bloomレベル",
    "キーワード",
    "LIFE",
    "HP",
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

struct ContentView: View {
    @StateObject private var viewModel = HocgViewModel()
    @State private var showingMenu = false
    @AppStorage("theme_mode") private var themeModeRawValue: String = AppThemeMode.system.rawValue

    var body: some View {
        GeometryReader { geo in
            let isMobileLayout = geo.size.width < 900

            ZStack(alignment: .top) {
                if isMobileLayout {
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
        let lines = viewModel.state.detailKoText
            .split(whereSeparator: { $0.isNewline })
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        return Group {
            if scrollable {
                ScrollView {
                    detailLinesView(lines: lines)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            } else {
                detailLinesView(lines: lines)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private func detailLinesView(lines: [String]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if lines.isEmpty {
                Text("(한국어 본문 없음)")
            } else {
                sectionChip("한국어")
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
        if sectionLabels.contains(line) {
            return AnyView(sectionChip(line))
        }

        if let label = sectionLabels.first(where: { line.hasPrefix("\($0) ") }) {
            let rest = String(line.dropFirst(label.count))
            return AnyView(
                (Text(label).bold() + Text(rest))
                    .frame(maxWidth: .infinity, alignment: .leading)
            )
        }

        return AnyView(
            Text(line)
                .frame(maxWidth: .infinity, alignment: .leading)
        )
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
        let displayName = !row.nameKo.isEmpty ? row.nameKo : (!row.nameJa.isEmpty ? row.nameJa : "(이름 없음)")
        if !row.cardNumber.isEmpty {
            return "\(row.cardNumber) | \(displayName)"
        }
        return displayName
    }

    private func dismissKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}

private struct MenuSheet: View {
    let state: HocgUiState
    @Binding var themeMode: AppThemeMode
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
            }
            .navigationTitle("메뉴")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

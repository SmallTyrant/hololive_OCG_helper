import SwiftUI

struct CardListView: View {
    @StateObject private var viewModel: CardListViewModel
    private let repository: CardRepository

    init(repository: CardRepository) {
        _viewModel = StateObject(wrappedValue: CardListViewModel(repository: repository))
        self.repository = repository
    }

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                TextField("카드번호 / 이름 / 태그", text: $viewModel.query)
                    .textFieldStyle(.roundedBorder)
                Button("검색") { viewModel.search() }
            }

            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage).foregroundStyle(.red)
            }

            List(viewModel.cards) { card in
                NavigationLink(card.cardNumber + "  " + card.nameJA) {
                    CardDetailView(viewModel: CardDetailViewModel(printID: card.id, repository: repository))
                }
            }
            .listStyle(.plain)

            Text("본 앱은 팬이 제작한 비공식 도우미이며, 카드 정보는 참고용입니다.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .navigationTitle("hOCG Helper")
    }
}

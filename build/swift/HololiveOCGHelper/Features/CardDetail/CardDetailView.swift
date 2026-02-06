import SwiftUI

struct CardDetailView: View {
    @StateObject private var viewModel: CardDetailViewModel

    init(viewModel: CardDetailViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                if let detail = viewModel.detail {
                    Text(detail.cardNumber).font(.headline)
                    Text(detail.nameKO.isEmpty ? detail.nameJA : detail.nameKO)
                        .font(.title3)
                    if let url = URL(string: detail.imageURL), !detail.imageURL.isEmpty {
                        AsyncImage(url: url) { image in
                            image.resizable().scaledToFit()
                        } placeholder: {
                            ProgressView()
                        }
                    }
                    Group {
                        Text("한국어 효과")
                            .font(.subheadline).bold()
                        Text(detail.effectTextKO.isEmpty ? "-" : detail.effectTextKO)
                        Divider()
                        Text("일본어 원문")
                            .font(.subheadline).bold()
                        Text(detail.rawTextJA.isEmpty ? "-" : detail.rawTextJA)
                    }
                } else if let errorMessage = viewModel.errorMessage {
                    Text(errorMessage).foregroundStyle(.red)
                } else {
                    ProgressView()
                }
            }
            .padding()
        }
        .navigationTitle("카드 상세")
        .onAppear { viewModel.load() }
    }
}

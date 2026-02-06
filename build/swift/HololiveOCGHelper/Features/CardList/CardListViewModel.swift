import Foundation

@MainActor
final class CardListViewModel: ObservableObject {
    @Published var query: String = ""
    @Published var cards: [CardSummary] = []
    @Published var errorMessage: String?

    private let repository: CardRepository

    init(repository: CardRepository) {
        self.repository = repository
    }

    func search() {
        do {
            cards = try repository.searchCards(keyword: query, limit: 50)
            errorMessage = nil
        } catch {
            errorMessage = "검색 중 오류가 발생했습니다: \(error.localizedDescription)"
        }
    }
}

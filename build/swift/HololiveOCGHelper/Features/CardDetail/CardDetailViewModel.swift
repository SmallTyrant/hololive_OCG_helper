import Foundation

@MainActor
final class CardDetailViewModel: ObservableObject {
    @Published var detail: CardDetail?
    @Published var errorMessage: String?

    private let printID: Int
    private let repository: CardRepository

    init(printID: Int, repository: CardRepository) {
        self.printID = printID
        self.repository = repository
    }

    func load() {
        do {
            detail = try repository.loadDetail(printID: printID)
            errorMessage = nil
        } catch {
            errorMessage = "상세 로딩 중 오류가 발생했습니다: \(error.localizedDescription)"
        }
    }
}

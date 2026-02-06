import Foundation

protocol CardRepository {
    func searchCards(keyword: String, limit: Int) throws -> [CardSummary]
    func loadDetail(printID: Int) throws -> CardDetail?
}

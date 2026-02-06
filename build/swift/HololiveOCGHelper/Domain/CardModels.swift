import Foundation

struct CardSummary: Identifiable, Equatable {
    let id: Int
    let cardNumber: String
    let nameJA: String
}

struct CardDetail: Equatable {
    let printID: Int
    let cardNumber: String
    let nameJA: String
    let nameKO: String
    let rawTextJA: String
    let effectTextKO: String
    let imageURL: String
}

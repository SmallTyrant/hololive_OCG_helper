import SwiftUI

final class AppState: ObservableObject {
    let repository: CardRepository

    init() {
        let databaseProvider = DatabaseProvider()
        repository = SQLiteCardRepository(databaseProvider: databaseProvider)
    }
}

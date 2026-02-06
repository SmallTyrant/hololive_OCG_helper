import SwiftUI

@main
struct HololiveOCGHelperApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                CardListView(repository: appState.repository)
            }
        }
    }
}

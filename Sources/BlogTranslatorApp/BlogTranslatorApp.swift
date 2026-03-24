import SwiftUI

@main
struct BlogTranslatorAppMain: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup("博文翻译助手") {
            RootView(model: model)
                .frame(minWidth: 1160, minHeight: 760)
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(after: .saveItem) {
                Button("保存当前文章") {
                    Task { await model.saveCurrentArticle() }
                }
                .keyboardShortcut("s")
            }
        }
    }
}

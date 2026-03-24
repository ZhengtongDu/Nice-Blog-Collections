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

            CommandMenu("操作") {
                Button("导出 HTML") {
                    Task { await model.exportCurrentArticleHTML() }
                }
                .keyboardShortcut("e")

                Button("复制公众号富文本") {
                    Task { await model.copyCurrentArticleRichText() }
                }
                .keyboardShortcut("c", modifiers: [.command, .shift])

                Button("刷新预览") {
                    model.previewReloadToken = UUID()
                }
                .keyboardShortcut("r")

                Divider()

                Button("Translate") {
                    model.selectedSection = .translate
                }
                .keyboardShortcut("1")

                Button("Library") {
                    model.selectedSection = .library
                }
                .keyboardShortcut("2")

                Button("Review Queue") {
                    model.selectedSection = .reviewQueue
                }
                .keyboardShortcut("3")

                Button("Settings") {
                    model.selectedSection = .settings
                }
                .keyboardShortcut("4")
            }
        }
    }
}

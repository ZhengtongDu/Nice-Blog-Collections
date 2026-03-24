import SwiftUI

struct RootView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        Group {
            if model.needsOnboarding {
                OnboardingView(model: model)
            } else {
                NavigationSplitView {
                    List(AppSection.allCases, selection: $model.selectedSection) { section in
                        Label(section.title, systemImage: section.systemImage)
                            .tag(section)
                    }
                    .navigationSplitViewColumnWidth(min: 180, ideal: 210)
                } detail: {
                    detailView
                        .toolbar {
                            if let message = model.transientMessage {
                                ToolbarItem(placement: .status) {
                                    Text(message)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                }
            }
        }
        .task {
            await model.bootstrap()
        }
        .alert(
            "发生错误",
            isPresented: Binding(
                get: { model.workerErrorMessage != nil },
                set: { newValue in
                    if !newValue {
                        model.workerErrorMessage = nil
                    }
                }
            )
        ) {
            Button("确定", role: .cancel) {
                model.workerErrorMessage = nil
            }
        } message: {
            Text(model.workerErrorMessage ?? "")
        }
    }

    @ViewBuilder
    private var detailView: some View {
        switch model.selectedSection ?? .translate {
        case .translate:
            TranslateWorkspaceView(model: model)
        case .library:
            ArticleWorkspaceView(model: model, kind: .library)
        case .reviewQueue:
            ArticleWorkspaceView(model: model, kind: .reviewQueue)
        case .settings:
            SettingsView(model: model)
        }
    }
}

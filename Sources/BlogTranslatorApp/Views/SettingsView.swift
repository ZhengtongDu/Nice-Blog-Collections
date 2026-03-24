import SwiftUI

struct SettingsView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                Text("Settings")
                    .font(.system(size: 30, weight: .bold, design: .rounded))

                HStack(spacing: 14) {
                    StatusBadge(title: model.health.workerReady ? "Worker Ready" : "Worker Waiting", tint: model.health.workerReady ? .green : .secondary)
                    StatusBadge(title: model.health.ollamaReachable ? "Ollama Connected" : "Ollama Offline", tint: model.health.ollamaReachable ? .green : .orange)
                    StatusBadge(title: model.health.modelInstalled ? "Model Installed" : "Model Missing", tint: model.health.modelInstalled ? .green : .orange)
                }

                settingsCard(title: "内容库") {
                    settingsValue(label: "Storage Root", value: model.health.storageRoot)
                    settingsValue(label: "Articles", value: model.health.articlesDir)
                    settingsValue(label: "Logs", value: model.health.logsDir)

                    HStack {
                        Button("重新选择内容库") {
                            model.chooseStorageRoot()
                        }
                        .buttonStyle(.borderedProminent)

                        Button("打开日志目录") {
                            model.openLogsFolder()
                        }
                        .buttonStyle(.bordered)
                    }
                }

                settingsCard(title: "运行诊断") {
                    Button("重新检查 Worker / Ollama / Model") {
                        Task {
                            do {
                                try await model.refreshHealth()
                            } catch {
                                model.workerErrorMessage = error.localizedDescription
                            }
                        }
                    }
                    .buttonStyle(.borderedProminent)

                    if let error = model.health.lastError, !error.isEmpty {
                        Text(error)
                            .foregroundStyle(.orange)
                    }
                }

                if let message = model.workerErrorMessage {
                    settingsCard(title: "最近错误") {
                        Text(message)
                            .foregroundStyle(.red)
                    }
                }
            }
            .padding(28)
        }
        .background(Color(red: 0.97, green: 0.95, blue: 0.91))
    }

    private func settingsCard<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title)
                .font(.headline)
            content()
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }

    private func settingsValue(label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value.isEmpty ? "—" : value)
                .textSelection(.enabled)
        }
    }
}

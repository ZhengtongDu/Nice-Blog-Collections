import SwiftUI

struct OnboardingView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        ZStack {
            Color(nsColor: .windowBackgroundColor)
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 24) {
                Text("博文翻译助手")
                    .font(.system(size: 38, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)

                Text("先选择一个内容库目录。应用会在里面管理 `articles/`、`logs/` 和导出的 HTML 文件。")
                    .font(.title3)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: 12) {
                    HealthChip(
                        title: "Worker",
                        value: model.health.workerReady ? "Ready" : "Waiting",
                        tint: model.health.workerReady ? .green : .secondary
                    )
                    HealthChip(
                        title: "Ollama",
                        value: model.health.ollamaReachable ? "Connected" : "Offline",
                        tint: model.health.ollamaReachable ? .green : .orange
                    )
                    HealthChip(
                        title: "Model",
                        value: model.health.modelInstalled ? "Installed" : "Missing",
                        tint: model.health.modelInstalled ? .green : .orange
                    )
                }

                if let error = model.health.lastError, !error.isEmpty {
                    Text(error)
                        .font(.callout)
                        .foregroundStyle(.orange)
                }

                Button("选择内容库") {
                    model.chooseStorageRoot()
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)

                if let message = model.workerErrorMessage {
                    Text(message)
                        .foregroundStyle(.red)
                }
            }
            .padding(36)
            .frame(maxWidth: 720)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 30, style: .continuous))
            .padding(40)
        }
    }
}

private struct HealthChip: View {
    let title: String
    let value: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.headline)
                .foregroundStyle(tint)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(nsColor: .controlBackgroundColor).opacity(0.65), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

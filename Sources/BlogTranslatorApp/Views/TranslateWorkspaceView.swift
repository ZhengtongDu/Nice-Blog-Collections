import SwiftUI

struct TranslateWorkspaceView: View {
    @ObservedObject var model: AppModel
    @State private var showLogs = true

    private let columns = [
        GridItem(.adaptive(minimum: 190), spacing: 16)
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 26) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Translate")
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                    Text("输入文章 URL，后台 Python worker 会负责抓取、翻译、润色和产物落盘。")
                        .font(.title3)
                        .foregroundStyle(.secondary)

                    HStack(spacing: 12) {
                        TextField("https://example.com/blog-post", text: $model.translationURL)
                            .textFieldStyle(.roundedBorder)
                            .font(.body.monospaced())

                        Button("开始翻译") {
                            Task { await model.startTranslation() }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(model.translationURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                        if model.activeJob?.state == "running" {
                            Button("取消") {
                                Task { await model.cancelTranslation() }
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
                .padding(26)
                .background(
                    LinearGradient(
                        colors: [
                            Color(red: 0.99, green: 0.95, blue: 0.90),
                            Color(red: 0.94, green: 0.88, blue: 0.80),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    in: RoundedRectangle(cornerRadius: 28, style: .continuous)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .stroke(Color(red: 0.61, green: 0.34, blue: 0.15).opacity(0.14), lineWidth: 1)
                )

                if let job = model.activeJob {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            StatusBadge(
                                title: job.state.capitalized,
                                tint: job.state == "failed" ? .red : (job.state == "completed" ? .green : .orange)
                            )
                            Text("\(job.percent)%")
                                .font(.headline.monospacedDigit())
                            Spacer()
                            Text(job.message)
                                .foregroundStyle(.secondary)
                        }
                        ProgressView(value: Double(job.percent), total: 100)
                    }
                    .padding(18)
                    .background(Color.white.opacity(0.7), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                }

                LazyVGrid(columns: columns, spacing: 16) {
                    ForEach(PipelineStage.allCases) { stage in
                        PipelineStageCard(stage: stage, state: model.pipelineState(for: stage))
                    }
                }

                DisclosureGroup("任务日志", isExpanded: $showLogs) {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 10) {
                            ForEach(Array(model.jobLogs.reversed())) { item in
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(item.line)
                                        .font(.system(.body, design: .monospaced))
                                    Text(item.timestamp)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.vertical, 4)
                                Divider()
                            }
                        }
                    }
                    .frame(minHeight: 220)
                }
                .padding(20)
                .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            }
            .padding(28)
        }
        .background(
            LinearGradient(
                colors: [
                    Color(red: 0.97, green: 0.95, blue: 0.91),
                    Color(red: 0.93, green: 0.89, blue: 0.84),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
    }
}

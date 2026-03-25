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

                    Picker("模式", selection: $model.translateMode) {
                        ForEach(TranslateMode.allCases) { mode in
                            Text(mode.title).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 240)

                    Text(model.translateMode == .single
                        ? "输入文章 URL，后台 Python worker 会负责抓取、翻译、润色和产物落盘。"
                        : "输入目录页 URL，自动发现子链接，勾选后批量翻译。")
                        .font(.title3)
                        .foregroundStyle(.secondary)

                    HStack(spacing: 12) {
                        TextField(
                            model.translateMode == .single
                                ? "https://example.com/blog-post"
                                : "https://example.com/guide/",
                            text: $model.translationURL
                        )
                        .textFieldStyle(.roundedBorder)
                        .font(.body.monospaced())

                        if model.translateMode == .single {
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
                        } else {
                            Button("发现链接") {
                                Task { await model.discoverLinks() }
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(
                                model.translationURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                                || model.isDiscovering
                            )

                            if model.isDiscovering {
                                ProgressView()
                                    .controlSize(.small)
                            }
                        }
                    }
                }
                .padding(26)
                .background(
                    Color(nsColor: .controlBackgroundColor),
                    in: RoundedRectangle(cornerRadius: 28, style: .continuous)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                )

                // Link discovery results
                if let discovery = model.discoveredLinks, model.translateMode == .discover {
                    VStack(alignment: .leading, spacing: 14) {
                        HStack {
                            Text(discovery.pageTitle)
                                .font(.headline)
                            Spacer()
                            Text("发现 \(discovery.links.count) 个链接")
                                .foregroundStyle(.secondary)
                        }

                        if discovery.links.isEmpty {
                            Text("未发现文章链接，请检查 URL 是否为目录页。")
                                .foregroundStyle(.orange)
                        } else {
                            if discovery.links.count > 50 {
                                Text("发现 \(discovery.links.count) 个链接，可能不是系列文章目录页，建议手动筛选。")
                                    .font(.caption)
                                    .foregroundStyle(.orange)
                            }

                            HStack {
                                Button("全选") {
                                    model.selectedDiscoveredURLs = Set(discovery.links.map(\.url))
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                                Button("取消全选") {
                                    model.selectedDiscoveredURLs = []
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }

                            ScrollView {
                                LazyVStack(alignment: .leading, spacing: 8) {
                                    ForEach(discovery.links) { link in
                                        HStack(spacing: 10) {
                                            Toggle("", isOn: Binding(
                                                get: { model.selectedDiscoveredURLs.contains(link.url) },
                                                set: { selected in
                                                    if selected {
                                                        model.selectedDiscoveredURLs.insert(link.url)
                                                    } else {
                                                        model.selectedDiscoveredURLs.remove(link.url)
                                                    }
                                                }
                                            ))
                                            .toggleStyle(.checkbox)
                                            .labelsHidden()

                                            VStack(alignment: .leading, spacing: 2) {
                                                Text(link.title)
                                                    .lineLimit(1)
                                                Text(link.url)
                                                    .font(.caption)
                                                    .foregroundStyle(.secondary)
                                                    .lineLimit(1)
                                            }

                                            Spacer()

                                            if link.alreadyExists {
                                                Text("已存在")
                                                    .font(.caption2)
                                                    .padding(.horizontal, 6)
                                                    .padding(.vertical, 2)
                                                    .background(Color.orange.opacity(0.15), in: Capsule())
                                                    .foregroundStyle(.orange)
                                            }
                                        }
                                        .padding(.vertical, 4)
                                        Divider()
                                    }
                                }
                            }
                            .frame(maxHeight: 320)

                            HStack(spacing: 12) {
                                TextField("系列名称", text: $model.batchSeriesTitle)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(maxWidth: 300)

                                Button("批量翻译 (\(model.selectedDiscoveredURLs.count) 篇)") {
                                    Task { await model.startBatchTranslation() }
                                }
                                .buttonStyle(.borderedProminent)
                                .disabled(model.selectedDiscoveredURLs.isEmpty)
                            }
                        }
                    }
                    .padding(18)
                    .background(Color(nsColor: .controlBackgroundColor).opacity(0.7), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                }

                // Batch progress
                if let batch = model.activeBatch {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            StatusBadge(title: "批量翻译", tint: .orange)
                            Text("文章 \(batch.currentIndex)/\(batch.totalJobs)")
                                .font(.headline.monospacedDigit())
                            Spacer()
                            if let title = batch.currentArticleTitle {
                                Text(title)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        ProgressView(value: Double(batch.currentIndex), total: Double(batch.totalJobs))

                        if !model.batchJobMessage.isEmpty {
                            HStack {
                                Text(model.batchJobMessage)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text("\(model.batchJobPercent)%")
                                    .font(.caption.monospacedDigit())
                                    .foregroundStyle(.secondary)
                            }
                            ProgressView(value: Double(model.batchJobPercent), total: 100)
                                .tint(.orange)
                        }

                        Button("取消批量翻译") {
                            Task { await model.cancelBatch() }
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(18)
                    .background(Color(nsColor: .controlBackgroundColor).opacity(0.7), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                }

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

                        if job.state == "failed" {
                            HStack(spacing: 12) {
                                Button("重试") {
                                    Task { await model.retryTranslation() }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(.orange)

                                if let errorSummary = job.errorSummary {
                                    Text(errorSummary)
                                        .font(.caption)
                                        .foregroundStyle(.red)
                                        .lineLimit(2)
                                }
                            }
                            .padding(.top, 4)
                        }

                        if job.state == "completed", model.completedArticleID != nil {
                            Button("查看文章") {
                                model.navigateToCompletedArticle()
                            }
                            .buttonStyle(.borderedProminent)
                            .padding(.top, 4)
                        }
                    }
                    .padding(18)
                    .background(Color(nsColor: .controlBackgroundColor).opacity(0.7), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
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
                .background(Color(nsColor: .controlBackgroundColor).opacity(0.72), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            }
            .padding(28)
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .alert("文章已存在", isPresented: $model.showDuplicateAlert) {
            Button("仍然翻译") {
                Task { await model.startTranslation(skipDuplicateCheck: true) }
            }
            Button("取消", role: .cancel) {}
        } message: {
            let titles = model.duplicateArticles.map(\.title).joined(separator: "\n")
            Text("该 URL 已翻译过以下文章：\n\(titles)\n\n确定要重新翻译吗？")
        }
    }
}

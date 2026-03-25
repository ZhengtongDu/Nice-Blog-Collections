import SwiftUI

enum ArticleWorkspaceKind {
    case library
    case reviewQueue

    var title: String {
        switch self {
        case .library: "Library"
        case .reviewQueue: "Review Queue"
        }
    }

    var emptyMessage: String {
        switch self {
        case .library: "当前筛选条件下没有文章。"
        case .reviewQueue: "暂时没有待审查文章。"
        }
    }
}

struct ArticleWorkspaceView: View {
    @ObservedObject var model: AppModel
    let kind: ArticleWorkspaceKind
    @State private var articleToDelete: ArticleSummary?

    private var selection: Binding<String?> {
        Binding(
            get: {
                switch kind {
                case .library: model.selectedLibraryArticleID
                case .reviewQueue: model.selectedReviewArticleID
                }
            },
            set: { newValue in
                switch kind {
                case .library: model.selectLibraryArticle(newValue)
                case .reviewQueue: model.selectReviewArticle(newValue)
                }
            }
        )
    }

    private var articles: [ArticleSummary] {
        switch kind {
        case .library: model.filteredLibraryArticles
        case .reviewQueue: model.reviewQueueArticles
        }
    }

    private var editorBinding: Binding<String> {
        Binding(
            get: { model.editorText },
            set: { model.handleEditorChange($0) }
        )
    }

    var body: some View {
        HSplitView {
            sidebarPane
                .frame(minWidth: 250, idealWidth: 290, maxWidth: 320)
            contentPane
                .frame(minWidth: 620, idealWidth: 920)
            inspectorPane
                .frame(minWidth: 220, idealWidth: 250, maxWidth: 280)
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .alert(
            "确认删除",
            isPresented: Binding(
                get: { articleToDelete != nil },
                set: { if !$0 { articleToDelete = nil } }
            )
        ) {
            Button("删除", role: .destructive) {
                if let article = articleToDelete {
                    Task { await model.deleteArticle(article.id) }
                }
                articleToDelete = nil
            }
            Button("取消", role: .cancel) { articleToDelete = nil }
        } message: {
            Text("将永久删除「\(articleToDelete?.title ?? "")」及其所有文件。此操作不可撤销。")
        }
    }

    private var sidebarPane: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(kind.title)
                .font(.system(size: 28, weight: .bold, design: .rounded))

            if kind == .library {
                TextField("搜索标题 / 作者 / 来源", text: $model.librarySearch)
                    .textFieldStyle(.roundedBorder)

                Picker("状态", selection: Binding<ArticleStatus?>(
                    get: { model.libraryFilter },
                    set: { model.libraryFilter = $0 }
                )) {
                    Text("全部").tag(Optional<ArticleStatus>.none)
                    ForEach(ArticleStatus.allCases) { status in
                        Text(status.title).tag(Optional(status))
                    }
                }
                .pickerStyle(.segmented)
            } else {
                Text("聚焦所有 `status=translated` 的文章。")
                    .foregroundStyle(.secondary)
            }

            if articles.isEmpty {
                Spacer()
                VStack(spacing: 14) {
                    Image(systemName: kind == .library ? "books.vertical" : "checklist")
                        .font(.system(size: 38))
                        .foregroundStyle(.tertiary)
                    Text(kind.emptyMessage)
                        .foregroundStyle(.secondary)
                    if kind == .library {
                        Button("翻译第一篇文章") {
                            model.selectedSection = .translate
                        }
                        .buttonStyle(.bordered)
                    }
                }
                .frame(maxWidth: .infinity)
                Spacer()
            } else {
                List(selection: selection) {
                    ForEach(articles) { article in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(article.title)
                                .font(.headline)
                                .lineLimit(2)
                            HStack {
                                Text(article.author)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                if let status = ArticleStatus(rawValue: article.status) {
                                    StatusBadge(title: status.title, tint: color(for: status))
                                }
                            }
                            HStack(spacing: 8) {
                                Text(article.added)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                if let host = URL(string: article.sourceURL)?.host {
                                    Text(host)
                                        .font(.caption2)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.secondary.opacity(0.12), in: Capsule())
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                        .padding(.vertical, 4)
                        .tag(Optional(article.id))
                        .contextMenu {
                            Button("在 Finder 中打开") {
                                NSWorkspace.shared.activateFileViewerSelecting([
                                    URL(fileURLWithPath: article.directoryPath)
                                ])
                            }
                            Divider()
                            Button("删除", role: .destructive) {
                                articleToDelete = article
                            }
                        }
                    }
                }
                .listStyle(.sidebar)
            }
        }
        .padding(18)
    }

    private var contentPane: some View {
        VStack(alignment: .leading, spacing: 16) {
            if let article = model.activeArticle {
                VStack(alignment: .leading, spacing: 12) {
                    Text(article.title)
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                        .fixedSize(horizontal: false, vertical: true)

                    HStack(alignment: .center, spacing: 16) {
                        Text(model.saveState.title)
                            .font(.headline)
                            .foregroundStyle(saveStateColor)

                        Spacer()

                        Text("视图")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)

                        Spacer(minLength: 0)

                    }

                    Picker("视图", selection: $model.reviewMode) {
                        ForEach(ReviewContentMode.allCases) { mode in
                            Text(mode.title).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(maxWidth: 320)
                }
                .padding(.bottom, 8)

                switch model.reviewMode {
                case .preview:
                    previewPane(for: article)
                case .markdown:
                    markdownEditor
                case .split:
                    VSplitView {
                        markdownEditor
                            .frame(minHeight: 220, idealHeight: 280)

                        previewPane(for: article)
                            .frame(minHeight: 340, idealHeight: 560)
                    }
                }
            } else {
                Spacer()
                VStack(alignment: .center, spacing: 12) {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.system(size: 44))
                        .foregroundStyle(.secondary)
                    Text("选择一篇文章开始审查")
                        .font(.title3.weight(.semibold))
                    Text("中间区域支持渲染预览、Markdown 编辑和 Split 视图。")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                Spacer()
            }
        }
        .padding(18)
    }

    private var markdownEditor: some View {
        TextEditor(text: editorBinding)
            .font(.system(.body, design: .monospaced))
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .fill(Color(nsColor: .textBackgroundColor).opacity(0.78))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Color.black.opacity(0.06), lineWidth: 1)
            )
    }

    private func previewPane(for article: ArticleDetail) -> some View {
        HTMLPreviewView(
            htmlPath: article.htmlPath,
            readAccessDirectory: article.directoryPath,
            reloadToken: model.previewReloadToken
        )
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor).opacity(0.62))
        )
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.black.opacity(0.06), lineWidth: 1)
        )
    }

    private var inspectorPane: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Inspector")
                    .font(.title3.weight(.bold))

                if let article = model.activeArticle {
                    Picker(
                        "状态",
                        selection: Binding(
                            get: { model.currentStatus(for: article) },
                            set: { newValue in
                                Task { await model.updateStatus(newValue) }
                            }
                        )
                    ) {
                        ForEach(ArticleStatus.allCases) { status in
                            Text(status.title).tag(status)
                        }
                    }

                    // Series info
                    if let series = article.series, !series.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("系列")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(series)
                                .font(.subheadline.weight(.medium))
                        }
                    }

                    if let parentID = article.parent, !parentID.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("父文章")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Button(parentID) {
                                selection.wrappedValue = parentID
                            }
                            .buttonStyle(.link)
                            .font(.caption)
                        }
                    }

                    if let children = article.children, !children.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("子文章 (\(children.count))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            ForEach(children, id: \.self) { childID in
                                Button(childID) {
                                    selection.wrappedValue = childID
                                }
                                .buttonStyle(.link)
                                .font(.caption)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        ActionButton(title: "复制公众号富文本", systemImage: "doc.on.doc") {
                            Task { await model.copyCurrentArticleRichText() }
                        }
                        ActionButton(title: "导出 HTML", systemImage: "doc.richtext") {
                            Task { await model.exportCurrentArticleHTML() }
                        }
                        ActionButton(title: "保存 Markdown", systemImage: "square.and.arrow.down") {
                            Task { await model.saveCurrentArticle() }
                        }
                        ActionButton(title: "在 Finder 中打开", systemImage: "folder") {
                            model.openCurrentArticleFolder()
                        }

                        Divider()

                        Button(role: .destructive) {
                            if let summary = model.allArticles.first(where: { $0.id == article.id }) {
                                articleToDelete = summary
                            }
                        } label: {
                            Label("删除文章", systemImage: "trash")
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .buttonStyle(.bordered)
                    }

                    metadataRow("作者", article.author)
                    metadataRow("添加日期", article.added)
                    metadataRow("原文日期", article.date)
                    metadataRow("来源", article.sourceURL)
                    metadataRow("目录", article.directoryPath)

                    if let htmlPath = article.htmlPath {
                        metadataRow("HTML", htmlPath)
                    }

                    if !article.images.isEmpty {
                        Text("图片")
                            .font(.headline)
                        ForEach(article.images, id: \.self) { imagePath in
                            Text(imagePath)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                        }
                    }
                } else {
                    Text("选择文章后可查看元数据、状态和导出动作。")
                        .foregroundStyle(.secondary)
                }
            }
            .padding(18)
        }
    }

    private func metadataRow(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value.isEmpty ? "—" : value)
                .textSelection(.enabled)
        }
    }

    private var saveStateColor: Color {
        switch model.saveState {
        case .saved: .green
        case .dirty: .orange
        case .saving: .secondary
        case .failed: .red
        }
    }

    private func color(for status: ArticleStatus) -> Color {
        switch status {
        case .pending: .gray
        case .translated: .orange
        case .published: .green
        case .failed: .red
        }
    }
}

private struct ActionButton: View {
    let title: String
    let systemImage: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.bordered)
    }
}

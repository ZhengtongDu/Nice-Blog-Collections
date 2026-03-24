import AppKit
import Foundation
import SwiftUI

@MainActor
final class AppModel: ObservableObject {
    @Published var selectedSection: AppSection? = .translate
    @Published var needsOnboarding = false
    @Published var health: AppHealth = .empty
    @Published var allArticles: [ArticleSummary] = []
    @Published var selectedLibraryArticleID: String?
    @Published var selectedReviewArticleID: String?
    @Published var activeArticle: ArticleDetail?
    @Published var editorText = ""
    @Published var reviewMode: ReviewContentMode = .split
    @Published var saveState: SaveState = .saved
    @Published var translationURL = ""
    @Published var activeJob: JobSnapshot?
    @Published var jobLogs: [JobLogItem] = []
    @Published var librarySearch = ""
    @Published var libraryFilter: ArticleStatus?
    @Published var workerErrorMessage: String?
    @Published var transientMessage: String?
    @Published var previewReloadToken = UUID()
    @Published var lastTranslatedURL = ""
    @Published var completedArticleID: String?
    @Published var showDuplicateAlert = false
    @Published var duplicateArticles: [ArticleSummary] = []

    private let storageRootKey = "BlogTranslatorApp.storageRoot"
    private let worker = WorkerClient()
    private let decoder = JSONDecoder()
    private var autosaveTask: Task<Void, Never>?
    private var isApplyingRemoteText = false

    func bootstrap() async {
        worker.eventHandler = { [weak self] event, data in
            Task { @MainActor [weak self] in
                await self?.handleWorkerEvent(event: event, data: data)
            }
        }

        let savedRoot = UserDefaults.standard.string(forKey: storageRootKey)
        needsOnboarding = savedRoot == nil
        let bootstrapRoot = savedRoot ?? defaultBootstrapStorageRoot()

        do {
            try worker.start(storageRoot: bootstrapRoot)
            try await refreshHealth()
            try await refreshArticles()
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    var filteredLibraryArticles: [ArticleSummary] {
        allArticles.filter { article in
            let matchesStatus: Bool
            if let libraryFilter {
                matchesStatus = article.status == libraryFilter.rawValue
            } else {
                matchesStatus = true
            }

            let term = librarySearch.trimmingCharacters(in: .whitespacesAndNewlines)
            let matchesSearch: Bool
            if term.isEmpty {
                matchesSearch = true
            } else {
                let haystack = "\(article.title) \(article.author) \(article.sourceURL)".localizedLowercase
                matchesSearch = haystack.contains(term.localizedLowercase)
            }

            return matchesStatus && matchesSearch
        }
    }

    var reviewQueueArticles: [ArticleSummary] {
        allArticles.filter { $0.status == ArticleStatus.translated.rawValue }
    }

    func chooseStorageRoot() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.prompt = "选择内容库"
        panel.message = "选择一个目录作为文章、日志与导出内容的根目录。"

        if panel.runModal() == .OK, let url = panel.url {
            Task {
                await applyStorageRoot(url.path)
            }
        }
    }

    func applyStorageRoot(_ path: String) async {
        do {
            let health: AppHealth = try await worker.request(
                "set_storage_root",
                params: ["path": path]
            )
            UserDefaults.standard.set(path, forKey: storageRootKey)
            self.health = health
            self.needsOnboarding = false
            try await refreshArticles()
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func refreshHealth() async throws {
        health = try await worker.request("health_check", as: AppHealth.self)
    }

    func refreshArticles() async throws {
        allArticles = try await worker.request("list_articles", as: [ArticleSummary].self)
    }

    func selectLibraryArticle(_ articleID: String?) {
        selectedLibraryArticleID = articleID
        guard let articleID else { return }
        Task {
            await loadArticle(articleID: articleID)
        }
    }

    func selectReviewArticle(_ articleID: String?) {
        selectedReviewArticleID = articleID
        guard let articleID else { return }
        Task {
            await loadArticle(articleID: articleID)
        }
    }

    func loadArticle(articleID: String) async {
        do {
            let detail: ArticleDetail = try await worker.request(
                "get_article",
                params: ["articleId": articleID]
            )
            activeArticle = detail
            isApplyingRemoteText = true
            editorText = detail.translatedMarkdown
            isApplyingRemoteText = false
            saveState = .saved
            previewReloadToken = UUID()
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func handleEditorChange(_ newValue: String) {
        editorText = newValue
        guard !isApplyingRemoteText, activeArticle != nil else { return }
        saveState = .dirty
        autosaveTask?.cancel()
        autosaveTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(800))
            await self?.saveCurrentArticle()
        }
    }

    func saveCurrentArticle() async {
        guard var article = activeArticle else { return }
        guard article.translatedMarkdown != editorText || saveState == .dirty else { return }
        saveState = .saving

        do {
            let ack: WorkerAcknowledgement = try await worker.request(
                "save_translated_markdown",
                params: [
                    "articleId": article.id,
                    "markdown": editorText,
                ]
            )
            article.translatedMarkdown = editorText
            article.htmlPath = ack.htmlPath ?? article.htmlPath
            activeArticle = article
            saveState = .saved
            previewReloadToken = UUID()
            transientMessage = "已保存 Markdown 与 HTML"
            try await refreshArticles()
        } catch {
            saveState = .failed(error.localizedDescription)
        }
    }

    func exportCurrentArticleHTML() async {
        guard let article = activeArticle else { return }
        await saveCurrentArticle()

        do {
            let ack: WorkerAcknowledgement = try await worker.request(
                "export_article_html",
                params: ["articleId": article.id]
            )
            if var current = activeArticle {
                current.htmlPath = ack.htmlPath ?? current.htmlPath
                activeArticle = current
            }
            previewReloadToken = UUID()
            transientMessage = "已导出 HTML"
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func copyCurrentArticleRichText() async {
        guard activeArticle != nil else { return }
        await exportCurrentArticleHTML()

        guard let htmlPath = activeArticle?.htmlPath else {
            workerErrorMessage = "未找到 HTML 导出文件"
            return
        }

        do {
            let html = try String(contentsOfFile: htmlPath, encoding: .utf8)
            PasteboardWriter.copy(html: html, plainText: editorText)
            transientMessage = "已复制公众号可用富文本"
        } catch {
            workerErrorMessage = "读取 HTML 失败: \(error.localizedDescription)"
        }
    }

    func updateStatus(_ status: ArticleStatus) async {
        guard var article = activeArticle else { return }
        do {
            _ = try await worker.request(
                "update_status",
                params: [
                    "articleId": article.id,
                    "status": status.rawValue,
                ],
                as: WorkerAcknowledgement.self
            )
            article.status = status.rawValue
            activeArticle = article
            try await refreshArticles()
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func openCurrentArticleFolder() {
        guard let article = activeArticle else { return }
        NSWorkspace.shared.activateFileViewerSelecting([
            URL(fileURLWithPath: article.directoryPath)
        ])
    }

    func deleteArticle(_ articleID: String) async {
        do {
            _ = try await worker.request(
                "delete_article",
                params: ["articleId": articleID],
                as: WorkerAcknowledgement.self
            )
            if activeArticle?.id == articleID {
                activeArticle = nil
                editorText = ""
            }
            if selectedLibraryArticleID == articleID {
                selectedLibraryArticleID = nil
            }
            if selectedReviewArticleID == articleID {
                selectedReviewArticleID = nil
            }
            try await refreshArticles()
            transientMessage = "文章已删除"
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func openLogsFolder() {
        guard !health.logsDir.isEmpty else { return }
        NSWorkspace.shared.activateFileViewerSelecting([
            URL(fileURLWithPath: health.logsDir)
        ])
    }

    func startTranslation(skipDuplicateCheck: Bool = false) async {
        let url = translationURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !url.isEmpty else { return }

        if !skipDuplicateCheck {
            do {
                let result: DuplicateCheckResult = try await worker.request(
                    "check_duplicate",
                    params: ["url": url]
                )
                if !result.duplicates.isEmpty {
                    duplicateArticles = result.duplicates
                    showDuplicateAlert = true
                    return
                }
            } catch {
                // check_duplicate failure is non-blocking; proceed with translation
            }
        }

        do {
            jobLogs = []
            lastTranslatedURL = url
            completedArticleID = nil
            activeJob = try await worker.request(
                "start_translation",
                params: ["url": url],
                as: JobSnapshot.self
            )
            transientMessage = nil
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func retryTranslation() async {
        translationURL = lastTranslatedURL
        await startTranslation(skipDuplicateCheck: true)
    }

    func navigateToCompletedArticle() {
        guard let articleID = completedArticleID else { return }
        selectedSection = .library
        selectLibraryArticle(articleID)
    }

    func cancelTranslation() async {
        guard let activeJob else { return }
        do {
            _ = try await worker.request(
                "cancel_job",
                params: ["jobId": activeJob.jobId],
                as: WorkerAcknowledgement.self
            )
        } catch {
            workerErrorMessage = error.localizedDescription
        }
    }

    func pipelineState(for stage: PipelineStage) -> StageVisualState {
        guard let activeJob else { return .idle }
        if activeJob.state == "failed", activeJob.stage == stage.key {
            return .failed
        }
        if activeJob.state == "completed" {
            return .completed
        }
        let allStages = PipelineStage.allCases
        guard let currentIndex = allStages.firstIndex(where: { $0.key == activeJob.stage }),
              let stageIndex = allStages.firstIndex(of: stage) else {
            return .idle
        }

        if stageIndex < currentIndex {
            return .completed
        }
        if stageIndex == currentIndex {
            return .active
        }
        return .idle
    }

    func currentStatus(for article: ArticleDetail?) -> ArticleStatus {
        ArticleStatus(rawValue: article?.status ?? "") ?? .pending
    }

    private func handleWorkerEvent(event: String, data: Data) async {
        switch event {
        case "job_started", "job_progress", "job_completed":
            if let snapshot = try? decoder.decode(JobSnapshot.self, from: data) {
                activeJob = snapshot
                if snapshot.state == "completed" {
                    translationURL = ""
                    transientMessage = "翻译任务完成"
                    if let outputDir = snapshot.outputDirectory {
                        let articleID = URL(fileURLWithPath: outputDir).lastPathComponent
                        completedArticleID = articleID
                    }
                    try? await refreshArticles()
                }
            }
        case "job_log":
            if let log = try? decoder.decode(JobLogItem.self, from: data) {
                jobLogs.append(log)
            }
        case "job_error":
            if let error = try? decoder.decode(JobErrorPayload.self, from: data) {
                workerErrorMessage = error.message
            }
        case "html_exported":
            if let ack = try? decoder.decode(WorkerAcknowledgement.self, from: data),
               var current = activeArticle,
               ack.articleId == current.id {
                current.htmlPath = ack.htmlPath ?? current.htmlPath
                activeArticle = current
                previewReloadToken = UUID()
            }
        case "article_saved":
            if let ack = try? decoder.decode(WorkerAcknowledgement.self, from: data),
               var current = activeArticle,
               ack.articleId == current.id {
                current.translatedMarkdown = editorText
                current.htmlPath = ack.htmlPath ?? current.htmlPath
                activeArticle = current
                previewReloadToken = UUID()
            }
        case "articles_changed":
            do {
                try await refreshArticles()
            } catch {
                workerErrorMessage = error.localizedDescription
            }
        default:
            break
        }
    }

    private func defaultBootstrapStorageRoot() -> String {
        let fileManager = FileManager.default
        let baseURL = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        let rootURL = baseURL
            .appendingPathComponent("博文翻译助手", isDirectory: true)
            .appendingPathComponent("BootstrapStorage", isDirectory: true)
        try? fileManager.createDirectory(at: rootURL, withIntermediateDirectories: true)
        return rootURL.path
    }
}

enum StageVisualState {
    case idle
    case active
    case completed
    case failed
}

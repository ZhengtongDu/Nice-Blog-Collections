import Foundation

enum AppSection: String, CaseIterable, Identifiable {
    case translate
    case library
    case reviewQueue
    case settings

    var id: String { rawValue }

    var title: String {
        switch self {
        case .translate: "Translate"
        case .library: "Library"
        case .reviewQueue: "Review Queue"
        case .settings: "Settings"
        }
    }

    var systemImage: String {
        switch self {
        case .translate: "sparkles.rectangle.stack"
        case .library: "books.vertical"
        case .reviewQueue: "checklist"
        case .settings: "slider.horizontal.3"
        }
    }
}

enum ArticleStatus: String, Codable, CaseIterable, Identifiable {
    case pending
    case translated
    case published
    case failed

    var id: String { rawValue }

    var title: String {
        switch self {
        case .pending: "待处理"
        case .translated: "待审查"
        case .published: "已发布"
        case .failed: "失败"
        }
    }

    var tintName: String {
        switch self {
        case .pending: "gray"
        case .translated: "orange"
        case .published: "green"
        case .failed: "red"
        }
    }
}

enum ReviewContentMode: String, CaseIterable, Identifiable {
    case preview
    case markdown
    case split

    var id: String { rawValue }

    var title: String {
        switch self {
        case .preview: "Preview"
        case .markdown: "Markdown"
        case .split: "Split"
        }
    }
}

enum SaveState: Equatable {
    case saved
    case dirty
    case saving
    case failed(String)

    var title: String {
        switch self {
        case .saved: "已保存"
        case .dirty: "待保存"
        case .saving: "保存中"
        case let .failed(message): "保存失败: \(message)"
        }
    }
}

struct ArticleSummary: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let author: String
    let added: String
    let date: String
    let status: String
    let sourceURL: String
    let directoryPath: String
    let htmlPath: String?
}

struct ArticleDetail: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let author: String
    let added: String
    let date: String
    var status: String
    let sourceURL: String
    let directoryPath: String
    var htmlPath: String?
    let originalMarkdown: String
    let rawTranslatedMarkdown: String
    var translatedMarkdown: String
    let images: [String]
}

struct JobSnapshot: Codable, Equatable {
    let jobId: String
    let url: String
    let stage: String
    let percent: Int
    let state: String
    let startTime: String
    let endTime: String?
    let message: String
    let logItems: [String]
    let outputDirectory: String?
    let errorSummary: String?
}

struct JobLogItem: Codable, Identifiable, Hashable {
    let jobId: String
    let timestamp: String
    let line: String

    var id: String { "\(timestamp)-\(line)" }
}

struct JobErrorPayload: Codable {
    let jobId: String
    let stage: String
    let message: String
    let logPath: String?
}

struct AppHealth: Codable, Equatable {
    let storageRoot: String
    let articlesDir: String
    let logsDir: String
    let workerReady: Bool
    let ollamaReachable: Bool
    let modelInstalled: Bool
    let lastError: String?

    static let empty = AppHealth(
        storageRoot: "",
        articlesDir: "",
        logsDir: "",
        workerReady: false,
        ollamaReachable: false,
        modelInstalled: false,
        lastError: nil
    )
}

struct WorkerAcknowledgement: Codable {
    let articleId: String?
    let savedAt: String?
    let translatedPath: String?
    let htmlPath: String?
    let updatedAt: String?
    let status: String?
    let accepted: Bool?
    let jobId: String?
    let deleted: Bool?
}

struct DuplicateCheckResult: Codable {
    let url: String
    let duplicates: [ArticleSummary]
}

enum PipelineStage: CaseIterable, Identifiable {
    case checkOllama
    case fetch
    case extractMetadata
    case convert
    case translate
    case polish
    case save

    var id: String { key }

    var key: String {
        switch self {
        case .checkOllama: "check_ollama"
        case .fetch: "fetch"
        case .extractMetadata: "extract_metadata"
        case .convert: "convert"
        case .translate: "translate"
        case .polish: "polish"
        case .save: "save"
        }
    }

    var title: String {
        switch self {
        case .checkOllama: "Check Ollama"
        case .fetch: "Fetch"
        case .extractMetadata: "Extract Metadata"
        case .convert: "Convert"
        case .translate: "Translate"
        case .polish: "Polish"
        case .save: "Save"
        }
    }

    var subtitle: String {
        switch self {
        case .checkOllama: "检查服务和模型"
        case .fetch: "抓取文章 HTML"
        case .extractMetadata: "提取标题、作者、日期"
        case .convert: "转 Markdown + 下载图片"
        case .translate: "分段翻译正文"
        case .polish: "润色成公众号风格"
        case .save: "写入文件并导出 HTML"
        }
    }
}

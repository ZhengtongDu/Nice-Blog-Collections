import SwiftUI
import WebKit

struct HTMLPreviewView: NSViewRepresentable {
    let htmlPath: String?
    let readAccessDirectory: String?
    let reloadToken: UUID

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.setValue(false, forKey: "drawsBackground")
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {
        guard let htmlPath,
              let readAccessDirectory else {
            nsView.loadHTMLString(
                """
                <html><body style="font-family:-apple-system;padding:32px;color:#7d6850;background:#fbf7f1;">
                暂无可预览内容。
                </body></html>
                """,
                baseURL: nil
            )
            return
        }

        let fileURL = URL(fileURLWithPath: htmlPath)
        let accessURL = URL(fileURLWithPath: readAccessDirectory)
        nsView.loadFileURL(fileURL, allowingReadAccessTo: accessURL)
    }
}

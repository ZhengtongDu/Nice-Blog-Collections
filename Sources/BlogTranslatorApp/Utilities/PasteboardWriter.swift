import AppKit
import Foundation

enum PasteboardWriter {
    static func copy(html: String, plainText: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(plainText, forType: .string)
        pasteboard.setString(html, forType: .html)
    }
}

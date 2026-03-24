import XCTest
@testable import BlogTranslatorApp

final class RepositoryLocatorTests: XCTestCase {
    func testRepositoryRootCanBeResolvedFromWorkspace() {
        let root = RepositoryLocator.repositoryRoot()
        XCTAssertNotNil(root)
        XCTAssertTrue(root?.path.contains("博文翻译") == true)
    }
}

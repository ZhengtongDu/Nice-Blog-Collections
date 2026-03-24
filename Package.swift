// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "BlogTranslatorApp",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(
            name: "BlogTranslatorApp",
            targets: ["BlogTranslatorApp"]
        )
    ],
    targets: [
        .executableTarget(
            name: "BlogTranslatorApp",
            path: "Sources/BlogTranslatorApp"
        ),
        .testTarget(
            name: "BlogTranslatorAppTests",
            dependencies: ["BlogTranslatorApp"],
            path: "Tests/BlogTranslatorAppTests"
        ),
    ]
)

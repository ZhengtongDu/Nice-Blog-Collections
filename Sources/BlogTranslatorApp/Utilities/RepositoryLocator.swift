import Foundation

enum RepositoryLocator {
    static func repositoryRoot() -> URL? {
        let fileManager = FileManager.default
        let currentDirectory = URL(fileURLWithPath: fileManager.currentDirectoryPath)
        let executableDirectory = URL(fileURLWithPath: CommandLine.arguments[0])
            .deletingLastPathComponent()

        for candidate in [currentDirectory, executableDirectory] {
            if let root = searchUpwards(from: candidate) {
                return root
            }
        }

        return nil
    }

    static func bundledWorkerRoot() -> URL? {
        guard let resourceURL = Bundle.main.resourceURL else {
            return nil
        }

        let candidate = resourceURL.appendingPathComponent("PythonWorker")
        let worker = candidate.appendingPathComponent("src/worker/main.py")
        if FileManager.default.fileExists(atPath: worker.path) {
            return candidate
        }
        return nil
    }

    static func workerScriptURL() -> URL? {
        if let bundledRoot = bundledWorkerRoot() {
            return bundledRoot.appendingPathComponent("src/worker/main.py")
        }
        return repositoryRoot()?.appendingPathComponent("src/worker/main.py")
    }

    static func workingDirectory() -> URL? {
        bundledWorkerRoot() ?? repositoryRoot()
    }

    private static func searchUpwards(from startingURL: URL) -> URL? {
        var candidate = startingURL
        while true {
            let worker = candidate.appendingPathComponent("src/worker/main.py")
            let translate = candidate.appendingPathComponent("src/translate.py")
            if FileManager.default.fileExists(atPath: worker.path),
               FileManager.default.fileExists(atPath: translate.path) {
                return candidate
            }

            let parent = candidate.deletingLastPathComponent()
            if parent.path == candidate.path {
                return nil
            }
            candidate = parent
        }
    }
}

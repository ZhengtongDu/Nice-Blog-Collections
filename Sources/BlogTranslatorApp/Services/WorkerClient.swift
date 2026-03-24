import Foundation

enum WorkerClientError: LocalizedError {
    case workerNotFound
    case failedToStart(String)
    case pipeUnavailable
    case invalidResponse
    case workerReturnedError(String)
    case terminated

    var errorDescription: String? {
        switch self {
        case .workerNotFound:
            "未找到 Python worker，请确认仓库结构完整。"
        case let .failedToStart(message):
            "启动 worker 失败: \(message)"
        case .pipeUnavailable:
            "worker 管道不可用。"
        case .invalidResponse:
            "worker 返回了无法解析的数据。"
        case let .workerReturnedError(message):
            message
        case .terminated:
            "worker 已退出。"
        }
    }
}

final class WorkerClient: @unchecked Sendable {
    var eventHandler: (@Sendable (String, Data) -> Void)?

    private let decoder = JSONDecoder()
    private let queue = DispatchQueue(label: "blog-translator.worker-client")
    private var process: Process?
    private var inputHandle: FileHandle?
    private var outputHandle: FileHandle?
    private var buffer = Data()
    private var pending: [String: (Result<Data, Error>) -> Void] = [:]

    deinit {
        stop()
    }

    func start(storageRoot: String?) throws {
        if process?.isRunning == true {
            return
        }

        guard let workerURL = RepositoryLocator.workerScriptURL(),
              let workingDirectory = RepositoryLocator.workingDirectory() else {
            throw WorkerClientError.workerNotFound
        }

        let inputPipe = Pipe()
        let outputPipe = Pipe()
        let errorPipe = Pipe()

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", workerURL.path]
        process.currentDirectoryURL = workingDirectory

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONUNBUFFERED"] = "1"
        if let storageRoot, !storageRoot.isEmpty {
            environment["BLOG_TRANSLATOR_STORAGE_ROOT"] = storageRoot
        }
        process.environment = environment

        process.standardInput = inputPipe
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        outputPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            self?.consume(data: data)
        }

        errorPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            self?.consume(stderr: data)
        }

        process.terminationHandler = { [weak self] _ in
            self?.finishPending(with: WorkerClientError.terminated)
        }

        do {
            try process.run()
        } catch {
            throw WorkerClientError.failedToStart(error.localizedDescription)
        }

        self.process = process
        self.inputHandle = inputPipe.fileHandleForWriting
        self.outputHandle = outputPipe.fileHandleForReading
    }

    func stop() {
        queue.sync {
            self.pending.removeAll()
        }
        outputHandle?.readabilityHandler = nil
        process?.terminate()
        process = nil
        inputHandle = nil
        outputHandle = nil
    }

    func request<T: Decodable>(
        _ command: String,
        params: [String: Any] = [:],
        as type: T.Type = T.self
    ) async throws -> T {
        let data = try await rawRequest(command, params: params)
        return try decoder.decode(T.self, from: data)
    }

    private func rawRequest(_ command: String, params: [String: Any]) async throws -> Data {
        let requestID = UUID().uuidString
        let payload: [String: Any] = [
            "id": requestID,
            "command": command,
            "params": params,
        ]
        let body = try JSONSerialization.data(withJSONObject: payload)

        return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Data, Error>) in
            queue.async {
                guard self.process?.isRunning == true else {
                    continuation.resume(throwing: WorkerClientError.terminated)
                    return
                }

                guard let inputHandle = self.inputHandle else {
                    continuation.resume(throwing: WorkerClientError.pipeUnavailable)
                    return
                }

                self.pending[requestID] = { result in
                    continuation.resume(with: result)
                }

                inputHandle.write(body)
                inputHandle.write(Data([0x0A]))
            }
        }
    }

    private func consume(data: Data) {
        queue.async {
            self.buffer.append(data)
            let newline = Data([0x0A])

            while let range = self.buffer.range(of: newline) {
                let lineData = self.buffer.subdata(in: self.buffer.startIndex ..< range.lowerBound)
                self.buffer.removeSubrange(self.buffer.startIndex ... range.lowerBound)

                guard !lineData.isEmpty else { continue }
                self.handle(lineData: lineData)
            }
        }
    }

    private func consume(stderr data: Data) {
        if let text = String(data: data, encoding: .utf8), !text.isEmpty {
            NSLog("Python worker stderr: %@", text)
        }
    }

    private func handle(lineData: Data) {
        guard let object = try? JSONSerialization.jsonObject(with: lineData) as? [String: Any],
              let type = object["type"] as? String else {
            return
        }

        switch type {
        case "response":
            guard let id = object["id"] as? String else { return }
            let callback = pending.removeValue(forKey: id)
            let ok = (object["ok"] as? Bool) ?? false

            if ok {
                let resultObject = object["result"] ?? NSNull()
                do {
                    let resultData = try JSONSerialization.data(
                        withJSONObject: resultObject,
                        options: [.fragmentsAllowed]
                    )
                    callback?(.success(resultData))
                } catch {
                    callback?(.failure(error))
                }
            } else {
                let errorDict = object["error"] as? [String: Any]
                let message = errorDict?["message"] as? String ?? "worker 返回未知错误"
                callback?(.failure(WorkerClientError.workerReturnedError(message)))
            }

        case "event":
            guard let event = object["event"] as? String else { return }
            let payload = object["payload"] ?? NSNull()
            guard let payloadData = try? JSONSerialization.data(
                withJSONObject: payload,
                options: [.fragmentsAllowed]
            ) else {
                return
            }

            DispatchQueue.main.async {
                self.eventHandler?(event, payloadData)
            }
        default:
            break
        }
    }

    private func finishPending(with error: Error) {
        queue.async {
            let callbacks = self.pending.values
            self.pending.removeAll()
            callbacks.forEach { $0(.failure(error)) }
        }
    }
}

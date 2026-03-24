import SwiftUI

struct PipelineStageCard: View {
    let stage: PipelineStage
    let state: StageVisualState

    private var accent: Color {
        switch state {
        case .idle: .secondary
        case .active: Color(red: 0.63, green: 0.31, blue: 0.10)
        case .completed: .green
        case .failed: .red
        }
    }

    private var symbol: String {
        switch state {
        case .idle: "circle.dashed"
        case .active: "dot.radiowaves.left.and.right"
        case .completed: "checkmark.circle.fill"
        case .failed: "xmark.octagon.fill"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Image(systemName: symbol)
                .font(.title2.weight(.semibold))
                .foregroundStyle(accent)

            Text(stage.title)
                .font(.headline)

            Text(stage.subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, minHeight: 122, alignment: .topLeading)
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(Color.white.opacity(0.82))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .stroke(accent.opacity(0.22), lineWidth: 1)
        )
        .shadow(color: accent.opacity(0.08), radius: 22, y: 12)
    }
}

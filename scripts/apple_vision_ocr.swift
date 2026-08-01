#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

struct OCRLine: Codable {
    let text: String
    let confidence: Float
    let bbox: [Double]
}

struct OCRRecord: Codable {
    let path: String
    let width: Int
    let height: Int
    let lines: [OCRLine]
}

struct OCRPayload: Codable {
    let engine: String
    let recognitionLevel: String
    let usesLanguageCorrection: Bool
    let records: [OCRRecord]
}

func recognize(path: String) throws -> OCRRecord {
    let url = URL(fileURLWithPath: path)
    guard
        let image = NSImage(contentsOf: url),
        let representation = image.cgImage(
            forProposedRect: nil,
            context: nil,
            hints: nil
        )
    else {
        throw NSError(
            domain: "AppleVisionOCR",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Cannot load image: \(path)"]
        )
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: representation)
    try handler.perform([request])

    let lines = (request.results ?? []).compactMap { observation -> OCRLine? in
        guard let candidate = observation.topCandidates(1).first else {
            return nil
        }
        let box = observation.boundingBox
        return OCRLine(
            text: candidate.string,
            confidence: candidate.confidence,
            bbox: [
                box.origin.x,
                1.0 - box.origin.y - box.height,
                box.width,
                box.height,
            ]
        )
    }.sorted { left, right in
        let verticalDifference = abs(left.bbox[1] - right.bbox[1])
        if verticalDifference < 0.01 {
            return left.bbox[0] < right.bbox[0]
        }
        return left.bbox[1] < right.bbox[1]
    }

    return OCRRecord(
        path: path,
        width: representation.width,
        height: representation.height,
        lines: lines
    )
}

do {
    let paths = Array(CommandLine.arguments.dropFirst())
    guard !paths.isEmpty else {
        throw NSError(
            domain: "AppleVisionOCR",
            code: 2,
            userInfo: [NSLocalizedDescriptionKey: "Provide at least one image path"]
        )
    }
    let payload = OCRPayload(
        engine: "apple-vision-ocr",
        recognitionLevel: "accurate",
        usesLanguageCorrection: true,
        records: try paths.map(recognize)
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    FileHandle.standardOutput.write(try encoder.encode(payload))
    FileHandle.standardOutput.write(Data("\n".utf8))
} catch {
    FileHandle.standardError.write(Data("apple vision OCR failed: \(error)\n".utf8))
    exit(1)
}

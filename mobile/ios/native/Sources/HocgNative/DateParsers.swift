import Foundation

func formatIsoDateOrNil(_ rawInput: String?) -> String? {
    let raw = (rawInput ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    guard !raw.isEmpty else {
        return nil
    }

    var candidates: [String] = [raw]
    if raw.hasSuffix("Z") {
        candidates.append(String(raw.dropLast()) + "+00:00")
    }
    if raw.contains(" ") && !raw.contains("T") {
        candidates.append(raw.replacingOccurrences(of: " ", with: "T"))
    }

    let isoFormatter = ISO8601DateFormatter()
    isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

    let isoFormatterNoFraction = ISO8601DateFormatter()
    isoFormatterNoFraction.formatOptions = [.withInternetDateTime]

    let utc = TimeZone(secondsFromGMT: 0)!
    let outFormatter = DateFormatter()
    outFormatter.calendar = Calendar(identifier: .gregorian)
    outFormatter.locale = Locale(identifier: "en_US_POSIX")
    outFormatter.timeZone = utc
    outFormatter.dateFormat = "yyyy-MM-dd"

    let dateOnly = DateFormatter()
    dateOnly.calendar = Calendar(identifier: .gregorian)
    dateOnly.locale = Locale(identifier: "en_US_POSIX")
    dateOnly.timeZone = utc
    dateOnly.dateFormat = "yyyy-MM-dd"

    for candidate in candidates {
        if let date = isoFormatter.date(from: candidate) {
            return outFormatter.string(from: date)
        }
        if let date = isoFormatterNoFraction.date(from: candidate) {
            return outFormatter.string(from: date)
        }

        let localDateTime = DateFormatter()
        localDateTime.calendar = Calendar(identifier: .gregorian)
        localDateTime.locale = Locale(identifier: "en_US_POSIX")
        localDateTime.timeZone = utc
        localDateTime.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        if let date = localDateTime.date(from: candidate) {
            return outFormatter.string(from: date)
        }

        if let date = dateOnly.date(from: candidate) {
            return outFormatter.string(from: date)
        }
    }

    return nil
}

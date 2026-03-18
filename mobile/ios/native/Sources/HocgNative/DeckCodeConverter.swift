import Foundation

// MARK: - HoloDuel deck code
// Format: O:<oshiID>|D:<id>x<n>,...|C:<id>x<n>,...
// Then Base64-encoded

enum DeckCodeConverter {

    // MARK: - 카드 분류 helpers

    static func isOshiCard(_ card: DeckCardCandidate) -> Bool {
        card.cardType.contains("오시") || card.cardType.contains("推し")
    }

    static func isYellCard(_ card: DeckCardCandidate) -> Bool {
        if card.cardNumber.uppercased().hasPrefix("HY") { return true }
        let c = card.color.lowercased()
        let t = card.cardType.lowercased()
        return c.contains("옐") || c.contains("yell") || c.contains("エール")
            || t.contains("yell") || t.contains("エール")
    }

    // MARK: - HoloDuel Export

    /// (cardNumber, qty, card) 배열 → HoloDuel Base64 코드
    static func exportHoloDuel(entries: [(cardNumber: String, qty: Int, card: DeckCardCandidate)]) -> String? {
        var oshiID: String? = nil
        var deckCards: [(String, Int)] = []
        var cheerCards: [(String, Int)] = []

        for (cardNumber, qty, card) in entries {
            if isOshiCard(card) {
                oshiID = cardNumber
            } else if isYellCard(card) {
                cheerCards.append((cardNumber, qty))
            } else {
                deckCards.append((cardNumber, qty))
            }
        }

        guard let oshi = oshiID else { return nil }

        let deckPart = deckCards.map { "\($0.0)x\($0.1)" }.joined(separator: ",")
        let cheerPart = cheerCards.map { "\($0.0)x\($0.1)" }.joined(separator: ",")
        let raw = "O:\(oshi)|D:\(deckPart)|C:\(cheerPart)"

        return Data(raw.utf8).base64EncodedString()
    }

    // MARK: - HoloDuel Import

    struct HoloDuelDeck {
        let oshiCardNumber: String
        let deckEntries: [(cardNumber: String, qty: Int)]
        let cheerEntries: [(cardNumber: String, qty: Int)]
    }

    static func importHoloDuel(_ code: String) -> HoloDuelDeck? {
        let trimmed = code.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = Data(base64Encoded: trimmed),
              let raw = String(data: data, encoding: .utf8) else { return nil }

        let parts = raw.components(separatedBy: "|")
        guard parts.count == 3 else { return nil }

        guard let oshiPart = parts.first(where: { $0.hasPrefix("O:") }),
              let deckPart = parts.first(where: { $0.hasPrefix("D:") }),
              let cheerPart = parts.first(where: { $0.hasPrefix("C:") }) else { return nil }

        let oshi = String(oshiPart.dropFirst(2))
        guard !oshi.isEmpty else { return nil }

        func parseEntries(_ str: String) -> [(String, Int)]? {
            let body = String(str.dropFirst(2))
            if body.isEmpty { return [] }
            var result: [(String, Int)] = []
            for token in body.components(separatedBy: ",") {
                let p = token.components(separatedBy: "x")
                guard p.count == 2, let qty = Int(p[1]), qty > 0 else { return nil }
                result.append((p[0], qty))
            }
            return result
        }

        guard let deck = parseEntries(deckPart),
              let cheer = parseEntries(cheerPart) else { return nil }

        return HoloDuelDeck(oshiCardNumber: oshi, deckEntries: deck, cheerEntries: cheer)
    }

    // MARK: - 기존 앱 JSON 폴백 임포트 (하위 호환)

    /// HoloDuel base64를 먼저 시도, 실패 시 nil 반환 (caller가 JSON fallback 처리)
    static func importAuto(_ code: String) -> HoloDuelDeck? {
        return importHoloDuel(code)
    }

    // MARK: - Bushiroad (DeckLog) 구조체

    struct BushiDeckCard {
        let cardNumber: String
        let num: Int
        let manageId: String
    }

    struct BushiDeck {
        let deckId: String
        let title: String
        let pList: [BushiDeckCard]
        let list: [BushiDeckCard]
        let subList: [BushiDeckCard]
    }

    // MARK: - DeckLog Fetch (import)

    static func fetchBushiDeck(codeOrURL: String) async throws -> BushiDeck {
        let normalizedCode = normalizeBushiCode(codeOrURL)
        guard !normalizedCode.isEmpty,
              normalizedCode.allSatisfy({ $0.isLetter || $0.isNumber }) else {
            throw DeckCodeError.parseError("올바르지 않은 부시나비 코드입니다.")
        }

        let proxyBaseURL = "https://hocg-deck-convert-api.onrender.com"
        let apiURL = URL(string: "\(proxyBaseURL)/view-deck")!
        var req = URLRequest(url: apiURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", forHTTPHeaderField: "User-Agent")
        let requestBody: [String: Any] = [
            "game_title_id": 9,
            "code": normalizedCode,
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

        let (data, resp) = try await URLSession.shared.data(for: req)
        let statusCode = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard statusCode == 200 else {
            throw DeckCodeError.parseError("HTTP \(statusCode)")
        }

        return try parseBushiResponse(data: data, code: normalizedCode)
    }

    // MARK: - DeckLog Publish (export)

    /// entries: (cardNumber, qty, card) + dbRepository for manage_id
    static func publishBushiDeck(
        entries: [(cardNumber: String, qty: Int, card: DeckCardCandidate)],
        title: String,
        manageIdLookup: (Int64) -> Int?
    ) async throws -> String {
        var oshiList: [[String: Any]] = []
        var mainList: [[String: Any]] = []
        var cheerList: [[String: Any]] = []

        for (cardNumber, qty, card) in entries {
            let mid = manageIdLookup(card.printId).map { "\($0)" } ?? ""
            let item: [String: Any] = ["card_number": cardNumber, "num": qty, "manage_id": mid]
            if isOshiCard(card) {
                oshiList.append(item)
            } else if isYellCard(card) {
                cheerList.append(item)
            } else {
                mainList.append(item)
            }
        }

        let clampedTitle = String(title.prefix(25))
        let body: [String: Any] = [
            "game_title_id": 9,
            "deck_id": "",
            "title": clampedTitle.isEmpty ? "덱" : clampedTitle,
            "p_list": oshiList,
            "list": mainList,
            "sub_list": cheerList,
        ]

        let deckLogBaseURL = "https://decklog.bushiroad.com"
        let proxyBaseURL = "https://hocg-deck-convert-api.onrender.com"
        let apiURL = URL(string: "\(proxyBaseURL)/publish-deck")!
        var req = URLRequest(url: apiURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", forHTTPHeaderField: "User-Agent")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, resp) = try await URLSession.shared.data(for: req)
        let statusCode = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard statusCode == 200 else {
            throw DeckCodeError.publishFailed("HTTP \(statusCode)")
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let deckId = json["deck_id"] as? String, !deckId.isEmpty else {
            let raw = String(data: data, encoding: .utf8) ?? "(empty)"
            throw DeckCodeError.publishFailed(raw.prefix(120).description)
        }

        return "\(deckLogBaseURL)/view/\(deckId)"
    }

    // MARK: - Private helpers

    static func normalizeBushiCode(_ rawInput: String) -> String {
        let trimmed = rawInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "" }
        let lower = trimmed.lowercased()

        let extracted: String
        if lower.hasPrefix("https://decklog-en.bushiroad.com/ja/view/") {
            extracted = String(trimmed.dropFirst("https://decklog-en.bushiroad.com/ja/view/".count))
        } else if lower.hasPrefix("https://decklog-en.bushiroad.com/view/") {
            extracted = String(trimmed.dropFirst("https://decklog-en.bushiroad.com/view/".count))
        } else if lower.hasPrefix("https://decklog.bushiroad.com/view/") {
            extracted = String(trimmed.dropFirst("https://decklog.bushiroad.com/view/".count))
        } else {
            extracted = trimmed
        }

        let withoutQuery = extracted.split(separator: "?", maxSplits: 1, omittingEmptySubsequences: false).first.map(String.init) ?? extracted
        let withoutHash = withoutQuery.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false).first.map(String.init) ?? withoutQuery
        return withoutHash.trimmingCharacters(in: CharacterSet(charactersIn: "/").union(.whitespacesAndNewlines)).lowercased()
    }

    private static func parseBushiResponse(data: Data, code: String) throws -> BushiDeck {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw DeckCodeError.parseError("응답을 파싱할 수 없습니다.")
        }
        guard !(json.isEmpty), let _ = json["deck_id"] else {
            throw DeckCodeError.parseError("덱을 찾을 수 없습니다. 코드: \(code)")
        }

        let deckId = json["deck_id"] as? String ?? code
        let title = json["title"] as? String ?? ""

        func parseList(_ key: String) -> [BushiDeckCard] {
            guard let arr = json[key] as? [[String: Any]] else { return [] }
            return arr.compactMap { item in
                guard let cn = item["card_number"] as? String, !cn.isEmpty else { return nil }
                let num: Int
                if let n = item["num"] as? Int { num = n }
                else if let n = item["num"] as? String, let nInt = Int(n) { num = nInt }
                else { return nil }
                let mid = item["manage_id"] as? String ?? ""
                return BushiDeckCard(cardNumber: cn, num: num, manageId: mid)
            }
        }

        return BushiDeck(
            deckId: deckId,
            title: title,
            pList: parseList("p_list"),
            list: parseList("list"),
            subList: parseList("sub_list")
        )
    }
}

enum DeckCodeError: LocalizedError {
    case noOshi
    case parseError(String)
    case publishFailed(String)

    var errorDescription: String? {
        switch self {
        case .noOshi: return "덱에 오시 카드가 없습니다."
        case .parseError(let s): return "코드 파싱 실패: \(s)"
        case .publishFailed(let s): return "부시나비 업로드 실패: \(s)"
        }
    }
}

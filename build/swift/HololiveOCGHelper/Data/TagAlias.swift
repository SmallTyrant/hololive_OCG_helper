import Foundation

enum TagAlias {
    private static let map: [String: [String]] = [
        "동물귀": ["인권없음"],
        "인권없음": ["동물귀"]
    ]

    static func expanded(query: String) -> Set<String> {
        var result: Set<String> = [query]
        for (key, values) in map {
            if key == query {
                result.formUnion(values)
            } else if values.contains(query) {
                result.insert(key)
            }
        }
        return result
    }
}

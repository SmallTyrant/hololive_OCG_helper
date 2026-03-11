#!/usr/bin/env swift

import Foundation

// GitHub 설정
let githubRepo = "SmallTyrant/hololive_OCG_helper"
let dbReleaseTag = "DB"
let dbReleaseAPI = URL(string: "https://api.github.com/repos/\(githubRepo)/releases/tags/\(dbReleaseTag)")!
let dbDirectURL = URL(string: "https://github.com/\(githubRepo)/releases/download/\(dbReleaseTag)/hololive_ocg.sqlite")!

struct ReleaseDbInfo {
    let tag: String
    let assetName: String
    let assetURL: URL
    let assetUpdatedAt: String
    let publishedAt: String
    let createdAt: String
}

// 테스트 1: GitHub API 호출
func testGitHubAPI() async throws {
    print("📡 테스트 1: GitHub API 호출")
    print("   URL: \(dbReleaseAPI.absoluteString)")
    
    var request = URLRequest(url: dbReleaseAPI)
    request.timeoutInterval = 20
    request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
    request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
    
    let (data, response) = try await URLSession.shared.data(for: request)
    guard let http = response as? HTTPURLResponse else {
        throw URLError(.badServerResponse)
    }
    
    print("   ✅ HTTP 상태 코드: \(http.statusCode)")
    
    guard (200..<300).contains(http.statusCode) else {
        throw URLError(.badServerResponse)
    }
    
    let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any]
    guard let payload else {
        throw URLError(.cannotParseResponse)
    }
    
    let tag = payload["tag_name"] as? String ?? "unknown"
    let assets = payload["assets"] as? [[String: Any]] ?? []
    
    print("   ✅ 태그: \(tag)")
    print("   ✅ Assets 개수: \(assets.count)")
    
    // Asset 찾기
    var foundAsset: (name: String, url: String)?
    for item in assets {
        let name = item["name"] as? String ?? ""
        let urlString = item["browser_download_url"] as? String ?? ""
        if name == "hololive_ocg.sqlite" {
            foundAsset = (name, urlString)
            print("   ✅ DB Asset 발견: \(name)")
            print("   ✅ 다운로드 URL: \(urlString)")
            break
        }
    }
    
    guard foundAsset != nil else {
        throw URLError(.fileDoesNotExist)
    }
}

// 테스트 2: DB 파일 다운로드
func testDBDownload() async throws {
    print("\n📥 테스트 2: DB 파일 다운로드")
    print("   URL: \(dbDirectURL.absoluteString)")
    
    var request = URLRequest(url: dbDirectURL)
    request.timeoutInterval = 120
    request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
    request.setValue("application/octet-stream", forHTTPHeaderField: "Accept")
    
    let (tempURL, response) = try await URLSession.shared.download(for: request)
    guard let http = response as? HTTPURLResponse else {
        throw URLError(.badServerResponse)
    }
    
    print("   ✅ HTTP 상태 코드: \(http.statusCode)")
    
    guard (200..<300).contains(http.statusCode) else {
        throw URLError(.badServerResponse)
    }
    
    let fm = FileManager.default
    let attrs = try fm.attributesOfItem(atPath: tempURL.path)
    let fileSize = attrs[.size] as? Int64 ?? 0
    
    print("   ✅ 다운로드 완료: \(fileSize) bytes (\(Double(fileSize) / 1024.0 / 1024.0) MB)")
    
    // SQLite 헤더 검증
    let data = try Data(contentsOf: tempURL, options: .mappedIfSafe)
    guard data.count > 16 else {
        throw URLError(.cannotDecodeContentData)
    }
    
    let header = Data("SQLite format 3\u{0}".utf8)
    guard data.prefix(16) == header else {
        throw URLError(.cannotDecodeContentData)
    }
    
    print("   ✅ SQLite 헤더 검증 성공")
}

// 테스트 3: Fallback URL 검증
func testFallbackURL() async throws {
    print("\n🔄 테스트 3: Fallback URL 검증")
    print("   Fallback URL: \(dbDirectURL.absoluteString)")
    
    var request = URLRequest(url: dbDirectURL)
    request.httpMethod = "HEAD"
    request.timeoutInterval = 20
    request.setValue("hOCG_H/1.1", forHTTPHeaderField: "User-Agent")
    
    let (_, response) = try await URLSession.shared.data(for: request)
    guard let http = response as? HTTPURLResponse else {
        throw URLError(.badServerResponse)
    }
    
    print("   ✅ HTTP 상태 코드: \(http.statusCode)")
    
    guard (200..<300).contains(http.statusCode) else {
        throw URLError(.badServerResponse)
    }
    
    print("   ✅ Fallback URL 접근 가능")
}

// 메인 실행
Task {
    print("🧪 DB 다운로드 기능 테스트 시작\n")
    print(String(repeating: "=", count: 60))
    
    do {
        try await testGitHubAPI()
        try await testDBDownload()
        try await testFallbackURL()
        
        print("\n" + String(repeating: "=", count: 60))
        print("✅ 모든 테스트 통과!")
        exit(0)
    } catch {
        print("\n" + String(repeating: "=", count: 60))
        print("❌ 테스트 실패: \(error)")
        if let urlError = error as? URLError {
            print("   URLError 코드: \(urlError.code.rawValue)")
            print("   설명: \(urlError.localizedDescription)")
        }
        exit(1)
    }
}

dispatchMain()

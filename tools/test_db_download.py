#!/usr/bin/env python3
"""
Android UpdateRepository 로직을 Python으로 재현하여 테스트
"""

import json
import hashlib
import sys
import urllib.request
from urllib.error import HTTPError, URLError

# GitHub 설정
GITHUB_REPO = "SmallTyrant/hololive_OCG_helper"
DB_RELEASE_TAG = "DB"
DB_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{DB_RELEASE_TAG}"
DB_DIRECT_URL = f"https://github.com/{GITHUB_REPO}/releases/download/{DB_RELEASE_TAG}/hololive_ocg.sqlite"

def normalize_hash(raw):
    value = (raw or "").strip().lower()
    if value.startswith("sha256:"):
        value = value[len("sha256:"):].strip()
    return value

def get_release_asset():
    request = urllib.request.Request(
        DB_RELEASE_API,
        headers={
            "User-Agent": "hOCG_H/1.1",
            "Accept": "application/vnd.github+json"
        }
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status < 200 or response.status >= 300:
            raise Exception(f"HTTP 오류: {response.status}")
        data = json.loads(response.read().decode("utf-8"))

    assets = data.get("assets", [])
    for asset in assets:
        if asset.get("name") == "hololive_ocg.sqlite":
            return {
                "tag": data.get("tag_name", "unknown"),
                "name": asset.get("name", ""),
                "url": asset.get("browser_download_url", DB_DIRECT_URL),
                "digest": normalize_hash(asset.get("digest", "")),
            }

    raise Exception("DB asset을 찾을 수 없습니다")

def test_github_api():
    """테스트 1: GitHub API 호출"""
    print("📡 테스트 1: GitHub API 호출")
    print(f"   URL: {DB_RELEASE_API}")
    
    request = urllib.request.Request(
        DB_RELEASE_API,
        headers={
            "User-Agent": "hOCG_H/1.1",
            "Accept": "application/vnd.github+json"
        }
    )
    
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(f"   ✅ HTTP 상태 코드: {response.status}")
            
            data = json.loads(response.read().decode('utf-8'))
            tag = data.get("tag_name", "unknown")
            assets = data.get("assets", [])

            print(f"   ✅ 태그: {tag}")
            print(f"   ✅ Assets 개수: {len(assets)}")

            asset = get_release_asset()
            print(f"   ✅ DB Asset 발견: {asset['name']}")
            print(f"   ✅ 다운로드 URL: {asset['url']}")
            print(f"   ✅ Digest: {asset['digest'] or '(없음)'}")
                
    except HTTPError as e:
        raise Exception(f"HTTP 오류: {e.code} - {e.reason}")
    except URLError as e:
        raise Exception(f"URL 오류: {e.reason}")

def test_db_download():
    """테스트 2: DB 파일 다운로드"""
    asset = get_release_asset()
    print("\n📥 테스트 2: DB 파일 다운로드")
    print(f"   URL: {asset['url']}")
    
    request = urllib.request.Request(
        asset["url"],
        headers={
            "User-Agent": "hOCG_H/1.1",
            "Accept": "application/octet-stream"
        }
    )
    
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            print(f"   ✅ HTTP 상태 코드: {response.status}")
            
            data = response.read()
            file_size = len(data)
            print(f"   ✅ 다운로드 완료: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            # SQLite 헤더 검증
            if len(data) < 16:
                raise Exception("파일이 너무 작습니다")
            
            header = b"SQLite format 3\x00"
            if data[:16] != header:
                raise Exception("유효한 SQLite 파일이 아닙니다")
            
            print("   ✅ SQLite 헤더 검증 성공")

            actual_digest = hashlib.sha256(data).hexdigest()
            expected_digest = asset["digest"]
            if expected_digest:
                if actual_digest != expected_digest:
                    raise Exception("Digest 검증 실패")
                print(f"   ✅ SHA256 검증 성공: {actual_digest}")
            else:
                print("   ℹ️  Digest 정보 없음 - SHA256 검증 생략")
            
    except HTTPError as e:
        raise Exception(f"HTTP 오류: {e.code} - {e.reason}")
    except URLError as e:
        raise Exception(f"URL 오류: {e.reason}")

def test_fallback_url():
    """테스트 3: Fallback URL 검증"""
    print("\n🔄 테스트 3: Fallback URL 검증")
    print(f"   Fallback URL: {DB_DIRECT_URL}")
    
    request = urllib.request.Request(
        DB_DIRECT_URL,
        headers={"User-Agent": "hOCG_H/1.1"},
        method="HEAD"
    )
    
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(f"   ✅ HTTP 상태 코드: {response.status}")
            print("   ✅ Fallback URL 접근 가능")
            
    except HTTPError as e:
        raise Exception(f"HTTP 오류: {e.code} - {e.reason}")
    except URLError as e:
        raise Exception(f"URL 오류: {e.reason}")

def main():
    print("🧪 DB 다운로드 기능 테스트 시작 (Android 로직)\n")
    print("=" * 60)
    
    try:
        test_github_api()
        test_db_download()
        test_fallback_url()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        return 0
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 테스트 실패: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

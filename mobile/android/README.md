# Android (Kotlin) 앱 제작 가이드

## 권장 스택
- Kotlin
- Jetpack Compose
- Room (SQLite prepackaged DB)
- Hilt (DI)
- Kotlin Coroutines / Flow

## 프로젝트 생성
1. Android Studio에서 **Empty Compose Activity**로 새 프로젝트 생성
2. `minSdk`는 26 이상 권장

## 빌드 방법
### Android Studio
1. `android/` 프로젝트 열기
2. **Build > Make Project** 또는 **Run**으로 디바이스 실행

### CLI (Gradle)
```bash
./gradlew assembleDebug
./gradlew bundleRelease
```

## DB 포함 (Prepackaged SQLite)
1. 현재 저장소의 `data/hololive_ocg.sqlite`를 앱 `assets/`에 복사
2. Room에서 prepackaged DB로 로드

### 예시 (Room DB)
```kotlin
@Database(
    entities = [CardEntity::class, PrintEntity::class, CardTextKoEntity::class],
    version = 1,
    exportSchema = false
)
abstract class HololiveDb : RoomDatabase() {
    abstract fun cardDao(): CardDao
}

fun provideDatabase(context: Context): HololiveDb =
    Room.databaseBuilder(context, HololiveDb::class.java, "hololive_ocg.sqlite")
        .createFromAsset("hololive_ocg.sqlite")
        .fallbackToDestructiveMigration()
        .build()
```

## 기본 화면 흐름 (예시)
1. 카드 리스트 화면 (필터/검색)
2. 카드 상세 화면 (이미지/텍스트)
3. 덱 빌더 화면

## 할 일 체크리스트
- [ ] 카드/프린트/텍스트 모델 정의
- [ ] 카드 검색/필터 쿼리 작성
- [ ] 이미지 로딩(로컬 or 원격) 전략 결정
- [ ] 리스트/상세 UI 구현
- [ ] 상태 관리 구조 결정 (예: ViewModel + StateFlow)

## 데이터 접근 팁
- 스키마 변경 금지
- 필드명은 DB 스키마에 맞춰 Entity를 정의
- 검색/필터는 SQL에서 처리하는 것을 우선

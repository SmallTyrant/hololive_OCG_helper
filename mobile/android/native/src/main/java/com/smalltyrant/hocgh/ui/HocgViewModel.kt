package com.smalltyrant.hocgh.ui

import android.app.Application
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smalltyrant.hocgh.data.AppPaths
import com.smalltyrant.hocgh.data.DbRepository
import com.smalltyrant.hocgh.data.formatIsoDateOrNull
import com.smalltyrant.hocgh.data.ImageRepository
import com.smalltyrant.hocgh.data.UpdateRepository
import com.smalltyrant.hocgh.model.AppUpdateDialogState
import com.smalltyrant.hocgh.model.DeckCardCandidate
import com.smalltyrant.hocgh.model.HocgUiState
import com.smalltyrant.hocgh.model.ImageState
import com.smalltyrant.hocgh.model.UpdateDialogState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext

private const val DB_MISSING_TOAST = "DB파일이 존재하지 않습니다. 메뉴에서 DB 수동갱신을 실행해주세요"
private const val DB_UPDATING_TOAST = "갱신중..."
private const val DB_UPDATED_TOAST = "갱신완료"
private const val DB_RESTORED_TOAST = "번들 DB 복원완료"
private const val APP_UPDATE_AVAILABLE_TOAST = "앱 업데이트가 있습니다"
private const val BULK_IMAGE_MAX_CONCURRENCY = 10
private const val BULK_IMAGE_RETRY_COUNT = 1
private const val DETAIL_PREFETCH_MAX_CONCURRENCY = 4
private const val DETAIL_PREFETCH_LIMIT = 20

class HocgViewModel(application: Application) : AndroidViewModel(application) {

    private data class BulkImageOutcome(
        val downloaded: Int,
        val cached: Int,
        val failed: Int,
        val skipped: Int,
    )

    private val paths = AppPaths(application)
    private val dbRepository = DbRepository(paths)
    private val imageRepository = ImageRepository(paths)
    private val updateRepository = UpdateRepository()

    var state by mutableStateOf(HocgUiState(dbPath = paths.dbFile.absolutePath))
        private set

    var multiWordTags by mutableStateOf<List<String>>(emptyList())
        private set

    private val _toastEvents = MutableSharedFlow<String>(extraBufferCapacity = 32)
    val toastEvents = _toastEvents.asSharedFlow()

    private var searchJob: Job? = null
    private var detailJob: Job? = null
    private var prefetchJob: Job? = null
    private var remotePromptMarker: String? = null
    private var appUpdatePromptShown = false

    init {
        viewModelScope.launch {
            bootstrap()
        }
    }

    fun onSearchQueryChanged(query: String) {
        state = state.copy(searchQuery = query)
        refreshList()
    }

    fun onSelectPrint(printId: Long) {
        if (state.selectedPrintId == printId && state.detailLoading) {
            return
        }
        showDetail(printId)
    }

    fun onToggleImagePanel() {
        state = state.copy(imageCollapsed = !state.imageCollapsed)
    }

    fun onSelectIllustration(rarity: String, imageUrl: String) {
        val printId = state.selectedPrintId ?: return
        val cardNumber = state.selectedCardNumber.trim()
        if (cardNumber.isEmpty()) return

        detailJob?.cancel()
        detailJob = viewModelScope.launch {
            state = state.copy(selectedRarity = rarity, imageState = ImageState.Loading)
            val loadedImageState = withContext(Dispatchers.IO) {
                imageRepository.downloadIfNeeded(cardNumber, imageUrl, rarity)
            }
            if (state.selectedPrintId == printId && state.selectedRarity == rarity) {
                state = state.copy(imageState = loadedImageState)
            }
        }
    }

    fun onUpdateDialogDismiss() {
        state = state.copy(updateDialog = null)
    }

    fun onUpdateDialogConfirm() {
        state = state.copy(updateDialog = null)
        onManualUpdate()
    }

    fun onAppUpdateDialogDismiss() {
        state = state.copy(appUpdateDialog = null)
    }

    fun onAppUpdateDialogConfirm() {
        val dialog = state.appUpdateDialog ?: return
        state = state.copy(appUpdateDialog = null)

        val uri = runCatching { Uri.parse(dialog.downloadUrl) }.getOrNull() ?: return
        val intent = Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        runCatching {
            getApplication<Application>().startActivity(intent)
        }
    }

    fun onManualUpdate() {
        if (state.updateRunning) {
            return
        }
        viewModelScope.launch {
            if (state.dbPath.isBlank()) {
                state = state.copy(updateStatus = "DB 경로가 비어 있습니다.", updateStatusError = true)
                pushToast("DB 경로가 비어 있습니다.")
                return@launch
            }

            state = state.copy(
                updateRunning = true,
                updateStatus = "DB 갱신 중...",
                updateStatusError = false,
            )
            pushToast(DB_UPDATING_TOAST)

            try {
                withContext(Dispatchers.IO) {
                    updateRepository.downloadLatestDb(paths.dbFile)
                }
                state = state.copy(
                    updateStatus = "DB 갱신 완료",
                    updateStatusError = false,
                    persistentMessage = null,
                )
                pushToast(DB_UPDATED_TOAST)
                multiWordTags = withContext(Dispatchers.IO) {
                    dbRepository.loadMultiWordTags()
                }
                refreshList()
            } catch (ex: Throwable) {
                val message = "DB 갱신 실패: ${ex.message ?: ex.javaClass.simpleName}"
                state = state.copy(updateStatus = message, updateStatusError = true)
                pushToast(message)

                val recovered = withContext(Dispatchers.IO) {
                    val missingBeforeRecover = dbRepository.needsDbUpdate()
                    if (!missingBeforeRecover) {
                        return@withContext false
                    }
                    paths.restoreBundledDb() && !dbRepository.needsDbUpdate()
                }
                if (recovered) {
                    state = state.copy(
                        updateStatus = "DB 복원 완료",
                        updateStatusError = false,
                        persistentMessage = null,
                    )
                    pushToast(DB_RESTORED_TOAST)
                    refreshList()
                } else {
                    val stillMissing = withContext(Dispatchers.IO) {
                        dbRepository.needsDbUpdate()
                    }
                    if (stillMissing) {
                        applyMissingDbState()
                    }
                }
            } finally {
                state = state.copy(updateRunning = false)
            }
        }
    }

    fun onBulkImageDownload() {
        if (state.updateRunning) {
            return
        }
        viewModelScope.launch {
            if (state.dbPath.isBlank()) {
                state = state.copy(updateStatus = "DB 경로가 비어 있습니다.", updateStatusError = true)
                pushToast("DB 경로가 비어 있습니다.")
                return@launch
            }

            state = state.copy(
                updateRunning = true,
                updateStatus = "이미지 일괄 다운로드 준비 중...",
                updateStatusError = false,
            )
            pushToast("이미지 일괄 다운로드 시작")

            try {
                val targets = withContext(Dispatchers.IO) {
                    dbRepository.listImageTargets()
                }
                if (targets.isEmpty()) {
                    val message = "다운로드할 이미지가 없습니다."
                    state = state.copy(updateStatus = message, updateStatusError = false)
                    pushToast(message)
                    return@launch
                }

                var downloaded = 0
                var alreadyCached = 0
                var failed = 0
                var skipped = 0
                var completed = 0

                state = state.copy(updateStatus = "이미지 다운로드 중... (0/${targets.size})")
                val semaphore = Semaphore(BULK_IMAGE_MAX_CONCURRENCY)
                coroutineScope {
                    val jobs = targets.map { target ->
                        async(Dispatchers.IO) {
                            semaphore.withPermit {
                                downloadBulkImageTarget(target)
                            }
                        }
                    }

                    jobs.forEach { job ->
                        val outcome = job.await()
                        completed += 1
                        downloaded += outcome.downloaded
                        alreadyCached += outcome.cached
                        failed += outcome.failed
                        skipped += outcome.skipped
                        state = state.copy(updateStatus = "이미지 다운로드 중... (${completed}/${targets.size})")
                    }
                }

                val message = "이미지 다운로드 완료: 신규 ${downloaded}건 / 기존 ${alreadyCached}건 / 실패 ${failed}건 / 건너뜀 ${skipped}건"
                state = state.copy(
                    updateStatus = message,
                    updateStatusError = failed > 0,
                )
                pushToast(message)
                state.selectedPrintId?.let { selected ->
                    showDetail(selected)
                }
            } catch (ex: Throwable) {
                val message = "이미지 다운로드 실패: ${ex.message ?: ex.javaClass.simpleName}"
                state = state.copy(updateStatus = message, updateStatusError = true)
                pushToast(message)
            } finally {
                state = state.copy(updateRunning = false)
            }
        }
    }

    private suspend fun bootstrap() {
        withContext(Dispatchers.IO) {
            paths.copyBundledDbIfMissing()
        }

        val missing = withContext(Dispatchers.IO) { dbRepository.needsDbUpdate() }

        if (missing) {
            // DB 파일이 없거나 스키마가 유효하지 않으면 자동으로 다운로드 시작.
            // 사용자가 수동으로 메뉴를 찾아야 하는 불편함 제거.
            state = state.copy(updateStatus = "DB를 다운로드하는 중입니다...")
            onManualUpdate()
            // onManualUpdate() 내부에서 refreshList() 호출하므로 이후 로직 불필요.
            return
        }

        multiWordTags = withContext(Dispatchers.IO) {
            dbRepository.loadMultiWordTags()
        }

        refreshList()
        checkAppUpdateOnce()
        checkRemoteUpdateOnce()
    }

    private fun refreshList() {
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            val query = state.searchQuery.trim()
            if (query.isEmpty()) {
                prefetchJob?.cancel()
                state = state.copy(
                    results = emptyList(),
                    selectedPrintId = null,
                    selectedCardNumber = "",
                    selectedImageUrl = "",
                    selectedRarity = "",
                    selectedIllustrations = emptyList(),
                    detailKoText = "",
                    detailJaText = "",
                    detailLoading = false,
                    imageState = ImageState.Placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다."),
                )
                return@launch
            }

            delay(120)

            val needsUpdate = withContext(Dispatchers.IO) {
                dbRepository.needsDbUpdate()
            }
            if (needsUpdate) {
                prefetchJob?.cancel()
                applyMissingDbState()
                state = state.copy(
                    results = emptyList(),
                    selectedPrintId = null,
                    selectedCardNumber = "",
                    selectedImageUrl = "",
                    selectedRarity = "",
                    selectedIllustrations = emptyList(),
                    detailKoText = "",
                    detailJaText = "",
                    detailLoading = false,
                    imageState = ImageState.Placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다."),
                )
                return@launch
            }

            val rows = withContext(Dispatchers.IO) {
                dbRepository.querySuggest(query)
            }

            val selectedBefore = state.selectedPrintId

            state = state.copy(
                results = rows,
                persistentMessage = null,
            )

            if (selectedBefore != null && rows.any { it.printId == selectedBefore }) {
                showDetail(selectedBefore)
                prefetchCardDetails(rows = rows, excludingPrintId = selectedBefore)
                return@launch
            }

            val first = rows.firstOrNull()
            if (first == null) {
                prefetchJob?.cancel()
                state = state.copy(
                    selectedPrintId = null,
                    selectedCardNumber = "",
                    selectedImageUrl = "",
                    selectedRarity = "",
                    selectedIllustrations = emptyList(),
                    detailKoText = "",
                    detailJaText = "",
                    detailLoading = false,
                    imageState = ImageState.Placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다."),
                )
            } else {
                showDetail(first.printId)
                prefetchCardDetails(rows = rows, excludingPrintId = first.printId)
            }
        }
    }

    private fun showDetail(printId: Long) {
        detailJob?.cancel()
        detailJob = viewModelScope.launch {
            state = state.copy(
                selectedPrintId = printId,
                selectedCardNumber = "",
                selectedImageUrl = "",
                selectedRarity = "",
                selectedIllustrations = emptyList(),
                detailKoText = "",
                detailJaText = "",
                detailLoading = true,
            )

            val snapshot = withContext(Dispatchers.IO) {
                dbRepository.loadCardSnapshot(printId)
            }

            if (state.selectedPrintId != printId) {
                return@launch
            }

            if (snapshot == null) {
                state = state.copy(
                    detailKoText = "[ERROR] 상세 로드 실패",
                    detailJaText = "",
                    detailLoading = false,
                    selectedCardNumber = "",
                    selectedImageUrl = "",
                    selectedRarity = "",
                    selectedIllustrations = emptyList(),
                    imageState = ImageState.Error("이미지 로딩 실패"),
                )
                return@launch
            }

            val defaultIllustration = snapshot.brief.illustrations.firstOrNull()
            val selectedRarity = defaultIllustration?.rarity.orEmpty()
            val selectedImageUrl = defaultIllustration?.imageUrl?.takeIf { it.isNotBlank() } ?: snapshot.brief.imageUrl

            state = state.copy(
                selectedCardNumber = snapshot.brief.cardNumber,
                selectedImageUrl = selectedImageUrl,
                selectedRarity = selectedRarity,
                selectedIllustrations = snapshot.brief.illustrations,
                detailKoText = snapshot.detail.koText,
                detailJaText = snapshot.detail.jaText,
                detailLoading = false,
                imageState = if (snapshot.brief.cardNumber.isBlank()) {
                    ImageState.Placeholder("이미지 없음")
                } else {
                    ImageState.Loading
                },
            )

            if (snapshot.brief.cardNumber.isBlank()) {
                return@launch
            }

            val loadedImageState = withContext(Dispatchers.IO) {
                imageRepository.downloadIfNeeded(snapshot.brief.cardNumber, selectedImageUrl, selectedRarity)
            }

            if (state.selectedPrintId == printId) {
                state = state.copy(imageState = loadedImageState)
            }
        }
    }

    private fun prefetchCardDetails(rows: List<com.smalltyrant.hocgh.model.PrintRow>, excludingPrintId: Long?) {
        prefetchJob?.cancel()

        val targets = rows
            .asSequence()
            .map { it.printId }
            .filter { printId -> excludingPrintId == null || printId != excludingPrintId }
            .distinct()
            .take(DETAIL_PREFETCH_LIMIT)
            .toList()

        if (targets.isEmpty()) {
            return
        }

        prefetchJob = viewModelScope.launch(Dispatchers.IO) {
            val semaphore = Semaphore(DETAIL_PREFETCH_MAX_CONCURRENCY)
            coroutineScope {
                targets.map { printId ->
                    async {
                        semaphore.withPermit {
                            dbRepository.loadCardSnapshot(printId)
                        }
                    }
                }.awaitAll()
            }
        }
    }

    private fun checkAppUpdateOnce() {
        if (appUpdatePromptShown) {
            return
        }

        viewModelScope.launch {
            val application = getApplication<Application>()
            val localPackageInfo = runCatching {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
                    application.packageManager.getPackageInfo(
                        application.packageName,
                        PackageManager.PackageInfoFlags.of(0),
                    )
                } else {
                    @Suppress("DEPRECATION")
                    application.packageManager.getPackageInfo(application.packageName, 0)
                }
            }.getOrNull() ?: return@launch

            val localCode = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
                localPackageInfo.longVersionCode
            } else {
                @Suppress("DEPRECATION")
                localPackageInfo.versionCode.toLong()
            }
            val localName = localPackageInfo.versionName.orEmpty()

            val remoteInfo = withContext(Dispatchers.IO) {
                updateRepository.fetchLatestApkInfo()
            }

            if (remoteInfo.versionCode <= localCode) {
                return@launch
            }

            appUpdatePromptShown = true
            state = state.copy(
                appUpdateDialog = AppUpdateDialogState(
                    localVersionName = localName,
                    localVersionCode = localCode,
                    remoteVersionName = remoteInfo.versionName,
                    remoteVersionCode = remoteInfo.versionCode,
                    downloadUrl = remoteInfo.assetUrl,
                ),
            )
            pushToast(APP_UPDATE_AVAILABLE_TOAST)
        }
    }

    private fun checkRemoteUpdateOnce() {
        viewModelScope.launch {
            val dbPath = state.dbPath.trim()
            if (dbPath.isEmpty()) {
                return@launch
            }

            val localDateDeferred = async(Dispatchers.IO) { dbRepository.localDbDate() }
            val localDigestDeferred = async(Dispatchers.IO) { dbRepository.localDbDigest() }
            val remoteInfo = withContext(Dispatchers.IO) {
                runCatching { updateRepository.getLatestReleaseDbInfo() }.getOrNull()
            } ?: return@launch

            val remoteDate = formatIsoDateOrNull(
                remoteInfo.assetUpdatedAt.ifEmpty {
                    remoteInfo.publishedAt.ifEmpty { remoteInfo.createdAt }
                },
            ) ?: return@launch
            val remoteDigest = remoteInfo.assetDigest.ifBlank { null }
            val localDate = localDateDeferred.await()
            val localDigest = localDigestDeferred.await()
            val remoteMarker = remoteDigest ?: remoteInfo.assetUpdatedAt.ifEmpty { remoteDate }

            val needsPrompt = if (!remoteDigest.isNullOrBlank()) {
                remoteDigest != localDigest
            } else {
                remoteDate != localDate
            }

            if (!needsPrompt) {
                return@launch
            }
            if (remotePromptMarker == remoteMarker) {
                return@launch
            }

            if (state.appUpdateDialog != null) {
                return@launch
            }

            remotePromptMarker = remoteMarker
            state = state.copy(
                updateDialog = UpdateDialogState(
                    localDate = localDate,
                    remoteDate = remoteDate,
                    localDigest = localDigest,
                    remoteDigest = remoteDigest,
                ),
            )
        }
    }

    private fun applyMissingDbState() {
        state = state.copy(persistentMessage = DB_MISSING_TOAST)
        pushToast(DB_MISSING_TOAST)
    }

    private suspend fun downloadBulkImageTarget(target: DbRepository.ImageTarget): BulkImageOutcome {
        val localFile = paths.localImageFile(target.cardNumber)
        val existedBefore = localFile.exists()

        var imageState = imageRepository.downloadIfNeeded(target.cardNumber, target.imageUrl)
        var retryCount = 0
        while (imageState is ImageState.Error && retryCount < BULK_IMAGE_RETRY_COUNT) {
            retryCount += 1
            delay(120)
            imageState = imageRepository.downloadIfNeeded(target.cardNumber, target.imageUrl)
        }

        return when (imageState) {
            is ImageState.Local -> {
                if (existedBefore) {
                    BulkImageOutcome(downloaded = 0, cached = 1, failed = 0, skipped = 0)
                } else {
                    BulkImageOutcome(downloaded = 1, cached = 0, failed = 0, skipped = 0)
                }
            }
            is ImageState.Error -> BulkImageOutcome(downloaded = 0, cached = 0, failed = 1, skipped = 0)
            else -> BulkImageOutcome(downloaded = 0, cached = 0, failed = 0, skipped = 1)
        }
    }

    fun getDbRepository(): DbRepository = dbRepository

    suspend fun searchDeckCards(query: String, limit: Int = 240): List<DeckCardCandidate> {
        return withContext(Dispatchers.IO) {
            dbRepository.listDeckCards(query, limit).map { candidate ->
                candidate.copy(
                    imageUrl = paths.resolveImageUrl(candidate.imageUrl),
                    illustrations = candidate.illustrations.map { option ->
                        option.copy(imageUrl = paths.resolveImageUrl(option.imageUrl))
                    },
                )
            }
        }
    }

    private fun pushToast(message: String) {
        _toastEvents.tryEmit(message)
    }
}

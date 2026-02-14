package com.smalltyrant.hocgh.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.smalltyrant.hocgh.data.AppPaths
import com.smalltyrant.hocgh.data.DbRepository
import com.smalltyrant.hocgh.data.ImageRepository
import com.smalltyrant.hocgh.data.UpdateRepository
import com.smalltyrant.hocgh.model.HocgUiState
import com.smalltyrant.hocgh.model.ImageState
import com.smalltyrant.hocgh.model.UpdateDialogState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val DB_MISSING_TOAST = "DB파일이 존재하지 않습니다. 메뉴에서 DB 수동갱신을 실행해주세요"
private const val DB_UPDATING_TOAST = "갱신중..."
private const val DB_UPDATED_TOAST = "갱신완료"
private const val DB_RESTORED_TOAST = "번들 DB 복원완료"

class HocgViewModel(application: Application) : AndroidViewModel(application) {

    private val paths = AppPaths(application)
    private val dbRepository = DbRepository(paths)
    private val imageRepository = ImageRepository(paths)
    private val updateRepository = UpdateRepository()

    var state by mutableStateOf(HocgUiState(dbPath = paths.dbFile.absolutePath))
        private set

    private val _toastEvents = MutableSharedFlow<String>(extraBufferCapacity = 32)
    val toastEvents = _toastEvents.asSharedFlow()

    private var searchJob: Job? = null
    private var detailJob: Job? = null
    private var remotePromptShown = false

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
        showDetail(printId)
    }

    fun onToggleImagePanel() {
        state = state.copy(imageCollapsed = !state.imageCollapsed)
    }

    fun onUpdateDialogDismiss() {
        state = state.copy(updateDialog = null)
    }

    fun onUpdateDialogConfirm() {
        state = state.copy(updateDialog = null)
        onManualUpdate()
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

                targets.forEachIndexed { index, target ->
                    state = state.copy(updateStatus = "이미지 다운로드 중... (${index + 1}/${targets.size})")
                    val (existedBefore, imageState) = withContext(Dispatchers.IO) {
                        val localFile = paths.localImageFile(target.cardNumber)
                        val existed = localFile.exists()
                        val downloadedState = imageRepository.downloadIfNeeded(target.cardNumber, target.imageUrl)
                        existed to downloadedState
                    }
                    when (imageState) {
                        is ImageState.Local -> {
                            if (existedBefore) {
                                alreadyCached += 1
                            } else {
                                downloaded += 1
                            }
                        }
                        is ImageState.Error -> failed += 1
                        else -> skipped += 1
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

        if (withContext(Dispatchers.IO) { dbRepository.needsDbUpdate() }) {
            applyMissingDbState()
        }

        refreshList()
        checkRemoteUpdateOnce()
    }

    private fun refreshList() {
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            val query = state.searchQuery.trim()
            if (query.isEmpty()) {
                state = state.copy(
                    results = emptyList(),
                    selectedPrintId = null,
                    detailKoText = "",
                    imageState = ImageState.Placeholder("카드를 선택하세요"),
                )
                return@launch
            }

            val needsUpdate = withContext(Dispatchers.IO) {
                dbRepository.needsDbUpdate()
            }
            if (needsUpdate) {
                applyMissingDbState()
                state = state.copy(
                    results = emptyList(),
                    selectedPrintId = null,
                    detailKoText = "",
                    imageState = ImageState.Placeholder("카드를 선택하세요"),
                )
                return@launch
            }

            val rows = withContext(Dispatchers.IO) {
                dbRepository.querySuggest(query)
            }

            state = state.copy(
                results = rows,
                persistentMessage = null,
            )

            val first = rows.firstOrNull()
            if (first == null) {
                state = state.copy(
                    selectedPrintId = null,
                    detailKoText = "",
                    imageState = ImageState.Placeholder("카드를 선택하세요"),
                )
            } else {
                showDetail(first.printId)
            }
        }
    }

    private fun showDetail(printId: Long) {
        detailJob?.cancel()
        detailJob = viewModelScope.launch {
            state = state.copy(selectedPrintId = printId)

            val briefDeferred = async(Dispatchers.IO) {
                dbRepository.getPrintBrief(printId)
            }
            val detailDeferred = async(Dispatchers.IO) {
                dbRepository.loadCardDetail(printId)
            }
            val brief = briefDeferred.await()
            val detail = detailDeferred.await()

            if (brief == null) {
                state = state.copy(
                    detailKoText = "[ERROR] 상세 로드 실패",
                    imageState = ImageState.Error("이미지 로딩 실패"),
                )
                return@launch
            }

            state = state.copy(
                detailKoText = detail?.koText.orEmpty(),
                imageState = if (brief.cardNumber.isBlank()) {
                    ImageState.Placeholder("이미지 없음")
                } else {
                    ImageState.Loading
                },
            )

            if (brief.cardNumber.isBlank()) {
                return@launch
            }

            val loadedImageState = withContext(Dispatchers.IO) {
                imageRepository.downloadIfNeeded(brief.cardNumber, brief.imageUrl)
            }

            if (state.selectedPrintId == printId) {
                state = state.copy(imageState = loadedImageState)
            }
        }
    }

    private fun checkRemoteUpdateOnce() {
        if (remotePromptShown) {
            return
        }

        viewModelScope.launch {
            val dbPath = state.dbPath.trim()
            if (dbPath.isEmpty()) {
                return@launch
            }

            val localDate = withContext(Dispatchers.IO) {
                dbRepository.localDbDate()
            }
            val remoteDate = withContext(Dispatchers.IO) {
                updateRepository.fetchRemoteDbDate()
            }

            if (remoteDate.isNullOrBlank()) {
                return@launch
            }
            if (remoteDate == localDate) {
                return@launch
            }

            remotePromptShown = true
            state = state.copy(
                updateDialog = UpdateDialogState(
                    localDate = localDate,
                    remoteDate = remoteDate,
                ),
            )
        }
    }

    private fun applyMissingDbState() {
        state = state.copy(persistentMessage = DB_MISSING_TOAST)
        pushToast(DB_MISSING_TOAST)
    }

    private fun pushToast(message: String) {
        _toastEvents.tryEmit(message)
    }
}

package com.smalltyrant.hocgh.model

import java.io.File

enum class SearchMode {
    PARTIAL,
    EXACT,
}

data class PrintRow(
    val printId: Long,
    val cardNumber: String,
    val nameJa: String,
    val nameKo: String,
)

data class PrintBrief(
    val printId: Long,
    val cardNumber: String,
    val nameJa: String,
    val nameKo: String,
    val imageUrl: String,
)

data class CardDetail(
    val koText: String,
    val jaText: String,
)

data class CardSnapshot(
    val brief: PrintBrief,
    val detail: CardDetail,
)

data class UpdateDialogState(
    val localDate: String?,
    val remoteDate: String,
)

data class AppUpdateDialogState(
    val localVersionName: String,
    val localVersionCode: Long,
    val remoteVersionName: String,
    val remoteVersionCode: Long,
    val downloadUrl: String,
)


data class DeckCardCandidate(
    val printId: Long,
    val cardNumber: String,
    val nameJa: String,
    val nameKo: String,
    val imageUrl: String,
    val cardType: String,
    val color: String,
    val rarity: String,
    val koText: String,
    val jaText: String,
)

data class DeckEntryRecord(
    val printId: Long,
    val cardNumber: String,
    val qty: Int,
)

data class SavedDeckRecord(
    val id: String,
    val title: String,
    val entries: List<DeckEntryRecord>,
    val updatedAt: Long,
)

data class DeckLibraryRecord(
    val version: Int = 1,
    val decks: List<SavedDeckRecord> = emptyList(),
)

sealed interface ImageState {
    data class Local(val file: File) : ImageState
    data class Remote(val url: String) : ImageState
    data object Loading : ImageState
    data class Placeholder(val message: String) : ImageState
    data class Error(val message: String) : ImageState
}

data class HocgUiState(
    val dbPath: String = "",
    val searchQuery: String = "",
    val searchMode: SearchMode = SearchMode.PARTIAL,
    val results: List<PrintRow> = emptyList(),
    val selectedPrintId: Long? = null,
    val detailKoText: String = "",
    val detailJaText: String = "",
    val detailLoading: Boolean = false,
    val imageState: ImageState = ImageState.Placeholder("카드를 검색 후 선택하면 이미지가 표시됩니다."),
    val imageCollapsed: Boolean = false,
    val updateRunning: Boolean = false,
    val updateStatus: String = "",
    val updateStatusError: Boolean = false,
    val persistentMessage: String? = null,
    val updateDialog: UpdateDialogState? = null,
    val appUpdateDialog: AppUpdateDialogState? = null,
)

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
)

data class UpdateDialogState(
    val localDate: String?,
    val remoteDate: String,
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
    val imageState: ImageState = ImageState.Placeholder("카드를 선택하세요"),
    val imageCollapsed: Boolean = false,
    val updateRunning: Boolean = false,
    val updateStatus: String = "",
    val updateStatusError: Boolean = false,
    val persistentMessage: String? = null,
    val updateDialog: UpdateDialogState? = null,
)

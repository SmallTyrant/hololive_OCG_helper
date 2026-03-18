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


/** 레어리티별 일러스트 정보 (card_illustrations 테이블) */
data class IllustrationOption(
    val rarity: String,
    val manageIdJp: Int?,
    val imageUrl: String,  // 비어있으면 DeckCardCandidate.imageUrl 사용
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
    /** 선택 가능한 레어리티 목록. 1개면 선택 UI 불필요. */
    val illustrations: List<IllustrationOption> = emptyList(),
) {
    val selectableIllustrations: List<IllustrationOption>
        get() = illustrations.filter { it.imageUrl.trim().isNotEmpty() }

    val hasMultipleRarities: Boolean get() = selectableIllustrations.size > 1
}

data class DeckEntryRecord(
    val printId: Long,
    val cardNumber: String,
    val qty: Int,
    /** 사용자가 선택한 레어리티. null 이면 기본 레어리티 사용. */
    val selectedRarity: String? = null,
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

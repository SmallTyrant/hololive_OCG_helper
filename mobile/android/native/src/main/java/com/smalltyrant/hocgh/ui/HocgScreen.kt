package com.smalltyrant.hocgh.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Intent
import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BrokenImage
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.VerticalDivider
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.focus.FocusManager
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.input.ImeAction
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.core.graphics.drawable.toBitmap
import coil.compose.AsyncImage
import coil.ImageLoader
import coil.request.ImageRequest
import coil.request.SuccessResult
import com.smalltyrant.hocgh.data.AppPaths
import com.smalltyrant.hocgh.data.DeckCodeConverter
import com.smalltyrant.hocgh.data.DeckStorage
import com.smalltyrant.hocgh.data.DbRepository
import com.smalltyrant.hocgh.model.DeckEntryRecord
import com.smalltyrant.hocgh.model.HocgUiState
import com.smalltyrant.hocgh.model.ImageState
import com.smalltyrant.hocgh.model.DeckLibraryRecord
import com.smalltyrant.hocgh.model.PrintRow
import com.smalltyrant.hocgh.model.DeckCardCandidate
import com.smalltyrant.hocgh.model.SavedDeckRecord
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import java.util.Locale
import java.util.UUID

private val SECTION_LABELS = listOf(
    "서포트 / 아이템",
    "서포트 / 스태프",
    "서포트 / 이벤트",
    "서포트 / 툴",
    "서포트 / 마스코트",
    "서포트 / 팬",
    "SP 오시 스킬",
    "오시 스테이지 스킬",
    "오시 스킬",
    "콜라보 이펙트",
    "블룸 이펙트",
    "기프트",
    "태그",
    "카드 타입",
    "카드타입",
    "레어리티",
    "아츠",
    "엑스트라",
    "Bloom 레벨",
    "키워드",
    "속성",
    "레벨",
    "배턴 터치",
    "SP推しスキル",
    "推しステージスキル",
    "推しスキル",
    "カードタイプ",
    "タグ",
    "レアリティ",
    "能力テキスト",
    "色",
    "アーツ",
    "エクストラ",
    "Bloomレベル",
    "キーワード",
    "バトンタッチ",
    "LIFE",
    "HP",
)
private val SECTION_LABELS_SORTED = SECTION_LABELS.sortedByDescending { it.length }
private val JAPANESE_CHAR_REGEX = Regex("[\\u3040-\\u30ff\\u31f0-\\u31ff\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff々〆ヵヶ]")
private val KO_SECTION_MARKER_REGEX = Regex(
    "서포트 / 아이템|서포트 / 스태프|서포트 / 이벤트|서포트 / 툴|서포트 / 마스코트|서포트 / 팬|SP 오시 스킬|오시 스테이지 스킬|오시 스킬|콜라보 이펙트|블룸 이펙트|기프트|엑스트라|아츠(?=\\s+(?![+\\-]\\d)\\S)|#",
)
private val JA_SECTION_MARKER_REGEX = Regex(
    "SP推しスキル|推しステージスキル|推しスキル|コラボエフェクト|ブルームエフェクト|ギフト|エクストラ|アーツ(?=\\s+(?![+\\-]\\d)\\S)|カードタイプ|タグ|レアリティ|能力テキスト|バトンタッチ|#",
)
private val TAG_TOKEN_REGEX = Regex("#[^\\s#]+")
private val JA_TAG_OBJECT_SPLIT_REGEX = Regex("^(#[^\\s#を]+(?:\\s+[^\\s#を]+)*)(を.+)$")
private val KO_METADATA_TOKEN_SET = setOf(
    "레벨",
    "속성",
    "hp",
    "life",
    "배턴",
    "터치",
    "배턴터치",
    "1st",
    "2nd",
    "debut",
    "buzz",
)
private val JA_METADATA_TOKEN_SET = setOf(
    "レベル",
    "hp",
    "life",
    "1st",
    "2nd",
    "debut",
    "buzz",
)
private val KO_DETAIL_REPLACEMENTS = listOf(
    "【콜라보 이펙트】" to "콜라보 이펙트",
    "【블룸 이펙트】" to "블룸 이펙트",
    "【기프트】" to "기프트",
)
private val JA_DETAIL_REPLACEMENTS = listOf(
    "【SP推しスキル】" to "SP推しスキル",
    "【推しスキル】" to "推しスキル",
    "【コラボエフェクト】" to "コラボエフェクト",
    "【ブルームエフェクト】" to "ブルームエフェクト",
    "【ギフト】" to "ギフト",
    "【エクストラ】" to "エクストラ",
    "【アーツ】" to "アーツ",
    "【カードタイプ】" to "カードタイプ",
    "【タグ】" to "タグ",
    "【レアリティ】" to "レアリティ",
    "【能力テキスト】" to "能力テキスト",
    "【バトンタッチ】" to "バトンタッチ",
    "【色】" to "色",
)
private val KO_LINE_BREAK_PATTERNS = listOf(
    Regex("\\s*SP 오시 스킬\\s*") to "\nSP 오시 스킬\n",
    Regex("\\s*오시 스테이지 스킬\\s*") to "\n오시 스테이지 스킬\n",
    Regex("\\s*(?<!SP )오시 스킬\\s*") to "\n오시 스킬\n",
    Regex("\\s*콜라보 이펙트\\s*") to "\n콜라보 이펙트\n",
    Regex("\\s*블룸 이펙트\\s*") to "\n블룸 이펙트\n",
    Regex("\\s*기프트\\s*") to "\n기프트\n",
    Regex("\\s*엑스트라\\s*") to "\n엑스트라\n",
    Regex("\\s*아츠(?=\\s+(?![+\\-]\\d)\\S)\\s*") to "\n아츠\n",
    Regex("\\s+#") to "\n#",
)
private val JA_LINE_BREAK_PATTERNS = listOf(
    Regex("\\s*SP推しスキル\\s*") to "\nSP推しスキル\n",
    Regex("\\s*推しステージスキル\\s*") to "\n推しステージスキル\n",
    Regex("\\s*(?<!SP)推しスキル\\s*") to "\n推しスキル\n",
    Regex("\\s*コラボエフェクト\\s*") to "\nコラボエフェクト\n",
    Regex("\\s*ブルームエフェクト\\s*") to "\nブルームエフェクト\n",
    Regex("\\s*ギフト\\s*") to "\nギフト\n",
    Regex("\\s*エクストラ\\s*") to "\nエクストラ\n",
    Regex("\\s*アーツ(?=\\s+(?![+\\-]\\d)\\S)\\s*") to "\nアーツ\n",
    Regex("\\s*カードタイプ\\s*") to "\nカードタイプ\n",
    Regex("\\s*タグ\\s*") to "\nタグ\n",
    Regex("\\s*レアリティ\\s*") to "\nレアリティ\n",
    Regex("\\s*能力テキスト\\s*") to "\n能力テキスト\n",
    Regex("\\s*バトンタッチ\\s*") to "\nバトンタッチ\n",
    Regex("(?:^|\\s)色(?=\\s+\\S)") to "\n色\n",
    Regex("\\s+#") to "\n#",
)

private val DETAIL_PREFIX_PATTERN = Regex(
    pattern = """^(?:(?:.+?)\s+)?(?:서포트|サポート)\s*[/／]\s*(?:아이템|스태프|이벤트|이벤타|툴|마스코트|팬|アイテム|スタッフ|イベント|ツール|マスコット|ファン)(?=$|\s|[/／:：(\[])""",
)

private val INLINE_TAG_PATTERN = Regex(pattern = """#[\p{L}\p{N}_]+""")
private val HTML_TAG_REGEX = Regex("<[^>]+>", RegexOption.IGNORE_CASE)
private val WIDTH_ARTIFACT_REGEX = Regex("""(?i)\bwidth\s*=\s*\d+%?>?""")
private const val MW_PLACEHOLDER = "\uFFFF"
private val KO_MW_TAG_PATTERNS = listOf(
    Regex("#ID\\s+\\d+기생"),
    Regex("#[^\\s#]+['']s\\s+[^\\s#]+"),
    Regex("#비밀\\s+결사\\s+[Hh]oloX"),
    Regex("#FLOW\\s+GLOW"),
)
private val SCALAR_METADATA_PATTERN = Regex("^(hp\\s*\\d{2,3}|(1st|2nd)\\s*\\d{2,3})$", RegexOption.IGNORE_CASE)
private val DIGIT_TOKEN_PATTERN = Regex("^\\d{2,3}$")

private enum class DetailTextLanguage {
    KOREAN,
    JAPANESE,
}

private enum class DeckImportMode(val label: String) {
    HOLODUEL("홀로듀얼"),
    HOLODELTA("홀로델타"),
    BUSHIROAD("부시나비"),
}

private data class DeckEntryUi(
    val card: DeckCardCandidate,
    val qty: Int,
    val maxPerCard: Int,
    /** 사용자가 선택한 레어리티. null 이면 기본값(card.rarity) 사용. */
    val selectedRarity: String? = null,
) {
    val displayRarity: String get() = selectedRarity ?: card.selectableIllustrations.firstOrNull()?.rarity.orEmpty()

    val effectiveImageUrl: String get() {
        val rarity = selectedRarity ?: card.selectableIllustrations.firstOrNull()?.rarity ?: return card.imageUrl
        val option = card.selectableIllustrations.firstOrNull { it.rarity == rarity }
        return if (option != null && option.imageUrl.isNotEmpty()) option.imageUrl else card.imageUrl
    }

    val effectiveManageId: Int? get() {
        val rarity = selectedRarity ?: card.selectableIllustrations.firstOrNull()?.rarity ?: return null
        return card.selectableIllustrations.firstOrNull { it.rarity == rarity }?.manageIdJp
            ?: card.illustrations.firstOrNull { it.rarity == rarity }?.manageIdJp
    }
}

private data class DeckUi(
    val id: String,
    val title: String,
    val entries: List<DeckEntryUi>,
    val updatedAt: Long,
)

private fun unresolvedDeckCard(entry: DeckEntryRecord): DeckCardCandidate {
    val cardNumber = entry.cardNumber.ifBlank { "UNKNOWN-${entry.printId}" }
    val inferredType = if (cardNumber.uppercase().startsWith("HY")) "エール" else ""
    val inferredRarity = entry.selectedRarity.orEmpty()
    val inferredId = if (entry.printId > 0) entry.printId else -kotlin.math.abs(cardNumber.hashCode().toLong()).coerceAtLeast(1L)
    return DeckCardCandidate(
        printId = inferredId,
        cardNumber = cardNumber,
        nameJa = cardNumber,
        nameKo = "미복원 카드",
        imageUrl = "",
        cardType = inferredType,
        color = if (inferredType.isNotEmpty()) "엘" else "",
        rarity = inferredRarity,
        koText = "업데이트 후 현재 DB와 매칭되지 않아 원본 덱 엔트리를 보존한 카드입니다.",
        jaText = "",
        illustrations = emptyList(),
    )
}

private fun isOshi(card: DeckCardCandidate): Boolean = card.cardType.contains("오시") || card.cardType.contains("推し")
private fun isYell(card: DeckCardCandidate): Boolean {
    if (card.cardNumber.uppercase().startsWith("HY")) {
        return true
    }
    val c = card.color.lowercase()
    val t = card.cardType.lowercase()
    return c.contains("옐") || c.contains("yell") || c.contains("エール") || t.contains("yell") || t.contains("エール")
}

private fun hasUnlimitedPerCardRule(card: DeckCardCandidate): Boolean {
    val normalizedKo = card.koText
        .lowercase()
        .replace(" ", "")
        .replace("　", "")
    val normalizedJa = card.jaText
        .replace(" ", "")
        .replace("　", "")
    return normalizedKo.contains("이카드는갯수제한이없다") ||
        normalizedKo.contains("이카드는수량제한이없다") ||
        normalizedKo.contains("갯수제한이없다") ||
        normalizedKo.contains("수량제한이없다") ||
        normalizedKo.contains("몇장이라도넣을수있다") ||
        normalizedKo.contains("갯수상관없이여러장넣을수있다") ||
        normalizedKo.contains("수량상관없이여러장넣을수있다") ||
        (normalizedJa.contains("何枚でも") && normalizedJa.contains("入れられる"))
}

private fun hasOneCopyByRarity(card: DeckCardCandidate): Boolean {
    val rarities = buildSet {
        val base = card.rarity.trim().uppercase()
        if (base.isNotEmpty()) add(base)
        card.illustrations.forEach { option ->
            val rarity = option.rarity.trim().uppercase()
            if (rarity.isNotEmpty()) add(rarity)
        }
    }
    return "OUR" in rarities || "OSR" in rarities
}

private fun maxPerCard(card: DeckCardCandidate): Int {
    if (isOshi(card)) return 1
    if (hasOneCopyByRarity(card)) return 1
    if (isYell(card)) return Int.MAX_VALUE
    if (hasUnlimitedPerCardRule(card)) return Int.MAX_VALUE
    return 4
}

private fun blockReason(entries: List<DeckEntryUi>, card: DeckCardCandidate): String? {
    val qty = deckQuantity(entries, card)
    val perCardLimit = maxPerCard(card)
    if (perCardLimit != Int.MAX_VALUE && qty >= perCardLimit) {
        return "이 카드는 최대 ${perCardLimit}장까지만 편성 가능합니다."
    }
    val oshi = entries.filter { isOshi(it.card) }.sumOf { it.qty }
    val yell = entries.filter { isYell(it.card) }.sumOf { it.qty }
    val main = entries.filter { !isOshi(it.card) && !isYell(it.card) }.sumOf { it.qty }
    if (isOshi(card) && oshi >= 1) {
        return "오시는 1장만 편성 가능합니다."
    }
    if (isYell(card) && yell >= 20) {
        return "옐 슬롯이 가득 찼습니다 (20/20)."
    }
    if (!isOshi(card) && !isYell(card) && main >= 50) {
        return "덱이 가득 찼습니다 (50/50)."
    }
    return null
}

private fun deckQuantity(entries: List<DeckEntryUi>, card: DeckCardCandidate): Int {
    return entries.firstOrNull { it.card.printId == card.printId }?.qty ?: 0
}

private fun addCardToDeck(entries: MutableList<DeckEntryUi>, card: DeckCardCandidate): String? {
    val reason = blockReason(entries, card)
    if (reason != null) {
        return reason
    }
    val index = entries.indexOfFirst { it.card.printId == card.printId }
    if (index == -1) {
        entries.add(DeckEntryUi(card = card, qty = 1, maxPerCard = maxPerCard(card)))
        return null
    }
    val found = entries[index]
    val perCardLimit = maxPerCard(found.card)
    entries[index] = found.copy(qty = found.qty + 1, maxPerCard = perCardLimit)
    return null
}

private fun increaseDeckEntryByPrintId(entries: MutableList<DeckEntryUi>, printId: Long): String? {
    val index = entries.indexOfFirst { it.card.printId == printId }
    if (index == -1) {
        return "카드를 찾을 수 없습니다."
    }
    val current = entries[index]
    val reason = blockReason(entries, current.card)
    if (reason != null) {
        return reason
    }
    entries[index] = current.copy(qty = current.qty + 1, maxPerCard = maxPerCard(current.card))
    return null
}

private fun decreaseDeckEntryByPrintId(entries: MutableList<DeckEntryUi>, printId: Long) {
    val index = entries.indexOfFirst { it.card.printId == printId }
    if (index == -1) {
        return
    }
    val current = entries[index]
    if (current.qty <= 1) {
        entries.removeAt(index)
    } else {
        entries[index] = current.copy(qty = current.qty - 1)
    }
}

private fun toDeckRecords(decks: List<DeckUi>): List<SavedDeckRecord> {
    return decks.map { deck ->
        SavedDeckRecord(
            id = deck.id,
            title = deck.title,
            entries = deck.entries
                .filter { it.qty > 0 }
                .map { entry ->
                    DeckEntryRecord(
                        printId = entry.card.printId,
                        cardNumber = entry.card.cardNumber,
                        qty = entry.qty,
                        selectedRarity = entry.selectedRarity,
                    )
                },
            updatedAt = deck.updatedAt,
        )
    }
}

private fun resolveDecksFromRecords(
    records: List<SavedDeckRecord>,
    cards: List<DeckCardCandidate>,
): List<DeckUi> {
    val byPrintId = cards.associateBy { it.printId }
    val byCardNumber = cards.associateBy { it.cardNumber.uppercase() }
    return records.mapNotNull { deck ->
        val entries = deck.entries.mapNotNull { entry ->
            if (entry.qty <= 0) {
                null
            } else {
                val card = byPrintId[entry.printId] ?: byCardNumber[entry.cardNumber.uppercase()] ?: unresolvedDeckCard(entry)
                val perCardLimit = maxPerCard(card)
                val normalizedQty = entry.qty.coerceAtLeast(1)
                val clampedQty = if (perCardLimit == Int.MAX_VALUE) normalizedQty else normalizedQty.coerceAtMost(perCardLimit)
                val resolvedRarity = entry.selectedRarity?.trim()?.takeIf { rarity ->
                    card.selectableIllustrations.isEmpty() || card.selectableIllustrations.any { it.rarity == rarity }
                }
                DeckEntryUi(
                    card = card,
                    qty = clampedQty,
                    maxPerCard = perCardLimit,
                    selectedRarity = resolvedRarity,
                )
            }
        }
        if (entries.isEmpty()) {
            null
        } else {
            DeckUi(
                id = deck.id,
                title = deck.title,
                entries = entries,
                updatedAt = deck.updatedAt,
            )
        }
    }
}

private fun sanitizeDeckFilename(raw: String): String {
    val trimmed = raw.trim()
    if (trimmed.isEmpty()) {
        return "deck"
    }
    val safe = trimmed.replace(Regex("[^A-Za-z0-9가-힣._-]+"), "_")
    return safe.ifBlank { "deck" }
}

private suspend fun loadDeckCardBitmap(
    context: android.content.Context,
    imageLoader: ImageLoader,
    imageUrl: String,
    width: Int,
    height: Int,
): Bitmap? {
    val request = ImageRequest.Builder(context)
        .data(imageUrl)
        .allowHardware(false)
        .build()
    val result = imageLoader.execute(request)
    val drawable = (result as? SuccessResult)?.drawable ?: return null
    return runCatching { drawable.toBitmap(width, height) }.getOrNull()
}

private suspend fun buildDeckExportBitmap(
    context: android.content.Context,
    imageLoader: ImageLoader,
    deck: DeckUi,
): Bitmap? {
    val entries = deck.entries
    if (entries.isEmpty()) return null

    val oshiEntries = entries.filter { isOshi(it.card) }
    val yellEntries = entries.filter { !isOshi(it.card) && isYell(it.card) }
    // 오시 홀로멤 → 옐 → 홀로멤 → 서포트 순 정렬
    fun mainSortOrder(card: DeckCardCandidate): Int {
        val ct = card.cardType.lowercase()
        return if (ct.contains("홀로멤") || ct.contains("holomem") || ct.contains("ホロメン")) 0 else 1
    }
    val mainEntries = entries
        .filter { !isOshi(it.card) && !isYell(it.card) }
        .sortedBy { mainSortOrder(it.card) }

    val mainColumns = 5
    val sideColumns = 2
    val cardW = 220
    val cardH = 308
    val gap = 16
    val padding = 24
    val sideGap = 24
    val titleH = 76
    val sectionLabelH = 44
    val sectionSubLabelH = 38
    val sectionSpacing = 18
    val separatorH = 1
    val minEmptySectionH = 52

    val canvasW = padding * 2 + mainColumns * cardW + (mainColumns - 1) * gap
    val contentW = canvasW - padding * 2
    val sideWidth = (contentW - sideGap) / 2
    val sideGridW = sideColumns * cardW + (sideColumns - 1) * gap
    val sideGridOffset = ((sideWidth - sideGridW) / 2).coerceAtLeast(0)

    val oshiRows = if (oshiEntries.isEmpty()) 0 else (oshiEntries.size + sideColumns - 1) / sideColumns
    val yellRows = if (yellEntries.isEmpty()) 0 else (yellEntries.size + sideColumns - 1) / sideColumns
    val sideRows = maxOf(oshiRows, yellRows)
    val sideGridH = if (sideRows > 0) sideRows * cardH + (sideRows - 1) * gap else minEmptySectionH

    val mainRows = if (mainEntries.isEmpty()) 0 else (mainEntries.size + mainColumns - 1) / mainColumns
    val mainGridH = if (mainRows > 0) mainRows * cardH + (mainRows - 1) * gap else minEmptySectionH

    val canvasH = padding +
        titleH +
        sectionSpacing +
        sectionLabelH +
        sectionSubLabelH +
        sectionSpacing +
        sideGridH +
        sectionSpacing +
        separatorH +
        sectionSpacing +
        sectionLabelH +
        sectionSpacing +
        mainGridH +
        padding
    val bitmap = Bitmap.createBitmap(canvasW, canvasH, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    canvas.drawColor(Color.WHITE)

    val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.BLACK
        textSize = 52f
        typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
        textAlign = Paint.Align.LEFT
    }
    val sectionPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.BLACK
        textSize = 34f
        typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
        textAlign = Paint.Align.CENTER
    }
    val sectionLeftPaint = Paint(sectionPaint).apply {
        textAlign = Paint.Align.LEFT
    }
    val subSectionPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.DKGRAY
        textSize = 28f
        typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
        textAlign = Paint.Align.CENTER
    }
    val emptyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.GRAY
        textSize = 24f
        typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
        textAlign = Paint.Align.CENTER
    }
    val title = deck.title.ifBlank { "덱" }
    canvas.drawText(title, padding.toFloat(), (padding + 52).toFloat(), titlePaint)

    val cardPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    val placeholderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.LTGRAY }
    val placeholderTextPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.DKGRAY
        textSize = 22f
        textAlign = Paint.Align.LEFT
    }
    val badgeBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(205, 0, 0, 0)
    }
    val badgeTextPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 26f
        typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
        textAlign = Paint.Align.CENTER
    }
    val dividerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(210, 210, 210)
        strokeWidth = 1f
    }

    val imageCache = mutableMapOf<Long, Bitmap?>()
    for (entry in entries) {
        if (imageCache.containsKey(entry.card.printId)) continue
        imageCache[entry.card.printId] = loadDeckCardBitmap(
            context = context,
            imageLoader = imageLoader,
            imageUrl = entry.effectiveImageUrl,
            width = cardW,
            height = cardH,
        )
    }

    fun drawCard(entry: DeckEntryUi, dst: Rect) {
        val loaded = imageCache[entry.card.printId]
        if (loaded != null) {
            canvas.drawBitmap(loaded, null, dst, cardPaint)
        } else {
            canvas.drawRoundRect(RectF(dst), 12f, 12f, placeholderPaint)
            canvas.drawText(entry.card.cardNumber, (dst.left + 10).toFloat(), (dst.top + 30).toFloat(), placeholderTextPaint)
        }

        val qtyLabel = entry.qty.toString()
        val qtyWidth = badgeTextPaint.measureText(qtyLabel)
        val badgeW = maxOf(42f, qtyWidth + 24f)
        val badgeH = 36f
        val badgeLeft = dst.right - badgeW - 10f
        val badgeTop = dst.top + 10f
        val badgeRect = RectF(badgeLeft, badgeTop, badgeLeft + badgeW, badgeTop + badgeH)
        canvas.drawRoundRect(badgeRect, badgeH / 2f, badgeH / 2f, badgeBgPaint)
        val textY = badgeRect.centerY() - (badgeTextPaint.descent() + badgeTextPaint.ascent()) / 2f
        canvas.drawText(qtyLabel, badgeRect.centerX(), textY, badgeTextPaint)
    }

    fun drawCenteredText(text: String, rect: RectF, paint: Paint) {
        val textY = rect.centerY() - (paint.descent() + paint.ascent()) / 2f
        canvas.drawText(text, rect.centerX(), textY, paint)
    }

    val leftSectionX = padding
    val rightSectionX = padding + sideWidth + sideGap
    val sideSplitX = padding + sideWidth + sideGap / 2f
    val leftGridX = leftSectionX + sideGridOffset
    val rightGridX = rightSectionX + sideGridOffset
    var currentY = (padding + titleH + sectionSpacing).toFloat()
    val sideLabelTop = currentY

    drawCenteredText(
        "오시",
        RectF(leftSectionX.toFloat(), currentY, (leftSectionX + sideWidth).toFloat(), currentY + sectionLabelH),
        sectionPaint,
    )
    drawCenteredText(
        "옐",
        RectF(rightSectionX.toFloat(), currentY, (rightSectionX + sideWidth).toFloat(), currentY + sectionLabelH),
        sectionPaint,
    )
    currentY += sectionLabelH

    drawCenteredText(
        "오시 카드",
        RectF(leftSectionX.toFloat(), currentY, (leftSectionX + sideWidth).toFloat(), currentY + sectionSubLabelH),
        subSectionPaint,
    )
    drawCenteredText(
        "옐 카드",
        RectF(rightSectionX.toFloat(), currentY, (rightSectionX + sideWidth).toFloat(), currentY + sectionSubLabelH),
        subSectionPaint,
    )
    currentY += sectionSubLabelH + sectionSpacing

    val sideCardsTop = currentY.toInt()
    if (oshiEntries.isEmpty()) {
        drawCenteredText(
            "카드 없음",
            RectF(leftSectionX.toFloat(), currentY, (leftSectionX + sideWidth).toFloat(), currentY + sideGridH),
            emptyPaint,
        )
    } else {
        oshiEntries.forEachIndexed { index, entry ->
            val row = index / sideColumns
            val col = index % sideColumns
            val left = leftGridX + col * (cardW + gap)
            val top = sideCardsTop + row * (cardH + gap)
            drawCard(entry, Rect(left, top, left + cardW, top + cardH))
        }
    }

    if (yellEntries.isEmpty()) {
        drawCenteredText(
            "카드 없음",
            RectF(rightSectionX.toFloat(), currentY, (rightSectionX + sideWidth).toFloat(), currentY + sideGridH),
            emptyPaint,
        )
    } else {
        yellEntries.forEachIndexed { index, entry ->
            val row = index / sideColumns
            val col = index % sideColumns
            val left = rightGridX + col * (cardW + gap)
            val top = sideCardsTop + row * (cardH + gap)
            drawCard(entry, Rect(left, top, left + cardW, top + cardH))
        }
    }

    val sideBottom = sideCardsTop + sideGridH
    canvas.drawLine(sideSplitX, sideLabelTop, sideSplitX, sideBottom.toFloat(), dividerPaint)

    currentY = (sideBottom + sectionSpacing).toFloat()
    canvas.drawLine(padding.toFloat(), currentY, (canvasW - padding).toFloat(), currentY, dividerPaint)

    currentY += sectionSpacing
    canvas.drawText("덱 카드", padding.toFloat(), currentY + sectionLeftPaint.textSize, sectionLeftPaint)
    currentY += sectionLabelH + sectionSpacing

    if (mainEntries.isEmpty()) {
        drawCenteredText(
            "카드 없음",
            RectF(padding.toFloat(), currentY, (canvasW - padding).toFloat(), currentY + mainGridH),
            emptyPaint,
        )
    } else {
        mainEntries.forEachIndexed { index, entry ->
            val row = index / mainColumns
            val col = index % mainColumns
            val left = padding + col * (cardW + gap)
            val top = currentY.toInt() + row * (cardH + gap)
            drawCard(entry, Rect(left, top, left + cardW, top + cardH))
        }
    }
    return bitmap
}

private suspend fun saveDeckBitmapToGallery(
    context: android.content.Context,
    deckTitle: String,
    bitmap: Bitmap,
): Boolean = withContext(Dispatchers.IO) {
    val resolver = context.contentResolver
    val safeName = sanitizeDeckFilename(deckTitle)
    val fileName = "deck_${safeName}_${System.currentTimeMillis()}.png"
    val values = ContentValues().apply {
        put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
        put(MediaStore.Images.Media.MIME_TYPE, "image/png")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/hOCG_H")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
    }
    val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
    } else {
        MediaStore.Images.Media.EXTERNAL_CONTENT_URI
    }

    var savedUri: Uri? = null
    runCatching {
        savedUri = resolver.insert(collection, values) ?: error("갤러리 저장 URI 생성에 실패했습니다.")
        resolver.openOutputStream(savedUri!!)?.use { stream ->
            if (!bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)) {
                error("이미지 인코딩에 실패했습니다.")
            }
        } ?: error("갤러리 출력 스트림 생성에 실패했습니다.")

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val publish = ContentValues().apply {
                put(MediaStore.Images.Media.IS_PENDING, 0)
            }
            resolver.update(savedUri!!, publish, null, null)
        }
        true
    }.getOrElse {
        savedUri?.let { resolver.delete(it, null, null) }
        false
    }
}

private suspend fun saveDeckJsonToDownloads(
    context: android.content.Context,
    deckTitle: String,
    jsonText: String,
): Boolean = withContext(Dispatchers.IO) {
    val resolver = context.contentResolver
    val safeName = sanitizeDeckFilename(deckTitle)
    val fileName = "deck_${safeName}_${System.currentTimeMillis()}.json"

    val values = ContentValues().apply {
        put(MediaStore.Downloads.DISPLAY_NAME, fileName)
        put(MediaStore.Downloads.MIME_TYPE, "application/json")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
    }

    val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
    } else {
        MediaStore.Downloads.EXTERNAL_CONTENT_URI
    }

    var savedUri: Uri? = null
    runCatching {
        savedUri = resolver.insert(collection, values) ?: error("다운로드 저장 URI 생성에 실패했습니다.")
        resolver.openOutputStream(savedUri!!)?.use { stream ->
            stream.write(jsonText.toByteArray(Charsets.UTF_8))
            stream.flush()
        } ?: error("다운로드 출력 스트림 생성에 실패했습니다.")

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val publish = ContentValues().apply {
                put(MediaStore.Downloads.IS_PENDING, 0)
            }
            resolver.update(savedUri!!, publish, null, null)
        }
        true
    }.getOrElse {
        savedUri?.let { resolver.delete(it, null, null) }
        false
    }
}

private fun readTextFromUri(context: android.content.Context, uri: Uri): String? {
    return runCatching {
        context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }
    }.getOrNull()
}

@Composable
private fun DeckThumbnail(
    imageUrl: String,
    qty: Int,
    width: Dp,
    height: Dp,
) {
    Box(
        modifier = Modifier
            .size(width = width, height = height)
            .clip(RoundedCornerShape(6.dp)),
    ) {
        AsyncImage(
            model = imageUrl,
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
        )
        if (qty > 0) {
            Text(
                text = qty.toString(),
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(3.dp)
                    .background(
                        color = androidx.compose.ui.graphics.Color(0xCC000000),
                        shape = RoundedCornerShape(999.dp),
                    )
                    .padding(horizontal = 6.dp, vertical = 2.dp),
                color = androidx.compose.ui.graphics.Color.White,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun SearchRaritySelector(
    selectedRarity: String,
    illustrations: List<com.smalltyrant.hocgh.model.IllustrationOption>,
    fallbackImageUrl: String,
    onSelect: (String, String) -> Unit,
) {
    if (illustrations.size <= 1) return

    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(illustrations.size) { index ->
            val option = illustrations[index]
            val imageUrl = option.imageUrl.takeIf { it.isNotBlank() } ?: fallbackImageUrl
            val selected = option.rarity == selectedRarity
            if (selected) {
                ElevatedButton(onClick = { onSelect(option.rarity, imageUrl) }) {
                    Text(option.rarity)
                }
            } else {
                TextButton(onClick = { onSelect(option.rarity, imageUrl) }) {
                    Text(option.rarity)
                }
            }
        }
    }
}

private fun findAdjacentIllustration(
    selectedRarity: String,
    illustrations: List<com.smalltyrant.hocgh.model.IllustrationOption>,
    fallbackImageUrl: String,
    direction: Int,
): Pair<String, String>? {
    if (illustrations.size <= 1 || direction == 0) return null

    val currentIndex = illustrations.indexOfFirst { it.rarity == selectedRarity }.takeIf { it >= 0 } ?: 0
    val targetIndex = (currentIndex + direction).coerceIn(0, illustrations.lastIndex)
    if (targetIndex == currentIndex) return null

    val option = illustrations[targetIndex]
    val imageUrl = option.imageUrl.takeIf { it.isNotBlank() } ?: fallbackImageUrl
    return option.rarity to imageUrl
}

private fun currentImageModel(imageState: ImageState): Any? {
    return when (imageState) {
        is ImageState.Local -> imageState.file
        is ImageState.Remote -> imageState.url
        else -> null
    }
}

@Composable
fun HocgScreen(
    viewModel: HocgViewModel = viewModel(),
    themeMode: AppThemeMode,
    onThemeModeChange: (AppThemeMode) -> Unit,
    preferredLanguage: PreferredLanguage,
    onPreferredLanguageChange: (PreferredLanguage) -> Unit,
) {
    val state = viewModel.state
    val config = androidx.compose.ui.platform.LocalConfiguration.current
    val forceDesktopLandscape =
        config.orientation == Configuration.ORIENTATION_LANDSCAPE && config.screenWidthDp < 900
    val isMobileLayout = config.screenWidthDp < 900 && !forceDesktopLandscape
    val focusManager = LocalFocusManager.current
    val context = LocalContext.current

    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    val deckStorage = remember(context) { DeckStorage(AppPaths(context)) }

    var showDeckList by remember { mutableStateOf(false) }
    var showDeckEditor by remember { mutableStateOf(false) }
    var editingDeckId by remember { mutableStateOf<String?>(null) }
    var deckTitle by remember { mutableStateOf("새 덱") }
    var deckSearchQuery by remember { mutableStateOf("") }
    var deckCandidates by remember { mutableStateOf<List<DeckCardCandidate>>(emptyList()) }
    var renamingDeckId by remember { mutableStateOf<String?>(null) }
    var renamingDeckTitle by remember { mutableStateOf("") }
    var showingDeckImportDialog by remember { mutableStateOf(false) }
    var deckImportText by remember { mutableStateOf("") }
    var deckImportMode by remember { mutableStateOf(DeckImportMode.HOLODUEL) }
    /** 레어리티 선택 BottomSheet 용 — null 이면 닫힘 */
    var rarityPickerEntry by remember { mutableStateOf<DeckEntryUi?>(null) }
    /** 새 카드 추가 시 레어리티 선택용 — null 이면 닫힘 */
    var rarityPickerNewCard by remember { mutableStateOf<DeckCardCandidate?>(null) }
    val deckDraft = remember { mutableStateListOf<DeckEntryUi>() }
    val savedDecks = remember { mutableStateListOf<DeckUi>() }
    val imageLoader = remember(context) { ImageLoader(context) }
    val jsonFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            val raw = withContext(Dispatchers.IO) { readTextFromUri(context, uri) }
            if (raw.isNullOrBlank()) {
                snackbarHostState.showSnackbar("JSON 파일을 읽지 못했습니다.")
                return@launch
            }
            deckImportText = raw
            if (deckImportMode != DeckImportMode.HOLODELTA) {
                snackbarHostState.showSnackbar("JSON 파일을 불러왔습니다. 가져오기 방식을 홀로델타로 선택해 주세요.")
                return@launch
            }

            runCatching {
                val holoDeltaDeck = DeckCodeConverter.importHoloDelta(raw)
                    ?: error("홀로델타 코드 형식이 올바르지 않습니다.")
                val allCards = viewModel.searchDeckCards("", limit = 5000)
                val byNumber = allCards.associateBy { it.cardNumber.uppercase() }

                fun selectedRarity(card: DeckCardCandidate, artIndex: Int): String? {
                    if (artIndex < 0 || artIndex >= card.illustrations.size) return null
                    val rarity = card.illustrations[artIndex].rarity
                    return if (card.selectableIllustrations.any { it.rarity == rarity }) rarity else null
                }

                val entries = mutableListOf<DeckEntryUi>()
                byNumber[holoDeltaDeck.oshiCardNumber.uppercase()]?.let {
                    entries += DeckEntryUi(
                        card = it,
                        qty = 1,
                        maxPerCard = maxPerCard(it),
                        selectedRarity = selectedRarity(it, holoDeltaDeck.oshiArtIndex),
                    )
                }
                holoDeltaDeck.deckEntries.forEach { row ->
                    byNumber[row.cardNumber.uppercase()]?.let {
                        entries += DeckEntryUi(
                            card = it,
                            qty = row.qty,
                            maxPerCard = maxPerCard(it),
                            selectedRarity = selectedRarity(it, row.artIndex),
                        )
                    }
                }
                holoDeltaDeck.cheerEntries.forEach { row ->
                    byNumber[row.cardNumber.uppercase()]?.let {
                        entries += DeckEntryUi(
                            card = it,
                            qty = row.qty,
                            maxPerCard = maxPerCard(it),
                            selectedRarity = selectedRarity(it, row.artIndex),
                        )
                    }
                }

                if (entries.isEmpty()) error("카드 정보를 찾을 수 없습니다.")
                val title = holoDeltaDeck.deckName?.ifBlank { "홀로델타 덱" } ?: "홀로델타 덱"
                val deck = DeckUi(
                    id = java.util.UUID.randomUUID().toString(),
                    title = title,
                    entries = entries,
                    updatedAt = System.currentTimeMillis(),
                )
                savedDecks.add(deck)
                withContext(Dispatchers.IO) {
                    deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks)))
                }
                deckImportText = ""
                showingDeckImportDialog = false
            }.onSuccess {
                snackbarHostState.showSnackbar("홀로델타 JSON 덱 가져오기가 완료되었습니다.")
            }.onFailure { e ->
                snackbarHostState.showSnackbar("홀로델타 불러오기 실패: ${e.message?.take(80)}")
            }
        }
    }

    val openDeckBuilder: () -> Unit = {
        showDeckList = false
        showDeckEditor = true
        scope.launch { deckCandidates = viewModel.searchDeckCards(deckSearchQuery) }
        Unit
    }

    LaunchedEffect(Unit) {
        viewModel.toastEvents.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

    LaunchedEffect(Unit) {
        val records = withContext(Dispatchers.IO) { deckStorage.loadLibrary().decks }
        if (records.isEmpty()) {
            return@LaunchedEffect
        }
        val allCards = viewModel.searchDeckCards("", limit = 5000)
        val restored = resolveDecksFromRecords(records, allCards)
        savedDecks.clear()
        savedDecks.addAll(restored)
    }

    state.appUpdateDialog?.let { dialog ->
        AlertDialog(
            onDismissRequest = viewModel::onAppUpdateDialogDismiss,
            title = { Text("앱 업데이트") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("앱 업데이트가 있습니다. 업데이트 하시겠습니까?")
                    Text(
                        text = "현재 버전: ${dialog.localVersionName} (${dialog.localVersionCode})",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        text = "GitHub 버전: ${dialog.remoteVersionName.ifBlank { "알 수 없음" }} (${dialog.remoteVersionCode})",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            },
            confirmButton = {
                ElevatedButton(onClick = viewModel::onAppUpdateDialogConfirm) {
                    Text("업데이트")
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::onAppUpdateDialogDismiss) {
                    Text("나중에")
                }
            },
        )
    }

    if (state.appUpdateDialog == null) {
        state.updateDialog?.let { dialog ->
            AlertDialog(
                onDismissRequest = viewModel::onUpdateDialogDismiss,
                title = { Text("DB 업데이트") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("DB 업데이트가 있습니다. 업데이트 하시겠습니까?")
                        Text(
                            text = "로컬 DB 날짜: ${dialog.localDate ?: "없음"}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text(
                            text = "GitHub DB 날짜: ${dialog.remoteDate}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        dialog.remoteDigest?.take(8)?.let { remoteDigest ->
                            Text(
                                text = "GitHub DB 식별자: $remoteDigest",
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                },
                confirmButton = {
                    ElevatedButton(onClick = viewModel::onUpdateDialogConfirm) {
                        Text("업데이트")
                    }
                },
                dismissButton = {
                    TextButton(onClick = viewModel::onUpdateDialogDismiss) {
                        Text("나중에")
                    }
                },
            )
        }
    }

    if (renamingDeckId != null) {
        AlertDialog(
            onDismissRequest = { renamingDeckId = null },
            title = { Text("덱 이름 수정") },
            text = {
                OutlinedTextField(
                    value = renamingDeckTitle,
                    onValueChange = { renamingDeckTitle = it },
                    singleLine = true,
                    label = { Text("덱 이름") },
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val targetId = renamingDeckId
                        val title = renamingDeckTitle.trim()
                        if (targetId != null && title.isNotEmpty()) {
                            val idx = savedDecks.indexOfFirst { it.id == targetId }
                            if (idx >= 0) {
                                savedDecks[idx] = savedDecks[idx].copy(title = title, updatedAt = System.currentTimeMillis())
                                scope.launch(Dispatchers.IO) {
                                    deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks)))
                                }
                            }
                        }
                        renamingDeckId = null
                    },
                ) {
                    Text("저장")
                }
            },
            dismissButton = {
                TextButton(onClick = { renamingDeckId = null }) {
                    Text("취소")
                }
            },
        )
    }

    if (showingDeckImportDialog) {
        AlertDialog(
            onDismissRequest = { showingDeckImportDialog = false },
            title = { Text("덱 가져오기") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    // 탭 선택
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        DeckImportMode.entries.forEach { mode ->
                            ElevatedButton(
                                onClick = { deckImportMode = mode },
                                modifier = Modifier.weight(1f),
                                colors = androidx.compose.material3.ButtonDefaults.elevatedButtonColors(
                                    containerColor = if (deckImportMode == mode)
                                        MaterialTheme.colorScheme.primaryContainer
                                    else
                                        MaterialTheme.colorScheme.surface,
                                ),
                            ) { Text(mode.label) }
                        }
                    }
                    Text(
                        text = when (deckImportMode) {
                            DeckImportMode.HOLODUEL -> "홀로듀얼 덱 코드(Base64)를 붙여넣어 주세요."
                            DeckImportMode.HOLODELTA -> "홀로델타 코드(JSON 또는 Base64 URL-safe)를 붙여넣어 주세요."
                            DeckImportMode.BUSHIROAD -> "부시나비 URL 또는 코드를 붙여넣어 주세요.\n예: 6ADJR (URL 전체 입력 불필요)"
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                    OutlinedTextField(
                        value = deckImportText,
                        onValueChange = { deckImportText = it },
                        label = {
                            Text(
                                when (deckImportMode) {
                                    DeckImportMode.HOLODUEL -> "홀로듀얼 코드"
                                    DeckImportMode.HOLODELTA -> "홀로델타 코드"
                                    DeckImportMode.BUSHIROAD -> "부시나비 URL / 코드"
                                }
                            )
                        },
                        placeholder = {
                            Text(
                                when (deckImportMode) {
                                    DeckImportMode.HOLODUEL -> "Base64 코드를 붙여넣어 주세요"
                                    DeckImportMode.HOLODELTA -> "JSON 또는 Base64 URL-safe"
                                    DeckImportMode.BUSHIROAD -> "예: 6ADJR"
                                }
                            )
                        },
                        minLines = 4,
                        maxLines = 8,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    if (deckImportMode == DeckImportMode.HOLODELTA) {
                        TextButton(
                            onClick = { jsonFilePicker.launch(arrayOf("application/json", "text/json", "text/plain")) },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("홀로델타 JSON 파일 선택")
                        }
                    }
                    ElevatedButton(
                        onClick = {
                            val raw = deckImportText.trim()
                            if (raw.isEmpty()) {
                                scope.launch { snackbarHostState.showSnackbar("변환할 코드가 비어 있습니다.") }
                                return@ElevatedButton
                            }
                            scope.launch {
                                when (deckImportMode) {
                                    DeckImportMode.HOLODUEL -> {
                                        snackbarHostState.showSnackbar("홀로델타 코드로 변환 중...")
                                        val holoDuelDeck = withContext(Dispatchers.IO) {
                                            DeckCodeConverter.importHoloDuel(raw)
                                        }
                                        if (holoDuelDeck == null) {
                                            snackbarHostState.showSnackbar("홀로듀얼 코드 형식이 올바르지 않습니다.")
                                            return@launch
                                        }
                                        val allCards = viewModel.searchDeckCards("", limit = 5000)
                                        val byNumber = allCards.associateBy { it.cardNumber.uppercase() }
                                        val entries = mutableListOf<Triple<String, Int, DeckCardCandidate>>()
                                        byNumber[holoDuelDeck.oshiCardNumber.uppercase()]?.let {
                                            entries += Triple(it.cardNumber, 1, it)
                                        }
                                        for ((cn, qty) in holoDuelDeck.deckEntries) {
                                            byNumber[cn.uppercase()]?.let { entries += Triple(it.cardNumber, qty, it) }
                                        }
                                        for ((cn, qty) in holoDuelDeck.cheerEntries) {
                                            byNumber[cn.uppercase()]?.let { entries += Triple(it.cardNumber, qty, it) }
                                        }
                                        if (entries.isEmpty()) {
                                            snackbarHostState.showSnackbar("카드 정보를 찾을 수 없습니다.")
                                            return@launch
                                        }
                                        runCatching {
                                            DeckCodeConverter.exportHoloDelta(entries, title = "변환 덱")
                                        }.onSuccess { code ->
                                            if (code.isNullOrBlank()) {
                                                snackbarHostState.showSnackbar("변환 실패: 오시 카드가 없습니다.")
                                                return@onSuccess
                                            }
                                            val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? ClipboardManager
                                            clipboard?.setPrimaryClip(ClipData.newPlainText("holodelta_deck_code", code))
                                            deckImportText = ""
                                            showingDeckImportDialog = false
                                            snackbarHostState.showSnackbar("홀로델타 코드가 클립보드에 복사되었습니다.")
                                        }.onFailure { e ->
                                            snackbarHostState.showSnackbar("변환 실패: ${e.message?.take(80)}")
                                        }
                                    }
                                    DeckImportMode.HOLODELTA -> {
                                        snackbarHostState.showSnackbar("부시나비 코드로 변환 중...")
                                        runCatching {
                                            val holoDeltaDeck = DeckCodeConverter.importHoloDelta(raw)
                                                ?: error("홀로델타 코드 형식이 올바르지 않습니다.")
                                            val allCards = viewModel.searchDeckCards("", limit = 5000)
                                            val byNumber = allCards.associateBy { it.cardNumber.uppercase() }
                                            val entries = mutableListOf<Triple<String, Int, DeckCardCandidate>>()
                                            byNumber[holoDeltaDeck.oshiCardNumber.uppercase()]?.let {
                                                entries += Triple(it.cardNumber, 1, it)
                                            }
                                            holoDeltaDeck.deckEntries.forEach { row ->
                                                byNumber[row.cardNumber.uppercase()]?.let {
                                                    entries += Triple(it.cardNumber, row.qty, it)
                                                }
                                            }
                                            holoDeltaDeck.cheerEntries.forEach { row ->
                                                byNumber[row.cardNumber.uppercase()]?.let {
                                                    entries += Triple(it.cardNumber, row.qty, it)
                                                }
                                            }
                                            if (entries.isEmpty()) error("카드 정보를 찾을 수 없습니다.")
                                            val dbRepo = viewModel.getDbRepository()
                                            DeckCodeConverter.publishBushiDeck(
                                                entries = entries,
                                                title = holoDeltaDeck.deckName ?: "변환 덱",
                                                manageIdLookup = { printId -> dbRepo.getManageIdJp(printId) },
                                            )
                                        }.onSuccess { url ->
                                            val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? ClipboardManager
                                            clipboard?.setPrimaryClip(ClipData.newPlainText("bushiroad_deck_url", url))
                                            deckImportText = ""
                                            showingDeckImportDialog = false
                                            snackbarHostState.showSnackbar("부시나비 URL이 클립보드에 복사되었습니다.")
                                        }.onFailure { e ->
                                            snackbarHostState.showSnackbar("변환 실패: ${e.message?.take(80)}")
                                        }
                                    }
                                    DeckImportMode.BUSHIROAD -> {
                                        snackbarHostState.showSnackbar("홀로듀얼 코드로 변환 중...")
                                        runCatching {
                                            val bushiDeck = DeckCodeConverter.fetchBushiDeck(raw)
                                            val allCards = viewModel.searchDeckCards("", limit = 5000)
                                            val byNumber = allCards.associateBy { it.cardNumber.uppercase() }
                                            val entries = (bushiDeck.pList + bushiDeck.list + bushiDeck.subList).mapNotNull { bc ->
                                                byNumber[bc.cardNumber.uppercase()]?.let { Triple(it.cardNumber, bc.num, it) }
                                            }
                                            DeckCodeConverter.exportHoloDuel(entries)
                                        }.onSuccess { code ->
                                            if (code.isNullOrBlank()) {
                                                snackbarHostState.showSnackbar("변환 실패: 오시 카드가 없습니다.")
                                            } else {
                                                val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? ClipboardManager
                                                clipboard?.setPrimaryClip(ClipData.newPlainText("holoduel_deck_code", code))
                                                deckImportText = ""
                                                showingDeckImportDialog = false
                                                snackbarHostState.showSnackbar("홀로듀얼 코드가 클립보드에 복사되었습니다.")
                                            }
                                        }.onFailure { e ->
                                            snackbarHostState.showSnackbar("변환 실패: ${e.message?.take(80)}")
                                        }
                                    }
                                }
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(
                            when (deckImportMode) {
                                DeckImportMode.HOLODUEL -> "홀로델타 코드로 변환"
                                DeckImportMode.HOLODELTA -> "부시나비 코드로 변환"
                                DeckImportMode.BUSHIROAD -> "홀로듀얼 코드로 변환"
                            }
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val raw = deckImportText.trim()
                        if (raw.isEmpty()) {
                            scope.launch { snackbarHostState.showSnackbar("가져오기 코드가 비어 있습니다.") }
                            return@TextButton
                        }
                        showingDeckImportDialog = false
                        when (deckImportMode) {
                            DeckImportMode.HOLODUEL -> scope.launch {
                                // 1) HoloDuel Base64 시도
                                val holoDuelDeck = withContext(Dispatchers.IO) {
                                    DeckCodeConverter.importHoloDuel(raw)
                                }
                                if (holoDuelDeck != null) {
                                    val allCards = viewModel.searchDeckCards("", limit = 5000)
                                    val byNumber = allCards.associateBy { it.cardNumber.uppercase() }
                                    val entries = mutableListOf<DeckEntryUi>()
                                    byNumber[holoDuelDeck.oshiCardNumber.uppercase()]?.let {
                                        entries += DeckEntryUi(it, 1, maxPerCard(it))
                                    }
                                    for ((cn, qty) in holoDuelDeck.deckEntries) {
                                        byNumber[cn.uppercase()]?.let { entries += DeckEntryUi(it, qty, maxPerCard(it)) }
                                    }
                                    for ((cn, qty) in holoDuelDeck.cheerEntries) {
                                        byNumber[cn.uppercase()]?.let { entries += DeckEntryUi(it, qty, maxPerCard(it)) }
                                    }
                                    if (entries.isEmpty()) {
                                        snackbarHostState.showSnackbar("카드 정보를 찾을 수 없습니다.")
                                    } else {
                                        val deck = DeckUi(id = java.util.UUID.randomUUID().toString(), title = "가져온 덱", entries = entries, updatedAt = System.currentTimeMillis())
                                        savedDecks.add(deck)
                                        withContext(Dispatchers.IO) { deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks))) }
                                        deckImportText = ""
                                        snackbarHostState.showSnackbar("홀로듀얼 덱 가져오기가 완료되었습니다.")
                                    }
                                    return@launch
                                }
                                // 2) 폴백: 기존 앱 JSON
                                val importedRecords = withContext(Dispatchers.IO) {
                                    runCatching { deckStorage.importText(raw) }.getOrElse { emptyList() }
                                }
                                if (importedRecords.isEmpty()) { snackbarHostState.showSnackbar("가져올 덱이 없습니다."); return@launch }
                                val allCards = viewModel.searchDeckCards("", limit = 5000)
                                val importedDecks = resolveDecksFromRecords(importedRecords, allCards)
                                if (importedDecks.isEmpty()) { snackbarHostState.showSnackbar("가져온 코드에서 카드 정보를 찾을 수 없습니다."); return@launch }
                                importedDecks.forEach { deck ->
                                    val existing = savedDecks.indexOfFirst { it.id == deck.id }
                                    if (existing >= 0) savedDecks[existing] = deck else savedDecks.add(deck)
                                }
                                withContext(Dispatchers.IO) { deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks))) }
                                deckImportText = ""
                                snackbarHostState.showSnackbar("덱 가져오기가 완료되었습니다.")
                            }
                            DeckImportMode.HOLODELTA -> scope.launch {
                                runCatching {
                                    val holoDeltaDeck = withContext(Dispatchers.IO) {
                                        DeckCodeConverter.importHoloDelta(raw)
                                    } ?: error("홀로델타 코드 형식이 올바르지 않습니다.")
                                    val allCards = viewModel.searchDeckCards("", limit = 5000)
                                    val byNumber = allCards.associateBy { it.cardNumber.uppercase() }

                                    fun selectedRarity(card: DeckCardCandidate, artIndex: Int): String? {
                                        if (artIndex < 0 || artIndex >= card.illustrations.size) return null
                                        val rarity = card.illustrations[artIndex].rarity
                                        return if (card.selectableIllustrations.any { it.rarity == rarity }) rarity else null
                                    }

                                    val entries = mutableListOf<DeckEntryUi>()
                                    byNumber[holoDeltaDeck.oshiCardNumber.uppercase()]?.let {
                                        entries += DeckEntryUi(
                                            card = it,
                                            qty = 1,
                                            maxPerCard = maxPerCard(it),
                                            selectedRarity = selectedRarity(it, holoDeltaDeck.oshiArtIndex),
                                        )
                                    }
                                    holoDeltaDeck.deckEntries.forEach { row ->
                                        byNumber[row.cardNumber.uppercase()]?.let {
                                            entries += DeckEntryUi(
                                                card = it,
                                                qty = row.qty,
                                                maxPerCard = maxPerCard(it),
                                                selectedRarity = selectedRarity(it, row.artIndex),
                                            )
                                        }
                                    }
                                    holoDeltaDeck.cheerEntries.forEach { row ->
                                        byNumber[row.cardNumber.uppercase()]?.let {
                                            entries += DeckEntryUi(
                                                card = it,
                                                qty = row.qty,
                                                maxPerCard = maxPerCard(it),
                                                selectedRarity = selectedRarity(it, row.artIndex),
                                            )
                                        }
                                    }

                                    if (entries.isEmpty()) error("카드 정보를 찾을 수 없습니다.")
                                    val title = holoDeltaDeck.deckName?.ifBlank { "홀로델타 덱" } ?: "홀로델타 덱"
                                    val deck = DeckUi(
                                        id = java.util.UUID.randomUUID().toString(),
                                        title = title,
                                        entries = entries,
                                        updatedAt = System.currentTimeMillis(),
                                    )
                                    savedDecks.add(deck)
                                    withContext(Dispatchers.IO) {
                                        deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks)))
                                    }
                                    deckImportText = ""
                                }.onSuccess {
                                    snackbarHostState.showSnackbar("홀로델타 덱 가져오기가 완료되었습니다.")
                                }.onFailure { e ->
                                    snackbarHostState.showSnackbar("홀로델타 불러오기 실패: ${e.message?.take(80)}")
                                }
                            }
                            DeckImportMode.BUSHIROAD -> scope.launch {
                                snackbarHostState.showSnackbar("부시나비에서 덱 정보를 불러오는 중...")
                                runCatching {
                                    val bushiDeck = DeckCodeConverter.fetchBushiDeck(raw)
                                    val allCards = viewModel.searchDeckCards("", limit = 5000)
                                    val byNumber = allCards.associateBy { it.cardNumber.uppercase() }
                                    val entries = (bushiDeck.pList + bushiDeck.list + bushiDeck.subList).mapNotNull { bc ->
                                        byNumber[bc.cardNumber.uppercase()]?.let { DeckEntryUi(it, bc.num, maxPerCard(it)) }
                                    }
                                    if (entries.isEmpty()) error("카드 정보를 찾을 수 없습니다.")
                                    val title = bushiDeck.title.ifBlank { "부시나비 덱" }
                                    val deck = DeckUi(id = java.util.UUID.randomUUID().toString(), title = title, entries = entries, updatedAt = System.currentTimeMillis())
                                    savedDecks.add(deck)
                                    withContext(Dispatchers.IO) { deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks))) }
                                    deckImportText = ""
                                    snackbarHostState.showSnackbar("부시나비 덱 가져오기가 완료되었습니다.")
                                }.onFailure { e ->
                                    snackbarHostState.showSnackbar("부시나비 불러오기 실패: ${e.message?.take(80)}")
                                }
                            }
                        }
                    },
                ) { Text("가져오기") }
            },
            dismissButton = {
                TextButton(onClick = { showingDeckImportDialog = false }) { Text("취소") }
            },
        )
    }

    // 레어리티 선택 BottomSheet — 기존 엔트리 변경
    rarityPickerEntry?.let { entry ->
        RarityPickerBottomSheet(
            card = entry.card,
            currentRarity = entry.displayRarity,
            onSelect = { rarity ->
                val idx = deckDraft.indexOfFirst { it.card.printId == entry.card.printId }
                if (idx >= 0) {
                    deckDraft[idx] = deckDraft[idx].copy(selectedRarity = rarity)
                }
                rarityPickerEntry = null
            },
            onDismiss = { rarityPickerEntry = null },
        )
    }

    // 레어리티 선택 BottomSheet — 새 카드 추가
    rarityPickerNewCard?.let { card ->
        RarityPickerBottomSheet(
            card = card,
            currentRarity = card.selectableIllustrations.firstOrNull()?.rarity.orEmpty(),
            onSelect = { rarity ->
                val reason = blockReason(deckDraft, card)
                if (reason == null) {
                    val existing = deckDraft.firstOrNull { it.card.printId == card.printId }
                    if (existing != null) {
                        val idx = deckDraft.indexOf(existing)
                        deckDraft[idx] = existing.copy(qty = existing.qty + 1, selectedRarity = rarity)
                    } else {
                        deckDraft.add(DeckEntryUi(card = card, qty = 1, maxPerCard = maxPerCard(card), selectedRarity = rarity))
                    }
                } else {
                    scope.launch { snackbarHostState.showSnackbar(reason) }
                }
                rarityPickerNewCard = null
            },
            onDismiss = { rarityPickerNewCard = null },
        )
    }

    ModalNavigationDrawer(
        modifier = Modifier
            .fillMaxSize()
            .clearFocusOnTap(focusManager),
        drawerState = drawerState,
        gesturesEnabled = isMobileLayout || forceDesktopLandscape,
        drawerContent = {
            ModalDrawerSheet {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Text("메뉴", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    ElevatedButton(
                        onClick = {
                            scope.launch {
                                drawerState.close()
                            }
                            viewModel.onBulkImageDownload()
                        },
                        enabled = !state.updateRunning,
                    ) {
                        Text("이미지 일괄 다운로드 (오프라인)")
                    }
                    ElevatedButton(
                        onClick = {
                            scope.launch {
                                drawerState.close()
                            }
                            viewModel.onManualUpdate()
                        },
                        enabled = !state.updateRunning,
                    ) {
                        Text("DB 수동갱신")
                    }
                    HorizontalDivider()
                    Text("테마", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    AppThemeMode.entries.forEach { mode ->
                        ThemeModeItem(
                            mode = mode,
                            selectedMode = themeMode,
                            onSelected = onThemeModeChange,
                        )
                    }
                    HorizontalDivider()
                    Text("선호 언어", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    PreferredLanguage.entries.forEach { language ->
                        PreferredLanguageItem(
                            language = language,
                            selectedLanguage = preferredLanguage,
                            onSelected = onPreferredLanguageChange,
                        )
                    }
                    HorizontalDivider()
                    Text("About", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    Text(
                        text = "Deck conversion uses hocg-deck-convert. Licensed under MIT.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                    TextButton(onClick = {
                        openExternalUrl(context, "https://github.com/Qrimpuff/hocg-deck-convert")
                    }) {
                        Text("hocg-deck-convert GitHub")
                    }
                    TextButton(onClick = {
                        openExternalUrl(context, "https://github.com/Qrimpuff/hocg-deck-convert/blob/main/LICENSE")
                    }) {
                        Text("MIT License")
                    }
                }
            }
        },
    ) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
        ) { innerPadding ->
            if (showDeckList) {
                DeckListScreen(
                    innerPadding = innerPadding,
                    decks = savedDecks,
                    onBack = { showDeckList = false },
                    onImport = {
                        deckImportText = ""
                        showingDeckImportDialog = true
                    },
                    onExportCode = { deck ->
                        val entries = deck.entries.map { Triple(it.card.cardNumber, it.qty, it.card) }
                        val code = DeckCodeConverter.exportHoloDuel(entries)
                        if (code == null) {
                            scope.launch { snackbarHostState.showSnackbar("오시 카드가 없습니다. 덱을 확인해 주세요.") }
                        } else {
                            val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? ClipboardManager
                            clipboard?.setPrimaryClip(ClipData.newPlainText("holoduel_deck_code", code))
                            scope.launch { snackbarHostState.showSnackbar("홀로듀얼 코드가 클립보드에 복사되었습니다.") }
                        }
                    },
                    onExportDelta = { deck ->
                        scope.launch {
                            val entries = deck.entries.map { Triple(it.card.cardNumber, it.qty, it.card) }
                            val code = DeckCodeConverter.exportHoloDelta(entries, title = deck.title)
                            if (code.isNullOrBlank()) {
                                snackbarHostState.showSnackbar("오시 카드가 없습니다. 덱을 확인해 주세요.")
                            } else {
                                val ok = saveDeckJsonToDownloads(
                                    context = context,
                                    deckTitle = deck.title,
                                    jsonText = code,
                                )
                                if (ok) {
                                    snackbarHostState.showSnackbar("홀로델타 .json 파일을 Downloads에 저장했습니다.")
                                } else {
                                    snackbarHostState.showSnackbar("홀로델타 .json 파일 저장에 실패했습니다.")
                                }
                            }
                        }
                    },
                    onExportBushi = { deck ->
                        scope.launch {
                            snackbarHostState.showSnackbar("부시나비에 업로드 중...")
                            val entries = deck.entries.map { Triple(it.card.cardNumber, it.qty, it.card) }
                            runCatching {
                                val dbRepo = viewModel.getDbRepository()
                                val url = DeckCodeConverter.publishBushiDeck(
                                    entries = entries,
                                    title = deck.title,
                                    manageIdLookup = { printId -> dbRepo.getManageIdJp(printId) },
                                )
                                val clipboard = context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? ClipboardManager
                                clipboard?.setPrimaryClip(ClipData.newPlainText("bushiroad_deck_url", url))
                                snackbarHostState.showSnackbar("부시나비 URL이 클립보드에 복사되었습니다.")
                            }.onFailure { e ->
                                snackbarHostState.showSnackbar("부시나비 업로드 실패: ${e.message?.take(80)}")
                            }
                        }
                    },
                    onExportImage = { deck ->
                        scope.launch {
                            snackbarHostState.showSnackbar("덱 이미지를 생성하는 중입니다...")
                            val bitmap = withContext(Dispatchers.IO) {
                                buildDeckExportBitmap(
                                    context = context,
                                    imageLoader = imageLoader,
                                    deck = deck,
                                )
                            }
                            if (bitmap == null) {
                                snackbarHostState.showSnackbar("덱 이미지 생성에 실패했습니다.")
                                return@launch
                            }
                            val ok = saveDeckBitmapToGallery(
                                context = context,
                                deckTitle = deck.title,
                                bitmap = bitmap,
                            )
                            snackbarHostState.showSnackbar(
                                if (ok) "덱 이미지가 갤러리에 저장되었습니다." else "덱 이미지 저장에 실패했습니다. 권한을 확인해 주세요."
                            )
                        }
                    },
                    onAdd = {
                        deckTitle = "새 덱"
                        deckDraft.clear()
                        editingDeckId = null
                        openDeckBuilder()
                    },
                    onEdit = { deck ->
                        editingDeckId = deck.id
                        deckTitle = deck.title
                        deckDraft.clear()
                        deckDraft.addAll(deck.entries.map { it.copy() })
                        openDeckBuilder()
                    },
                    onRename = { deck ->
                        renamingDeckId = deck.id
                        renamingDeckTitle = deck.title
                    },
                    onDelete = { deck ->
                        savedDecks.removeAll { it.id == deck.id }
                        if (editingDeckId == deck.id) {
                            editingDeckId = null
                            deckDraft.clear()
                            deckTitle = "새 덱"
                        }
                        scope.launch(Dispatchers.IO) {
                            deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks)))
                        }
                    },
                )
            } else if (showDeckEditor) {
                DeckEditorScreen(
                    innerPadding = innerPadding,
                    title = deckTitle,
                    entries = deckDraft,
                    searchQuery = deckSearchQuery,
                    candidates = deckCandidates,
                    onTitleChange = { deckTitle = it },
                    onCancel = { showDeckEditor = false },
                    onOpenDeckList = {
                        showDeckEditor = false
                        showDeckList = true
                    },
                    onSave = {
                        val snapshot = deckDraft.groupBy { it.card.printId }.values.map { g ->
                            val first = g.first()
                            DeckEntryUi(first.card, g.sumOf { it.qty }, first.maxPerCard, first.selectedRarity)
                        }
                        val now = System.currentTimeMillis()
                        val targetId = editingDeckId ?: UUID.randomUUID().toString()
                        val deck = DeckUi(
                            id = targetId,
                            title = deckTitle.ifBlank { "덱" },
                            entries = snapshot,
                            updatedAt = now,
                        )
                        val existing = savedDecks.indexOfFirst { it.id == targetId }
                        if (existing >= 0) {
                            savedDecks[existing] = deck
                        } else {
                            savedDecks.add(deck)
                        }
                        editingDeckId = targetId
                        scope.launch(Dispatchers.IO) {
                            deckStorage.saveLibrary(DeckLibraryRecord(decks = toDeckRecords(savedDecks)))
                        }
                        showDeckEditor = false
                        showDeckList = true
                    },
                    onSearchQueryChange = {
                        deckSearchQuery = it
                        scope.launch { deckCandidates = viewModel.searchDeckCards(deckSearchQuery) }
                    },
                    onSelectCandidate = { card ->
                        if (card.hasMultipleRarities) {
                            rarityPickerNewCard = card
                        } else {
                            val reason = addCardToDeck(deckDraft, card)
                            if (reason != null) {
                                scope.launch { snackbarHostState.showSnackbar(reason) }
                            }
                        }
                    },
                    onChangeRarity = { entry ->
                        rarityPickerEntry = entry
                    },
                    quantityForCard = { card -> deckQuantity(deckDraft, card) },
                    onIncrease = { printId ->
                        val reason = increaseDeckEntryByPrintId(deckDraft, printId)
                        if (reason != null) {
                            scope.launch { snackbarHostState.showSnackbar(reason) }
                        }
                    },
                    onDecrease = { printId ->
                        decreaseDeckEntryByPrintId(deckDraft, printId)
                    },
                )
            } else if (isMobileLayout) {
                MobileLayout(
                    state = state,
                    innerPadding = innerPadding,
                    onSearchQueryChanged = viewModel::onSearchQueryChanged,
                    onOpenDeckBuilder = openDeckBuilder,
                    onOpenMenu = { scope.launch { drawerState.open() } },
                    onDismissKeyboard = { focusManager.clearFocus() },
                    onSelectPrint = viewModel::onSelectPrint,
                    onSelectIllustration = viewModel::onSelectIllustration,
                    onToggleImagePanel = viewModel::onToggleImagePanel,
                    preferredLanguage = preferredLanguage,
                    multiWordTags = viewModel.multiWordTags,
                )
            } else {
                DesktopLayout(
                    state = state,
                    innerPadding = innerPadding,
                    onSearchQueryChanged = viewModel::onSearchQueryChanged,
                    onOpenDeckBuilder = openDeckBuilder,
                    onDismissKeyboard = { focusManager.clearFocus() },
                    onOpenMenu = { scope.launch { drawerState.open() } },
                    showMenuButton = forceDesktopLandscape,
                    keepSearchBarTop = forceDesktopLandscape,
                    twoPaneLandscape = forceDesktopLandscape,
                    onSelectPrint = viewModel::onSelectPrint,
                    onSelectIllustration = viewModel::onSelectIllustration,
                    preferredLanguage = preferredLanguage,
                    multiWordTags = viewModel.multiWordTags,
                )
            }
        }
    }
}

@Composable
private fun DeckListScreen(
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    decks: List<DeckUi>,
    onBack: () -> Unit,
    onImport: () -> Unit,
    onExportCode: (DeckUi) -> Unit,
    onExportDelta: (DeckUi) -> Unit,
    onExportBushi: (DeckUi) -> Unit,
    onExportImage: (DeckUi) -> Unit,
    onAdd: () -> Unit,
    onEdit: (DeckUi) -> Unit,
    onRename: (DeckUi) -> Unit,
    onDelete: (DeckUi) -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(innerPadding).padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedButton(
                    onClick = onBack,
                    contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
                ) { Text("뒤로") }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedButton(
                        onClick = onImport,
                        contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
                    ) { Text("가져오기") }
                    FilledTonalButton(
                        onClick = onAdd,
                        contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
                    ) { Icon(Icons.Default.Add, contentDescription = "추가") }
                }
            }
            Text(
                text = "덱 리스트",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.align(Alignment.Center),
            )
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(decks.indices.toList(), key = { decks[it].id }) { idx ->
                val deck = decks[idx]
                var menuExpanded by remember(deck.id) { mutableStateOf(false) }
                var exportMenuExpanded by remember(deck.id) { mutableStateOf(false) }
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(10.dp))
                        .padding(10.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = deck.title,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier
                                .weight(1f)
                                .clickable { onEdit(deck) }
                                .padding(vertical = 4.dp),
                        )
                        Box {
                            IconButton(onClick = { menuExpanded = true }) {
                                Icon(Icons.Default.MoreVert, contentDescription = "덱 메뉴")
                            }
                            DropdownMenu(
                                expanded = menuExpanded,
                                onDismissRequest = {
                                    menuExpanded = false
                                    exportMenuExpanded = false
                                },
                            ) {
                                DropdownMenuItem(
                                    text = { Text("이름 수정") },
                                    onClick = {
                                        menuExpanded = false
                                        exportMenuExpanded = false
                                        onRename(deck)
                                    },
                                )
                                DropdownMenuItem(
                                    text = {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically,
                                        ) {
                                            Text("코드로 내보내기")
                                            Icon(
                                                imageVector = if (exportMenuExpanded) Icons.Default.KeyboardArrowDown else Icons.Default.KeyboardArrowRight,
                                                contentDescription = null,
                                                modifier = Modifier.size(18.dp),
                                            )
                                        }
                                    },
                                    onClick = {
                                        exportMenuExpanded = !exportMenuExpanded
                                    },
                                )
                                if (exportMenuExpanded) {
                                    DropdownMenuItem(
                                        text = { Text("홀로듀얼 코드") },
                                        onClick = {
                                            menuExpanded = false
                                            exportMenuExpanded = false
                                            onExportCode(deck)
                                        },
                                    )
                                    DropdownMenuItem(
                                        text = { Text("홀로델타 .json 파일") },
                                        onClick = {
                                            menuExpanded = false
                                            exportMenuExpanded = false
                                            onExportDelta(deck)
                                        },
                                    )
                                    DropdownMenuItem(
                                        text = { Text("부시나비 코드") },
                                        onClick = {
                                            menuExpanded = false
                                            exportMenuExpanded = false
                                            onExportBushi(deck)
                                        },
                                    )
                                }
                                DropdownMenuItem(
                                    text = { Text("이미지로 내보내기") },
                                    onClick = {
                                        menuExpanded = false
                                        exportMenuExpanded = false
                                        onExportImage(deck)
                                    },
                                )
                                DropdownMenuItem(
                                    text = { Text("삭제") },
                                    onClick = {
                                        menuExpanded = false
                                        exportMenuExpanded = false
                                        onDelete(deck)
                                    },
                                )
                            }
                        }
                    }
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onEdit(deck) },
                    ) {
                        deck.entries.take(8).forEach { entry ->
                            DeckThumbnail(
                                imageUrl = entry.effectiveImageUrl,
                                qty = entry.qty,
                                width = 42.dp,
                                height = 58.dp,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DeckEditorScreen(
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    title: String,
    entries: List<DeckEntryUi>,
    searchQuery: String,
    candidates: List<DeckCardCandidate>,
    onTitleChange: (String) -> Unit,
    onCancel: () -> Unit,
    onOpenDeckList: () -> Unit,
    onSave: () -> Unit,
    onSearchQueryChange: (String) -> Unit,
    onSelectCandidate: (DeckCardCandidate) -> Unit,
    quantityForCard: (DeckCardCandidate) -> Int,
    onIncrease: (Long) -> Unit,
    onDecrease: (Long) -> Unit,
    onChangeRarity: (DeckEntryUi) -> Unit = {},
) {
    val oshi = entries.filter { isOshi(it.card) }.sumOf { it.qty }
    val yell = entries.filter { isYell(it.card) }.sumOf { it.qty }
    val main = entries.filter { !isOshi(it.card) && !isYell(it.card) }.sumOf { it.qty }
    val total = entries.sumOf { it.qty }
    var showSelectedCards by rememberSaveable { mutableStateOf(true) }
    Column(modifier = Modifier.fillMaxSize().padding(innerPadding).padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedButton(
                onClick = onCancel,
                contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
            ) { Text("취소") }
            OutlinedTextField(
                value = title,
                onValueChange = onTitleChange,
                singleLine = true,
                modifier = Modifier.weight(1f),
                label = { Text("덱 이름") },
            )
            OutlinedButton(
                onClick = onOpenDeckList,
                contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
            ) { Text("덱 목록") }
            FilledTonalButton(
                onClick = onSave,
                contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
            ) { Text("저장") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("오시 $oshi/1")
            Text("옐 $yell/20")
            Text("덱 $main/50")
            Text("합계 $total")
        }
        OutlinedTextField(
            value = searchQuery,
            onValueChange = onSearchQueryChange,
            label = { Text("카드 검색") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(260.dp)
                .border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(10.dp))
                .padding(8.dp),
        ) {
            if (candidates.isEmpty()) {
                Text("검색 결과가 없습니다.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(candidates, key = { it.printId }) { card ->
                        val qty = quantityForCard(card)
                        val maxQty = entries.firstOrNull { it.card.printId == card.printId }?.maxPerCard ?: maxPerCard(card)
                        val blockedReason = blockReason(entries, card)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .clickable { onSelectCandidate(card) }
                                .padding(horizontal = 6.dp, vertical = 4.dp)
                                .alpha(if (blockedReason == null) 1f else 0.45f),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            DeckThumbnail(
                                imageUrl = card.selectableIllustrations.firstOrNull()?.imageUrl?.takeIf { it.isNotBlank() } ?: card.imageUrl,
                                qty = qty,
                                width = 36.dp,
                                height = 50.dp,
                            )
                            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                Text("${card.cardNumber} | ${card.nameKo.ifBlank { card.nameJa }}", maxLines = 1, overflow = TextOverflow.Ellipsis)
                            }
                            Text(
                                text = if (maxQty == Int.MAX_VALUE) "${qty}/∞" else "${qty}/${maxQty}",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = if (blockedReason == null) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.error,
                            )
                        }
                    }
                }
            }
        }
        if (showSelectedCards && entries.isNotEmpty()) {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.weight(1f, fill = true)) {
                items(entries, key = { it.card.printId }) { entry ->
                    Row(modifier = Modifier.fillMaxWidth().border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(10.dp)).padding(8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        DeckThumbnail(
                            imageUrl = entry.effectiveImageUrl,
                            qty = entry.qty,
                            width = 50.dp,
                            height = 70.dp,
                        )
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text("${entry.card.cardNumber} | ${entry.card.nameKo.ifBlank { entry.card.nameJa }}", maxLines = 1, overflow = TextOverflow.Ellipsis)
                            if (entry.card.hasMultipleRarities) {
                                Row(
                                    modifier = Modifier
                                        .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(999.dp))
                                        .clickable { onChangeRarity(entry) }
                                        .padding(horizontal = 8.dp, vertical = 3.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                                ) {
                                    Text(entry.displayRarity, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimaryContainer, fontWeight = FontWeight.Bold)
                                    Icon(Icons.Default.KeyboardArrowDown, contentDescription = "레어리티 변경", modifier = Modifier.size(12.dp), tint = MaterialTheme.colorScheme.onPrimaryContainer)
                                }
                            }
                        }
                        val blockedReason = blockReason(entries, entry.card)
                        IconButton(
                            onClick = { onDecrease(entry.card.printId) },
                        ) { Icon(Icons.Default.Remove, contentDescription = "감소") }
                        IconButton(
                            onClick = { onIncrease(entry.card.printId) },
                            enabled = blockedReason == null,
                        ) { Icon(Icons.Default.Add, contentDescription = "증가") }
                    }
                }
            }
        }
        if (entries.isNotEmpty()) {
            SelectedCardsActionBar(
                selectedCount = entries.size,
                totalCount = total,
                expanded = showSelectedCards,
                onToggle = { showSelectedCards = !showSelectedCards },
            )
        }
    }
}

@Composable
private fun MobileLayout(
    state: HocgUiState,
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    onSearchQueryChanged: (String) -> Unit,
    onOpenDeckBuilder: () -> Unit,
    onOpenMenu: () -> Unit,
    onDismissKeyboard: () -> Unit,
    onSelectPrint: (Long) -> Unit,
    onSelectIllustration: (String, String) -> Unit,
    onToggleImagePanel: () -> Unit,
    preferredLanguage: PreferredLanguage,
    multiWordTags: List<String> = emptyList(),
) {
    val listHeight = snappedListHeightDp(scaledHeightDp(ratio = 0.30f, minPx = 190, maxPx = 360))
    val imageHeight = scaledHeightDp(ratio = 0.45f, minPx = 240, maxPx = 560)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(innerPadding)
            .padding(horizontal = 10.dp, vertical = 6.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                modifier = Modifier.weight(1f),
                value = state.searchQuery,
                onValueChange = onSearchQueryChanged,
                label = { Text("카드번호 / 이름 / 태그 / 한국어 본문 검색") },
                enabled = !state.updateRunning,
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { onDismissKeyboard() }),
            )
            FilledTonalButton(
                onClick = {
                    onDismissKeyboard()
                    onOpenDeckBuilder()
                },
                enabled = !state.updateRunning,
            ) { Text("덱빌딩") }
            IconButton(
                onClick = {
                    onDismissKeyboard()
                    onOpenMenu()
                },
                enabled = !state.updateRunning,
            ) {
                Icon(Icons.Default.Menu, contentDescription = "메뉴")
            }
        }

        UpdateStatusBlock(state)

        HorizontalDivider()

        Text("목록", style = MaterialTheme.typography.titleSmall)
        Panel(
            modifier = Modifier
                .fillMaxWidth()
                .height(listHeight),
        ) {
            ResultsList(
                state = state,
                onSelect = onSelectPrint,
                preferredLanguage = preferredLanguage,
                multiWordTags = multiWordTags,
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("이미지", style = MaterialTheme.typography.titleSmall)
            TextButton(onClick = onToggleImagePanel) {
                Text(if (state.imageCollapsed) "이미지 펼치기" else "이미지 접기")
            }
        }

        if (state.imageCollapsed) {
            Text("이미지를 접었습니다.", style = MaterialTheme.typography.bodySmall)
        } else {
            SearchRaritySelector(
                selectedRarity = state.selectedRarity,
                illustrations = state.selectedIllustrations,
                fallbackImageUrl = state.selectedImageUrl,
                onSelect = onSelectIllustration,
            )
            Panel(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(imageHeight),
            ) {
                InteractiveImagePanel(
                    imageState = state.imageState,
                    selectedRarity = state.selectedRarity,
                    illustrations = state.selectedIllustrations,
                    fallbackImageUrl = state.selectedImageUrl,
                    onSelectIllustration = onSelectIllustration,
                )
            }
        }

        Text("효과", style = MaterialTheme.typography.titleSmall)
        Panel(modifier = Modifier.fillMaxWidth()) {
            DetailPanel(
                koText = state.detailKoText,
                jaText = state.detailJaText,
                detailLoading = state.detailLoading,
                preferredLanguage = preferredLanguage,
                scrollable = false,
                multiWordTags = multiWordTags,
            )
        }
    }
}

@Composable
private fun DesktopLayout(
    state: HocgUiState,
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    onSearchQueryChanged: (String) -> Unit,
    onOpenDeckBuilder: () -> Unit,
    onDismissKeyboard: () -> Unit,
    onOpenMenu: () -> Unit,
    showMenuButton: Boolean,
    keepSearchBarTop: Boolean,
    twoPaneLandscape: Boolean,
    onSelectPrint: (Long) -> Unit,
    onSelectIllustration: (String, String) -> Unit,
    preferredLanguage: PreferredLanguage,
    multiWordTags: List<String> = emptyList(),
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(innerPadding)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (keepSearchBarTop) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = state.searchQuery,
                    onValueChange = onSearchQueryChanged,
                    label = { Text("카드번호 / 이름 / 태그 / 한국어 본문 검색") },
                    enabled = !state.updateRunning,
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { onDismissKeyboard() }),
                )
                FilledTonalButton(
                    onClick = {
                        onDismissKeyboard()
                        onOpenDeckBuilder()
                    },
                    enabled = !state.updateRunning,
                ) { Text("덱빌딩") }
                if (state.updateRunning) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                    )
                }
                if (showMenuButton) {
                    IconButton(
                        onClick = {
                            onDismissKeyboard()
                            onOpenMenu()
                        },
                        enabled = !state.updateRunning,
                    ) {
                        Icon(Icons.Default.Menu, contentDescription = "메뉴")
                    }
                }
            }
            if (state.dbPath.isNotBlank()) {
                Text(
                    text = "DB: ${state.dbPath}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        } else {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = state.dbPath,
                    onValueChange = {},
                    readOnly = true,
                    enabled = !state.updateRunning,
                    label = { Text("DB") },
                    singleLine = true,
                )
                if (state.updateRunning) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                    )
                }
            }

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedTextField(
                    modifier = Modifier.weight(1f),
                    value = state.searchQuery,
                    onValueChange = onSearchQueryChanged,
                    label = { Text("카드번호 / 이름 / 태그 / 한국어 본문 검색") },
                    enabled = !state.updateRunning,
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { onDismissKeyboard() }),
                )
                FilledTonalButton(
                    onClick = {
                        onDismissKeyboard()
                        onOpenDeckBuilder()
                    },
                    enabled = !state.updateRunning,
                ) { Text("덱빌딩") }
                if (showMenuButton) {
                    IconButton(
                        onClick = {
                            onDismissKeyboard()
                            onOpenMenu()
                        },
                        enabled = !state.updateRunning,
                    ) {
                        Icon(Icons.Default.Menu, contentDescription = "메뉴")
                    }
                }
            }
        }

        UpdateStatusBlock(state)
        HorizontalDivider()

        if (twoPaneLandscape) {
            Row(modifier = Modifier.fillMaxSize()) {
                Column(modifier = Modifier.weight(4f).fillMaxSize()) {
                    Text("목록", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                    Panel(modifier = Modifier.fillMaxSize()) {
                        ResultsList(state = state, onSelect = onSelectPrint, preferredLanguage = preferredLanguage, multiWordTags = multiWordTags)
                    }
                }

                VerticalDivider(modifier = Modifier.width(1.dp))

                Column(
                    modifier = Modifier.weight(7f).fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Column(modifier = Modifier.weight(6f).fillMaxWidth()) {
                        Text("이미지", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                        SearchRaritySelector(
                            selectedRarity = state.selectedRarity,
                            illustrations = state.selectedIllustrations,
                            fallbackImageUrl = state.selectedImageUrl,
                            onSelect = onSelectIllustration,
                        )
                        Panel(modifier = Modifier.fillMaxSize()) {
                            InteractiveImagePanel(
                                imageState = state.imageState,
                                selectedRarity = state.selectedRarity,
                                illustrations = state.selectedIllustrations,
                                fallbackImageUrl = state.selectedImageUrl,
                                onSelectIllustration = onSelectIllustration,
                            )
                        }
                    }

                    Column(modifier = Modifier.weight(4f).fillMaxWidth()) {
                        Text("효과", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                        Panel(modifier = Modifier.fillMaxSize()) {
                            DetailPanel(
                                koText = state.detailKoText,
                                jaText = state.detailJaText,
                                detailLoading = state.detailLoading,
                                preferredLanguage = preferredLanguage,
                                scrollable = true,
                                multiWordTags = multiWordTags,
                            )
                        }
                    }
                }
            }
        } else {
            Row(modifier = Modifier.fillMaxSize()) {
                Column(modifier = Modifier.weight(3f)) {
                    Text("목록", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                    Panel(modifier = Modifier.fillMaxSize()) {
                        ResultsList(state = state, onSelect = onSelectPrint, preferredLanguage = preferredLanguage, multiWordTags = multiWordTags)
                    }
                }

                VerticalDivider(modifier = Modifier.width(1.dp))

                Column(modifier = Modifier.weight(6f)) {
                    Text("이미지", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                    SearchRaritySelector(
                        selectedRarity = state.selectedRarity,
                        illustrations = state.selectedIllustrations,
                        fallbackImageUrl = state.selectedImageUrl,
                        onSelect = onSelectIllustration,
                    )
                    Panel(modifier = Modifier.fillMaxSize()) {
                        InteractiveImagePanel(
                            imageState = state.imageState,
                            selectedRarity = state.selectedRarity,
                            illustrations = state.selectedIllustrations,
                            fallbackImageUrl = state.selectedImageUrl,
                            onSelectIllustration = onSelectIllustration,
                        )
                    }
                }

                VerticalDivider(modifier = Modifier.width(1.dp))

                Column(modifier = Modifier.weight(4f)) {
                    Text("효과", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                    Panel(modifier = Modifier.fillMaxSize()) {
                        DetailPanel(
                            koText = state.detailKoText,
                            jaText = state.detailJaText,
                            detailLoading = state.detailLoading,
                            preferredLanguage = preferredLanguage,
                            scrollable = true,
                            multiWordTags = multiWordTags,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun UpdateStatusBlock(state: HocgUiState) {
    if (state.updateStatus.isNotBlank()) {
        Text(
            text = state.updateStatus,
            color = if (state.updateStatusError) {
                MaterialTheme.colorScheme.error
            } else {
                MaterialTheme.colorScheme.tertiary
            },
            style = MaterialTheme.typography.bodySmall,
        )
    }

    if (!state.persistentMessage.isNullOrBlank()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    color = MaterialTheme.colorScheme.errorContainer,
                    shape = RoundedCornerShape(12.dp),
                )
                .padding(horizontal = 12.dp, vertical = 10.dp),
        ) {
            Text(
                text = state.persistentMessage,
                color = MaterialTheme.colorScheme.onErrorContainer,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun Panel(
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(
        modifier = modifier
            .border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(10.dp))
            .padding(10.dp),
        content = content,
    )
}

@Composable
private fun ResultsList(
    state: HocgUiState,
    onSelect: (Long) -> Unit,
    preferredLanguage: PreferredLanguage,
    multiWordTags: List<String> = emptyList(),
) {
    if (state.results.isEmpty()) {
        Text(
            text = "검색 결과가 없습니다.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.outline,
        )
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .nestedScroll(ConsumeScrollNestedScrollConnection),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        items(state.results, key = { it.printId }) { row ->
            ResultItem(
                row = row,
                selected = state.selectedPrintId == row.printId,
                onClick = { onSelect(row.printId) },
                preferredLanguage = preferredLanguage,
            )
        }
    }
}

@Composable
private fun ResultItem(row: PrintRow, selected: Boolean, onClick: () -> Unit, preferredLanguage: PreferredLanguage) {
    val displayName = when (preferredLanguage) {
        PreferredLanguage.KOREAN -> {
            val cleanKo = DbRepository.cleanDisplayName(row.nameKo)
            cleanKo.ifBlank { row.nameJa }
        }
        PreferredLanguage.JAPANESE -> row.nameJa.ifBlank { DbRepository.cleanDisplayName(row.nameKo) }
    }.ifBlank { "(이름 없음)" }
    val title = if (row.cardNumber.isNotBlank()) {
        "${row.cardNumber} | $displayName"
    } else {
        displayName
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface,
                shape = RoundedCornerShape(8.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 9.dp),
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.bodyMedium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ImagePanel(imageState: ImageState) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        when (imageState) {
            is ImageState.Local -> {
                AsyncImage(
                    model = imageState.file,
                    contentDescription = "카드 이미지",
                    modifier = Modifier.fillMaxSize(),
                )
            }

            is ImageState.Remote -> {
                AsyncImage(
                    model = imageState.url,
                    contentDescription = "카드 이미지",
                    modifier = Modifier.fillMaxSize(),
                )
            }

            ImageState.Loading -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    CircularProgressIndicator(strokeWidth = 2.dp)
                    Text("이미지 로딩 중...", style = MaterialTheme.typography.bodySmall)
                }
            }

            is ImageState.Placeholder -> {
                Placeholder(imageState.message, error = false)
            }

            is ImageState.Error -> {
                Placeholder(imageState.message, error = true)
            }
        }
    }
}

@Composable
private fun InteractiveImagePanel(
    imageState: ImageState,
    selectedRarity: String,
    illustrations: List<com.smalltyrant.hocgh.model.IllustrationOption>,
    fallbackImageUrl: String,
    onSelectIllustration: (String, String) -> Unit,
) {
    var zoomedModel by remember { mutableStateOf<Any?>(null) }
    val swipeThreshold = 72f

    Box(
        modifier = Modifier
            .fillMaxSize()
            .clip(RoundedCornerShape(10.dp))
            .clickable(enabled = currentImageModel(imageState) != null) {
                zoomedModel = currentImageModel(imageState)
            }
            .pointerInput(selectedRarity, illustrations, fallbackImageUrl) {
                var totalDrag = 0f
                detectHorizontalDragGestures(
                    onDragStart = { totalDrag = 0f },
                    onHorizontalDrag = { _, dragAmount ->
                        totalDrag += dragAmount
                    },
                    onDragEnd = {
                        val adjacent = when {
                            totalDrag <= -swipeThreshold -> findAdjacentIllustration(selectedRarity, illustrations, fallbackImageUrl, +1)
                            totalDrag >= swipeThreshold -> findAdjacentIllustration(selectedRarity, illustrations, fallbackImageUrl, -1)
                            else -> null
                        }
                        adjacent?.let { (rarity, imageUrl) ->
                            onSelectIllustration(rarity, imageUrl)
                        }
                    },
                )
            },
    ) {
        ImagePanel(imageState)
    }

    if (zoomedModel != null) {
        FullscreenImageDialog(
            model = zoomedModel!!,
            onDismiss = { zoomedModel = null },
        )
    }
}

@Composable
private fun FullscreenImageDialog(
    model: Any,
    onDismiss: () -> Unit,
) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false),
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .clickable(
                    indication = null,
                    interactionSource = remember { MutableInteractionSource() },
                    onClick = onDismiss,
                )
                .background(androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.92f)),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(18.dp)
                    .align(Alignment.Center)
                    .clickable(
                        indication = null,
                        interactionSource = remember { MutableInteractionSource() },
                        onClick = {},
                    ),
            ) {
                ZoomableAsyncImage(
                    model = model,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            IconButton(
                onClick = onDismiss,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(12.dp)
                    .background(androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.45f), RoundedCornerShape(999.dp)),
            ) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "닫기",
                    tint = androidx.compose.ui.graphics.Color.White,
                )
            }
        }
    }
}

@Composable
private fun ZoomableAsyncImage(
    model: Any,
    modifier: Modifier = Modifier,
) {
    var scale by remember(model) { mutableStateOf(1f) }
    var offset by remember(model) { mutableStateOf(Offset.Zero) }

    AsyncImage(
        model = model,
        contentDescription = "확대 카드 이미지",
        contentScale = ContentScale.Fit,
        modifier = modifier
            .graphicsLayer(
                scaleX = scale,
                scaleY = scale,
                translationX = offset.x,
                translationY = offset.y,
            )
            .pointerInput(model) {
                detectTransformGestures { _, pan, zoom, _ ->
                    val newScale = (scale * zoom).coerceIn(1f, 4f)
                    scale = newScale
                    offset = if (newScale <= 1f) {
                        Offset.Zero
                    } else {
                        offset + pan
                    }
                }
            },
    )
}

@Composable
private fun SelectedCardsActionBar(
    selectedCount: Int,
    totalCount: Int,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .clip(RoundedCornerShape(14.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f))
            .border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(14.dp))
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text("선택 ${selectedCount}장", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Text(
                "덱 합계 ${totalCount}장",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
            )
        }
        TextButton(
            onClick = onToggle,
            enabled = selectedCount > 0,
            colors = ButtonDefaults.textButtonColors(
                containerColor = MaterialTheme.colorScheme.primary.copy(alpha = if (selectedCount > 0) 0.16f else 0.08f),
                contentColor = MaterialTheme.colorScheme.primary,
            ),
        ) {
            Text(if (expanded) "선택 카드 접기" else "선택 카드")
        }
    }
}

@Composable
private fun Placeholder(message: String, error: Boolean) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(
            imageVector = if (error) Icons.Default.BrokenImage else Icons.Default.Image,
            contentDescription = null,
            modifier = Modifier.size(30.dp),
            tint = MaterialTheme.colorScheme.outline,
        )
        Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
    }
}

@Composable
private fun DetailPanel(
    koText: String,
    jaText: String,
    detailLoading: Boolean,
    preferredLanguage: PreferredLanguage,
    scrollable: Boolean,
    multiWordTags: List<String> = emptyList(),
) {
    val koLines = remember(koText, multiWordTags) { splitDetailLines(koText, language = DetailTextLanguage.KOREAN, multiWordTags = multiWordTags) }
    val jaLines = remember(jaText, multiWordTags) { splitDetailLines(jaText, language = DetailTextLanguage.JAPANESE, multiWordTags = multiWordTags) }

    // Build highlight regex once per multiWordTags change, reuse for all lines
    val highlightRegex = remember(multiWordTags) {
        val base = buildTagTokenRegex(multiWordTags)
        Regex("${base.pattern}|콜라보 이펙트|블룸 이펙트|기프트|コラボエフェクト|ブルームエフェクト|ギフト")
    }

    val hasKo = koLines.isNotEmpty()
    val hasJa = jaLines.isNotEmpty()
    val showJaFirst = !hasKo

    var koExpanded by rememberSaveable(koText, jaText, preferredLanguage) {
        mutableStateOf(hasKo && (!hasJa || preferredLanguage == PreferredLanguage.KOREAN))
    }
    var jaExpanded by rememberSaveable(koText, jaText, preferredLanguage) {
        mutableStateOf(hasJa && (!hasKo || preferredLanguage == PreferredLanguage.JAPANESE))
    }

    val contentModifier = if (scrollable) {
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    } else {
        Modifier.fillMaxWidth()
    }

    Column(
        modifier = contentModifier,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        if (!hasKo && !hasJa) {
            if (detailLoading) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    Text("(본문 로딩 중...)", style = MaterialTheme.typography.bodyMedium)
                }
            } else {
                Text("(본문 없음)", style = MaterialTheme.typography.bodyMedium)
            }
            return@Column
        }

        if (hasKo && hasJa) {
            ExpandableDetailSection(
                title = "한국어",
                lines = koLines,
                expanded = koExpanded,
                onToggle = { koExpanded = !koExpanded },
                highlightRegex = highlightRegex,
            )
            ExpandableDetailSection(
                title = "일본어",
                lines = jaLines,
                expanded = jaExpanded,
                onToggle = { jaExpanded = !jaExpanded },
                highlightRegex = highlightRegex,
            )
            return@Column
        }

        val singleTitle = if (hasKo) "한국어" else "일본어"
        val singleLines = if (showJaFirst) jaLines else koLines
        SectionChip(singleTitle)
        for (line in singleLines) {
            DetailLine(line, highlightRegex)
        }
    }
}

@Composable
private fun ExpandableDetailSection(
    title: String,
    lines: List<String>,
    expanded: Boolean,
    onToggle: () -> Unit,
    highlightRegex: Regex,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onToggle),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        SectionChip(title)
        Text(
            text = if (expanded) "접기" else "펼치기",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.primary,
        )
    }

    if (!expanded) {
        return
    }

    for (line in lines) {
        DetailLine(line, highlightRegex)
    }
}

@Composable
private fun SectionChip(text: String) {
    Box(
        modifier = Modifier
            .background(MaterialTheme.colorScheme.secondaryContainer, RoundedCornerShape(999.dp))
            .padding(horizontal = 9.dp, vertical = 4.dp),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun DetailLine(line: String, highlightRegex: Regex) {
    splitSectionLabel(line)?.let { (label, rest) ->
        if (rest.isBlank()) {
            Text(label, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(label, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text(buildHighlightedTagText(rest, MaterialTheme.colorScheme.primary, highlightRegex), style = MaterialTheme.typography.bodyMedium)
            }
        }
        return
    }

    Text(buildHighlightedTagText(line, MaterialTheme.colorScheme.primary, highlightRegex), style = MaterialTheme.typography.bodyMedium)
}

private fun buildHighlightedTagText(text: String, highlightColor: androidx.compose.ui.graphics.Color, highlightRegex: Regex) = buildAnnotatedString {
    var cursor = 0
    for (match in highlightRegex.findAll(text)) {
        if (match.range.first > cursor) {
            append(text.substring(cursor, match.range.first))
        }
        withStyle(
            SpanStyle(
                color = highlightColor,
                fontWeight = FontWeight.SemiBold,
            ),
        ) {
            append(match.value)
        }
        cursor = match.range.last + 1
    }
    if (cursor < text.length) {
        append(text.substring(cursor))
    }
}

private fun splitSectionLabel(line: String): Pair<String, String>? {
    val trimmed = line.trim()
    val separators = listOf(" ", ":", "：", "[", "(", "【")
    for (label in SECTION_LABELS_SORTED) {
        if (trimmed == label) {
            return label to ""
        }
        if (!trimmed.startsWith(label)) {
            continue
        }
        val suffix = trimmed.removePrefix(label)
        val rest = suffix.trim()
        if (rest.isEmpty()) {
            return label to ""
        }
        if (separators.any { suffix.startsWith(it) }) {
            return label to rest
        }
    }
    return null
}

private fun sanitizeDetailLine(line: String): String {
    val strippedHtml = HTML_TAG_REGEX.replace(line, " ")
    val strippedWidth = WIDTH_ARTIFACT_REGEX.replace(strippedHtml, " ")
    val trimmed = strippedWidth.trim()
    if (trimmed.isNotEmpty() && DETAIL_PREFIX_PATTERN.matches(trimmed)) {
        return trimmed
    }
    return DETAIL_PREFIX_PATTERN.replace(trimmed, "")
}

private fun mergeBrokenTagLines(lines: List<String>, tagRegex: Regex? = null): List<String> {
    val output = mutableListOf<String>()
    var index = 0

    while (index < lines.size) {
        val line = lines[index].trim()
        if (line == "태그" || line == "タグ") {
            val tags = mutableListOf<String>()
            var cursor = index

            while (cursor < lines.size) {
                val current = lines[cursor].trim()
                if (current == line && cursor + 1 < lines.size && lines[cursor + 1].trim().startsWith("#")) {
                    tags += lines[cursor + 1].trim()
                    cursor += 2
                    continue
                }
                if (current.startsWith("#")) {
                    tags += current
                    cursor += 1
                    continue
                }
                break
            }

            if (tags.isNotEmpty()) {
                output += "$line ${tags.joinToString(" ")}".trim()
                index = cursor
                continue
            }
        }

        output += lines[index]
        index += 1
    }

    return output
}

private fun splitDetailLines(text: String, language: DetailTextLanguage, multiWordTags: List<String> = emptyList()): List<String> {
    // Build tag regex once for this call — reused in normalizeTagLine
    val tagRegex = buildTagTokenRegex(multiWordTags)
    val payload = when (language) {
        DetailTextLanguage.KOREAN -> prettifyKoDetailText(text, multiWordTags, tagRegex)
        DetailTextLanguage.JAPANESE -> prettifyJaDetailText(text, multiWordTags, tagRegex)
    }
    val lines = payload.lines()
        .map(::sanitizeDetailLine)
        .map(::normalizeInlineWhitespace)
        .filter { it.isNotEmpty() }

    return mergeBrokenTagLines(lines)
}

private fun prettifyKoDetailText(text: String, multiWordTags: List<String> = emptyList(), tagRegex: Regex? = null): String {
    return prettifyDetailText(
        text = text,
        replacements = KO_DETAIL_REPLACEMENTS,
        sectionMarkerRegex = KO_SECTION_MARKER_REGEX,
        lineBreakPatterns = KO_LINE_BREAK_PATTERNS,
        sectionBreakOnceLabels = listOf("블룸 이펙트"),
        tagLabel = "태그",
        metadataTokens = KO_METADATA_TOKEN_SET,
        stripJapaneseChars = true,
        multiWordTags = multiWordTags,
        tagRegex = tagRegex,
    )
}

private fun prettifyJaDetailText(text: String, multiWordTags: List<String> = emptyList(), tagRegex: Regex? = null): String {
    return prettifyDetailText(
        text = text,
        replacements = JA_DETAIL_REPLACEMENTS,
        sectionMarkerRegex = JA_SECTION_MARKER_REGEX,
        lineBreakPatterns = JA_LINE_BREAK_PATTERNS,
        sectionBreakOnceLabels = listOf("ブルームエフェクト"),
        tagLabel = "タグ",
        metadataTokens = JA_METADATA_TOKEN_SET,
        multiWordTags = multiWordTags,
        tagRegex = tagRegex,
    )
}

private fun prettifyDetailText(
    text: String,
    replacements: List<Pair<String, String>>,
    sectionMarkerRegex: Regex,
    lineBreakPatterns: List<Pair<Regex, String>>,
    sectionBreakOnceLabels: List<String>,
    tagLabel: String,
    metadataTokens: Set<String>,
    stripJapaneseChars: Boolean = false,
    multiWordTags: List<String> = emptyList(),
    tagRegex: Regex? = null,
): String {
    val effectiveTagRegex = tagRegex ?: buildTagTokenRegex(multiWordTags)
    var normalized = text.trim()
    if (normalized.isEmpty()) {
        return ""
    }

    replacements.forEach { (before, after) ->
        normalized = normalized.replace(before, after)
    }
    if (stripJapaneseChars) {
        normalized = JAPANESE_CHAR_REGEX.replace(normalized, " ")
    }

    var lines = normalized.lines()
        .map(::normalizeInlineWhitespace)
        .filter { it.isNotEmpty() }

        if (lines.size <= 2) {
            var merged = normalizeInlineWhitespace(lines.joinToString(" "))
            val marker = sectionMarkerRegex.find(merged)
            if (
                marker != null &&
                marker.range.first > 0 &&
                !marker.value.startsWith("#") &&
                !DETAIL_PREFIX_PATTERN.containsMatchIn(merged)
            ) {
                merged = merged.substring(marker.range.first)
            }

        merged = protectMultiWordTags(merged, multiWordTags)
        sectionBreakOnceLabels.forEach { label ->
            merged = insertSectionBreakOnce(merged, label)
        }
        lineBreakPatterns.forEach { (pattern, replacement) ->
            merged = merged.replace(pattern, replacement)
        }
        merged = restoreMultiWordTags(merged)

        lines = merged.lines()
            .map(::normalizeInlineWhitespace)
            .filter { it.isNotEmpty() }
    }

    val expanded = lines

    val markerIndex = expanded.indexOfFirst { splitSectionLabel(it) != null }
    val trimmed = if (markerIndex >= 0) expanded.drop(markerIndex) else expanded
    val filtered = trimmed.filterNot { isNoiseMetadataLine(it, metadataTokens) }

    val result = mutableListOf<String>()
    for (line in filtered) {
        if (isStandaloneTagMetadataLine(line, effectiveTagRegex)) {
            if (result.lastOrNull() != tagLabel) {
                result += tagLabel
            }
            result += normalizeTagLine(line, effectiveTagRegex)
            continue
        }

        if (line == tagLabel && result.lastOrNull() == tagLabel) {
            continue
        }
        if (line in SECTION_LABELS && result.lastOrNull() == line) {
            continue
        }
        result += line
    }

    return result.joinToString("\n")
}

private fun insertSectionBreakOnce(text: String, label: String): String {
    val pattern = Regex("\\s*${Regex.escape(label)}\\s*")
    return pattern.replaceFirst(text, "\n$label\n")
}

private fun normalizeInlineWhitespace(text: String): String {
    return text.replace(Regex("\\s+"), " ").trim()
}

private fun isStandaloneTagMetadataLine(line: String, tagRegex: Regex): Boolean {
    val normalized = normalizeInlineWhitespace(line)
    if (!normalized.startsWith("#")) {
        return false
    }

    val tags = tagRegex.findAll(normalized).map { it.value }.toList()
    if (tags.isEmpty()) {
        return false
    }

    var remainder = normalized
    for (tag in tags) {
        remainder = remainder.replace(tag, " ")
    }
    return normalizeInlineWhitespace(remainder).isEmpty()
}

private fun expandTagLinesHelper(lines: List<String>, tagLabel: String): List<String> {
    val result = mutableListOf<String>()
    for (line in lines) {
        if (!line.contains('#')) {
            result += line
            continue
        }
        val jaMatch = JA_TAG_OBJECT_SPLIT_REGEX.matchEntire(line)
        if (jaMatch != null) {
            result += tagLabel
            result += normalizeInlineWhitespace(jaMatch.groupValues[1])
            val tail = normalizeInlineWhitespace(jaMatch.groupValues[2])
            if (tail.isNotEmpty()) {
                if (tail.contains('#')) {
                    result += expandTagLinesHelper(listOf(tail), tagLabel)
                } else {
                    result += tail
                }
            }
        } else {
            result += line
        }
    }
    return result
}

private fun normalizeTagLine(line: String, tagRegex: Regex): String {
    val tags = tagRegex.findAll(line).map { it.value }.toList()
    if (tags.isEmpty()) {
        return normalizeInlineWhitespace(line)
    }

    var tail = line
    for (tag in tags) {
        tail = tail.replace(tag, " ")
    }
    val remainder = normalizeInlineWhitespace(tail)
    return if (remainder.isEmpty()) {
        tags.joinToString(" ")
    } else {
        "${tags.joinToString(" ")} $remainder"
    }
}

private fun isNoiseMetadataLine(line: String, metadataTokens: Set<String>): Boolean {
    val normalized = normalizeInlineWhitespace(line)
    if (normalized.isEmpty()) {
        return true
    }

    val lowered = normalized.lowercase(Locale.ROOT)
    if (SCALAR_METADATA_PATTERN.matches(lowered)) {
        return true
    }

    val tokens = lowered.split(" ").filter { it.isNotBlank() }
    if (tokens.isNotEmpty() && tokens.all { token ->
            token in metadataTokens || DIGIT_TOKEN_PATTERN.matches(token)
        }) {
        return true
    }

    return false
}

@Composable
private fun ThemeModeItem(
    mode: AppThemeMode,
    selectedMode: AppThemeMode,
    onSelected: (AppThemeMode) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onSelected(mode) }
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(
            selected = selectedMode == mode,
            onClick = { onSelected(mode) },
        )
        Text(
            text = mode.label,
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}

@Composable
private fun PreferredLanguageItem(
    language: PreferredLanguage,
    selectedLanguage: PreferredLanguage,
    onSelected: (PreferredLanguage) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onSelected(language) }
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(
            selected = selectedLanguage == language,
            onClick = { onSelected(language) },
        )
        Text(
            text = language.label,
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}

@Composable
private fun scaledHeightDp(ratio: Float, minPx: Int, maxPx: Int): Dp {
    val config = androidx.compose.ui.platform.LocalConfiguration.current
    val scaled = (config.screenHeightDp * ratio).roundToInt()
    return scaled.coerceIn(minPx, maxPx).dp
}

private fun snappedListHeightDp(rawHeight: Dp): Dp {
    val panelVerticalPadding = 20
    val rowHeight = 38
    val rowSpacing = 4
    val rowStride = rowHeight + rowSpacing

    val raw = rawHeight.value.roundToInt()
    val available = (raw - panelVerticalPadding + rowSpacing).coerceAtLeast(rowStride)
    val fullRows = (available / rowStride).coerceAtLeast(1)
    val snappedInner = fullRows * rowStride - rowSpacing
    return (snappedInner + panelVerticalPadding).dp
}

private fun buildTagTokenRegex(multiWordTags: List<String>): Regex {
    val parts = mutableListOf<String>()
    for (tag in multiWordTags) {
        parts += Regex.escape(tag)
    }
    for (pat in KO_MW_TAG_PATTERNS) {
        parts += pat.pattern
    }
    parts += "#[^\\s#]+"
    return Regex(parts.joinToString("|"))
}

private fun protectMultiWordTags(text: String, tags: List<String>): String {
    var result = text
    for (tag in tags) {
        result = result.replace(tag, tag.replace(" ", MW_PLACEHOLDER))
    }
    for (pat in KO_MW_TAG_PATTERNS) {
        result = pat.replace(result) { match ->
            match.value.replace(" ", MW_PLACEHOLDER)
        }
    }
    return result
}

private fun restoreMultiWordTags(text: String): String {
    return text.replace(MW_PLACEHOLDER, " ")
}

private fun openExternalUrl(context: android.content.Context, url: String) {
    val uri = runCatching { Uri.parse(url) }.getOrNull() ?: return
    val intent = Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching {
        context.startActivity(intent)
    }
}

/**
 * Lets LazyColumn consume drag/fling first, then swallows leftover delta so
 * the parent Column( verticalScroll ) does not move from inner-list gestures.
 */
private val ConsumeScrollNestedScrollConnection = object : NestedScrollConnection {
    override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset = Offset.Zero

    override fun onPostScroll(consumed: Offset, available: Offset, source: NestedScrollSource): Offset = available

    override suspend fun onPreFling(available: Velocity): Velocity = Velocity.Zero

    override suspend fun onPostFling(consumed: Velocity, available: Velocity): Velocity = available
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun RarityPickerBottomSheet(
    card: DeckCardCandidate,
    currentRarity: String,
    onSelect: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = androidx.compose.material3.rememberModalBottomSheetState(skipPartiallyExpanded = true)
    androidx.compose.material3.ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                card.nameKo.ifBlank { card.nameJa },
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "레어리티 선택",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.outline,
            )
            androidx.compose.foundation.lazy.LazyRow(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(card.selectableIllustrations) { option ->
                    val isSelected = option.rarity == currentRarity
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier
                            .width(90.dp)
                            .clickable { onSelect(option.rarity) },
                    ) {
                        val imgUrl = if (option.imageUrl.isNotEmpty()) option.imageUrl else card.imageUrl
                        val hasImageUrl = imgUrl.trim().isNotEmpty()
                        if (hasImageUrl) {
                            AsyncImage(
                                model = imgUrl,
                                contentDescription = option.rarity,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .aspectRatio(400f / 558f)
                                    .clip(RoundedCornerShape(6.dp))
                                    .border(
                                        width = if (isSelected) 3.dp else 0.dp,
                                        color = if (isSelected) MaterialTheme.colorScheme.primary else androidx.compose.ui.graphics.Color.Transparent,
                                        shape = RoundedCornerShape(6.dp),
                                    ),
                                contentScale = ContentScale.Crop,
                            )
                        } else {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .aspectRatio(400f / 558f)
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(MaterialTheme.colorScheme.surfaceVariant)
                                    .border(
                                        width = if (isSelected) 3.dp else 0.dp,
                                        color = if (isSelected) MaterialTheme.colorScheme.primary else androidx.compose.ui.graphics.Color.Transparent,
                                        shape = RoundedCornerShape(6.dp),
                                    ),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Image,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.outline,
                                )
                            }
                        }
                        Text(
                            option.rarity,
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                        )
                        if (isSelected) {
                            Icon(
                                Icons.Default.CheckCircle,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(16.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}

private fun Modifier.clearFocusOnTap(focusManager: FocusManager): Modifier {
    return pointerInput(focusManager) {
        awaitEachGesture {
            awaitFirstDown(
                requireUnconsumed = false,
                pass = PointerEventPass.Final,
            )
            focusManager.clearFocus(force = true)
            waitForUpOrCancellation(pass = PointerEventPass.Final)
        }
    }
}

package com.smalltyrant.hocgh.ui

import android.content.res.Configuration
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BrokenImage
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Save
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
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.input.ImeAction
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.smalltyrant.hocgh.model.HocgUiState
import com.smalltyrant.hocgh.model.ImageState
import com.smalltyrant.hocgh.model.PrintRow
import com.smalltyrant.hocgh.model.DeckCardCandidate
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import java.util.Locale

private val SECTION_LABELS = listOf(
    "SP 오시 스킬",
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
    "SP 오시 스킬|오시 스킬|콜라보 이펙트|블룸 이펙트|기프트|엑스트라|아츠(?=\\s+[A-Za-z가-힣])|#",
)
private val JA_SECTION_MARKER_REGEX = Regex(
    "SP推しスキル|推しスキル|コラボエフェクト|ブルームエフェクト|ギフト|エクストラ|アーツ(?=\\s+\\S)|カードタイプ|タグ|レアリティ|能力テキスト|バトンタッチ|#",
)
private val TAG_TOKEN_REGEX = Regex("#[^\\s#]+")
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
    Regex("\\s*(?<!SP )오시 스킬\\s*") to "\n오시 스킬\n",
    Regex("\\s*콜라보 이펙트\\s*") to "\n콜라보 이펙트\n",
    Regex("\\s*블룸 이펙트\\s*") to "\n블룸 이펙트\n",
    Regex("\\s*기프트\\s*") to "\n기프트\n",
    Regex("\\s*엑스트라\\s*") to "\n엑스트라\n",
    Regex("\\s*아츠(?=\\s+[A-Za-z가-힣])\\s*") to "\n아츠\n",
    Regex("\\s+#") to "\n#",
)
private val JA_LINE_BREAK_PATTERNS = listOf(
    Regex("\\s*SP推しスキル\\s*") to "\nSP推しスキル\n",
    Regex("\\s*(?<!SP)推しスキル\\s*") to "\n推しスキル\n",
    Regex("\\s*コラボエフェクト\\s*") to "\nコラボエフェクト\n",
    Regex("\\s*ブルームエフェクト\\s*") to "\nブルームエフェクト\n",
    Regex("\\s*ギフト\\s*") to "\nギフト\n",
    Regex("\\s*エクストラ\\s*") to "\nエクストラ\n",
    Regex("\\s*アーツ(?=\\s+\\S)\\s*") to "\nアーツ\n",
    Regex("\\s*カードタイプ\\s*") to "\nカードタイプ\n",
    Regex("\\s*タグ\\s*") to "\nタグ\n",
    Regex("\\s*レアリティ\\s*") to "\nレアリティ\n",
    Regex("\\s*能力テキスト\\s*") to "\n能力テキスト\n",
    Regex("\\s*バトンタッチ\\s*") to "\nバトンタッチ\n",
    Regex("(?:^|\\s)色(?=\\s+\\S)") to "\n色\n",
    Regex("\\s+#") to "\n#",
)

private val DETAIL_PREFIX_PATTERN = Regex(
    pattern = """^(?:.+?)\s+(?:서포트|サポート)\s*[/／]\s*(?:아이템|스태프|이벤트|이벤타|툴|アイテム|スタッフ|イベント|ツール)\s+""",
)

private val INLINE_TAG_PATTERN = Regex(pattern = """#[\p{L}\p{N}_]+""")

private enum class DetailTextLanguage {
    KOREAN,
    JAPANESE,
}

private data class DeckEntryUi(
    val card: DeckCardCandidate,
    var qty: Int,
    val maxPerCard: Int,
)

private data class DeckUi(
    val title: String,
    val entries: List<DeckEntryUi>,
)

private fun isOshi(card: DeckCardCandidate): Boolean = card.cardType.contains("오시") || card.cardType.contains("推し")
private fun isYell(card: DeckCardCandidate): Boolean {
    val c = card.color.lowercase()
    val t = card.cardType.lowercase()
    return c.contains("옐") || c.contains("yell") || c.contains("エール") || t.contains("yell")
}
private fun maxPerCard(card: DeckCardCandidate): Int {
    if (isOshi(card)) return 1
    val src = card.koText
    if (src.contains("리미티드") || src.contains("limited", ignoreCase = true)) return 1
    val rx = listOf(Regex("(\\d+)장만"), Regex("최대\\s*(\\d+)장"), Regex("(\\d+)장까지"))
    for (r in rx) {
        val m = r.find(src) ?: continue
        val n = m.groupValues.getOrNull(1)?.toIntOrNull() ?: continue
        return n.coerceAtLeast(1)
    }
    return 4
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

    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = androidx.compose.runtime.rememberCoroutineScope()

    var showDeckList by remember { mutableStateOf(false) }
    var showDeckEditor by remember { mutableStateOf(false) }
    var showCardPicker by remember { mutableStateOf(false) }
    var deckTitle by remember { mutableStateOf("새 덱") }
    var deckSearchQuery by remember { mutableStateOf("") }
    var deckCandidates by remember { mutableStateOf<List<DeckCardCandidate>>(emptyList()) }
    val deckDraft = remember { mutableStateListOf<DeckEntryUi>() }
    val savedDecks = remember { mutableStateListOf<DeckUi>() }

    LaunchedEffect(Unit) {
        viewModel.toastEvents.collect { message ->
            snackbarHostState.showSnackbar(message)
        }
    }

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
                    onAdd = {
                        deckTitle = "새 덱"
                        deckDraft.clear()
                        showDeckList = false
                        showDeckEditor = true
                    },
                    onEdit = { deck ->
                        deckTitle = deck.title
                        deckDraft.clear()
                        deckDraft.addAll(deck.entries.map { it.copy() })
                        showDeckList = false
                        showDeckEditor = true
                    },
                )
            } else if (showDeckEditor) {
                DeckEditorScreen(
                    innerPadding = innerPadding,
                    title = deckTitle,
                    entries = deckDraft,
                    onTitleChange = { deckTitle = it },
                    onCancel = { showDeckEditor = false },
                    onSave = {
                        val snapshot = deckDraft.groupBy { it.card.printId }.values.map { g ->
                            val first = g.first()
                            DeckEntryUi(first.card, g.sumOf { it.qty }, first.maxPerCard)
                        }
                        savedDecks.removeAll { it.title == deckTitle }
                        savedDecks.add(DeckUi(deckTitle.ifBlank { "덱" }, snapshot))
                        showDeckEditor = false
                        showDeckList = true
                    },
                    onOpenPicker = {
                        showCardPicker = true
                        scope.launch { deckCandidates = viewModel.searchDeckCards(deckSearchQuery) }
                    },
                    onIncrease = { entry ->
                        val oshi = deckDraft.filter { isOshi(it.card) }.sumOf { it.qty }
                        val yell = deckDraft.filter { isYell(it.card) }.sumOf { it.qty }
                        val main = deckDraft.filter { !isOshi(it.card) && !isYell(it.card) }.sumOf { it.qty }
                        if (entry.qty < entry.maxPerCard && (!isOshi(entry.card) || oshi < 1) && (!isYell(entry.card) || yell < 20) && (isOshi(entry.card) || isYell(entry.card) || main < 50)) {
                            entry.qty += 1
                        }
                    },
                    onDecrease = { entry ->
                        entry.qty -= 1
                        if (entry.qty <= 0) deckDraft.remove(entry)
                    },
                )

                if (showCardPicker) {
                    AlertDialog(
                        onDismissRequest = { showCardPicker = false },
                        confirmButton = { TextButton(onClick = { showCardPicker = false }) { Text("닫기") } },
                        title = { Text("카드 선택") },
                        text = {
                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                OutlinedTextField(
                                    value = deckSearchQuery,
                                    onValueChange = {
                                        deckSearchQuery = it
                                        scope.launch { deckCandidates = viewModel.searchDeckCards(deckSearchQuery) }
                                    },
                                    label = { Text("카드 검색") },
                                    singleLine = true,
                                )
                                LazyColumn(modifier = Modifier.height(320.dp)) {
                                    items(deckCandidates, key = { it.printId }) { card ->
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable {
                                                    val found = deckDraft.firstOrNull { it.card.printId == card.printId }
                                                    val oshi = deckDraft.filter { isOshi(it.card) }.sumOf { it.qty }
                                                    val yell = deckDraft.filter { isYell(it.card) }.sumOf { it.qty }
                                                    val main = deckDraft.filter { !isOshi(it.card) && !isYell(it.card) }.sumOf { it.qty }
                                                    if (found == null) {
                                                        if ((!isOshi(card) || oshi < 1) && (!isYell(card) || yell < 20) && (isOshi(card) || isYell(card) || main < 50)) {
                                                            deckDraft.add(DeckEntryUi(card = card, qty = 1, maxPerCard = maxPerCard(card)))
                                                        }
                                                    } else if (found.qty < found.maxPerCard) {
                                                        if ((!isOshi(card) || oshi < 1) && (!isYell(card) || yell < 20) && (isOshi(card) || isYell(card) || main < 50)) {
                                                            found.qty += 1
                                                        }
                                                    }
                                                }
                                                .padding(vertical = 4.dp),
                                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        ) {
                                            AsyncImage(model = card.imageUrl, contentDescription = null, modifier = Modifier.size(width = 44.dp, height = 60.dp))
                                            Text("${card.cardNumber} | ${card.nameKo.ifBlank { card.nameJa }}", maxLines = 1, overflow = TextOverflow.Ellipsis)
                                        }
                                    }
                                }
                            }
                        },
                    )
                }
            } else if (isMobileLayout) {
                MobileLayout(
                    state = state,
                    innerPadding = innerPadding,
                    onSearchQueryChanged = viewModel::onSearchQueryChanged,
                    onOpenMenu = { scope.launch { drawerState.open() } },
                    onDismissKeyboard = { focusManager.clearFocus() },
                    onSelectPrint = viewModel::onSelectPrint,
                    onToggleImagePanel = viewModel::onToggleImagePanel,
                    preferredLanguage = preferredLanguage,
                )
            } else {
                DesktopLayout(
                    state = state,
                    innerPadding = innerPadding,
                    onSearchQueryChanged = viewModel::onSearchQueryChanged,
                    onDismissKeyboard = { focusManager.clearFocus() },
                    onOpenMenu = { scope.launch { drawerState.open() } },
                    showMenuButton = forceDesktopLandscape,
                    keepSearchBarTop = forceDesktopLandscape,
                    twoPaneLandscape = forceDesktopLandscape,
                    onSelectPrint = viewModel::onSelectPrint,
                    preferredLanguage = preferredLanguage,
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
    onAdd: () -> Unit,
    onEdit: (DeckUi) -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(innerPadding).padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onBack) { Text("취소") }
            Text("덱 리스트", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            IconButton(onClick = onAdd) { Icon(Icons.Default.Add, contentDescription = "추가") }
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(decks.indices.toList(), key = { it }) { idx ->
                val deck = decks[idx]
                Column(modifier = Modifier.fillMaxWidth().clickable { onEdit(deck) }.border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(10.dp)).padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(deck.title, fontWeight = FontWeight.Bold)
                    deck.entries.take(5).forEach { entry ->
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            AsyncImage(model = entry.card.imageUrl, contentDescription = null, modifier = Modifier.size(width = 42.dp, height = 58.dp))
                            Text("x ${entry.qty}")
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
    onTitleChange: (String) -> Unit,
    onCancel: () -> Unit,
    onSave: () -> Unit,
    onOpenPicker: () -> Unit,
    onIncrease: (DeckEntryUi) -> Unit,
    onDecrease: (DeckEntryUi) -> Unit,
) {
    val oshi = entries.filter { isOshi(it.card) }.sumOf { it.qty }
    val yell = entries.filter { isYell(it.card) }.sumOf { it.qty }
    val main = entries.filter { !isOshi(it.card) && !isYell(it.card) }.sumOf { it.qty }
    Column(modifier = Modifier.fillMaxSize().padding(innerPadding).padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onCancel) { Text("취소") }
            OutlinedTextField(value = title, onValueChange = onTitleChange, singleLine = true, modifier = Modifier.weight(1f), label = { Text("덱 이름") })
            TextButton(onClick = onSave) { Text("저장") }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("오시 $oshi/1")
            Text("옐 $yell/20")
            Text("기타 $main/50")
            IconButton(onClick = onOpenPicker) { Icon(Icons.Default.Add, contentDescription = "카드 추가") }
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items(entries, key = { it.card.printId }) { entry ->
                Row(modifier = Modifier.fillMaxWidth().border(BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(10.dp)).padding(8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AsyncImage(model = entry.card.imageUrl, contentDescription = null, modifier = Modifier.size(width = 50.dp, height = 70.dp))
                    Text("${entry.card.cardNumber} | ${entry.card.nameKo.ifBlank { entry.card.nameJa }} x ${entry.qty}", modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    IconButton(onClick = { onDecrease(entry) }) { Icon(Icons.Default.Close, contentDescription = "감소") }
                    IconButton(onClick = { onIncrease(entry) }) { Icon(Icons.Default.Add, contentDescription = "증가") }
                }
            }
        }
    }
}

@Composable
private fun MobileLayout(
    state: HocgUiState,
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    onSearchQueryChanged: (String) -> Unit,
    onOpenMenu: () -> Unit,
    onDismissKeyboard: () -> Unit,
    onSelectPrint: (Long) -> Unit,
    onToggleImagePanel: () -> Unit,
    preferredLanguage: PreferredLanguage,
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
            Panel(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(imageHeight),
            ) {
                ImagePanel(state.imageState)
            }
        }

        Text("효과", style = MaterialTheme.typography.titleSmall)
        Panel(modifier = Modifier.fillMaxWidth()) {
            DetailPanel(
                koText = state.detailKoText,
                jaText = state.detailJaText,
                preferredLanguage = preferredLanguage,
                scrollable = false,
            )
        }
    }
}

@Composable
private fun DesktopLayout(
    state: HocgUiState,
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    onSearchQueryChanged: (String) -> Unit,
    onDismissKeyboard: () -> Unit,
    onOpenMenu: () -> Unit,
    showMenuButton: Boolean,
    keepSearchBarTop: Boolean,
    twoPaneLandscape: Boolean,
    onSelectPrint: (Long) -> Unit,
    preferredLanguage: PreferredLanguage,
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
                        ResultsList(state = state, onSelect = onSelectPrint, preferredLanguage = preferredLanguage)
                    }
                }

                VerticalDivider(modifier = Modifier.width(1.dp))

                Column(
                    modifier = Modifier.weight(7f).fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Column(modifier = Modifier.weight(6f).fillMaxWidth()) {
                        Text("이미지", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                        Panel(modifier = Modifier.fillMaxSize()) {
                            ImagePanel(state.imageState)
                        }
                    }

                    Column(modifier = Modifier.weight(4f).fillMaxWidth()) {
                        Text("효과", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                        Panel(modifier = Modifier.fillMaxSize()) {
                            DetailPanel(
                                koText = state.detailKoText,
                                jaText = state.detailJaText,
                                preferredLanguage = preferredLanguage,
                                scrollable = true,
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
                        ResultsList(state = state, onSelect = onSelectPrint, preferredLanguage = preferredLanguage)
                    }
                }

                VerticalDivider(modifier = Modifier.width(1.dp))

                Column(modifier = Modifier.weight(6f)) {
                    Text("이미지", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                    Panel(modifier = Modifier.fillMaxSize()) {
                        ImagePanel(state.imageState)
                    }
                }

                VerticalDivider(modifier = Modifier.width(1.dp))

                Column(modifier = Modifier.weight(4f)) {
                    Text("효과", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                    Panel(modifier = Modifier.fillMaxSize()) {
                        DetailPanel(
                            koText = state.detailKoText,
                            jaText = state.detailJaText,
                            preferredLanguage = preferredLanguage,
                            scrollable = true,
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
        modifier = Modifier.fillMaxSize(),
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
        PreferredLanguage.KOREAN -> row.nameKo.ifBlank { row.nameJa }
        PreferredLanguage.JAPANESE -> row.nameJa.ifBlank { row.nameKo }
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
    preferredLanguage: PreferredLanguage,
    scrollable: Boolean,
) {
    val koLines = remember(koText) { splitDetailLines(koText, language = DetailTextLanguage.KOREAN) }
    val jaLines = remember(jaText) { splitDetailLines(jaText, language = DetailTextLanguage.JAPANESE) }

    val hasKo = koLines.isNotEmpty()
    val hasJa = jaLines.isNotEmpty()
    val showJaFirst = !hasKo
    val expandBoth = hasKo && hasJa && koLines.size <= 2 && jaLines.size >= 4

    var koExpanded by rememberSaveable(koText, jaText, preferredLanguage) {
        mutableStateOf(hasKo && (expandBoth || !hasJa || preferredLanguage == PreferredLanguage.KOREAN))
    }
    var jaExpanded by rememberSaveable(koText, jaText, preferredLanguage) {
        mutableStateOf(hasJa && (expandBoth || !hasKo || preferredLanguage == PreferredLanguage.JAPANESE))
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
            Text("(본문 없음)", style = MaterialTheme.typography.bodyMedium)
            return@Column
        }

        if (hasKo && hasJa) {
            ExpandableDetailSection(
                title = "한국어",
                lines = koLines,
                expanded = koExpanded,
                onToggle = { koExpanded = !koExpanded },
            )
            ExpandableDetailSection(
                title = "일본어",
                lines = jaLines,
                expanded = jaExpanded,
                onToggle = { jaExpanded = !jaExpanded },
            )
            return@Column
        }

        val singleTitle = if (hasKo) "한국어" else "일본어"
        val singleLines = if (showJaFirst) jaLines else koLines
        SectionChip(singleTitle)
        for (line in singleLines) {
            DetailLine(line)
        }
    }
}

@Composable
private fun ExpandableDetailSection(
    title: String,
    lines: List<String>,
    expanded: Boolean,
    onToggle: () -> Unit,
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
        DetailLine(line)
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
private fun DetailLine(line: String) {
    splitSectionLabel(line)?.let { (label, rest) ->
        if (rest.isBlank()) {
            SectionChip(label)
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                SectionChip(label)
                Text(buildHighlightedTagText(rest, MaterialTheme.colorScheme.primary), style = MaterialTheme.typography.bodyMedium)
            }
        }
        return
    }

    Text(buildHighlightedTagText(line, MaterialTheme.colorScheme.primary), style = MaterialTheme.typography.bodyMedium)
}

private fun buildHighlightedTagText(text: String, highlightColor: androidx.compose.ui.graphics.Color) = buildAnnotatedString {
    var cursor = 0
    for (match in INLINE_TAG_PATTERN.findAll(text)) {
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
        val rest = trimmed.removePrefix(label).trim()
        if (rest.isEmpty()) {
            return label to ""
        }
        if (separators.any { rest.startsWith(it) }) {
            return label to rest
        }
    }
    return null
}

private fun sanitizeDetailLine(line: String): String {
    val trimmed = line.trim()
    return DETAIL_PREFIX_PATTERN.replace(trimmed, "")
}

private fun mergeBrokenTagLines(lines: List<String>): List<String> {
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

private fun splitDetailLines(text: String, language: DetailTextLanguage): List<String> {
    val payload = when (language) {
        DetailTextLanguage.KOREAN -> prettifyKoDetailText(text)
        DetailTextLanguage.JAPANESE -> prettifyJaDetailText(text)
    }
    val lines = payload.lines()
        .map(::sanitizeDetailLine)
        .map(::normalizeInlineWhitespace)
        .filter { it.isNotEmpty() }

    return mergeBrokenTagLines(lines)
}

private fun prettifyKoDetailText(text: String): String {
    return prettifyDetailText(
        text = text,
        replacements = KO_DETAIL_REPLACEMENTS,
        sectionMarkerRegex = KO_SECTION_MARKER_REGEX,
        lineBreakPatterns = KO_LINE_BREAK_PATTERNS,
        tagLabel = "태그",
        metadataTokens = KO_METADATA_TOKEN_SET,
        stripJapaneseChars = true,
    )
}

private fun prettifyJaDetailText(text: String): String {
    return prettifyDetailText(
        text = text,
        replacements = JA_DETAIL_REPLACEMENTS,
        sectionMarkerRegex = JA_SECTION_MARKER_REGEX,
        lineBreakPatterns = JA_LINE_BREAK_PATTERNS,
        tagLabel = "タグ",
        metadataTokens = JA_METADATA_TOKEN_SET,
    )
}

private fun prettifyDetailText(
    text: String,
    replacements: List<Pair<String, String>>,
    sectionMarkerRegex: Regex,
    lineBreakPatterns: List<Pair<Regex, String>>,
    tagLabel: String,
    metadataTokens: Set<String>,
    stripJapaneseChars: Boolean = false,
): String {
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
        if (marker != null && marker.range.first > 0) {
            merged = merged.substring(marker.range.first)
        }

        lineBreakPatterns.forEach { (pattern, replacement) ->
            merged = merged.replace(pattern, replacement)
        }

        lines = merged.lines()
            .map(::normalizeInlineWhitespace)
            .filter { it.isNotEmpty() }
    }

    val expanded = mutableListOf<String>()
    for (line in lines) {
        val hashIdx = line.indexOf('#')
        if (hashIdx > 0) {
            val prefix = normalizeInlineWhitespace(line.substring(0, hashIdx))
            val tags = normalizeInlineWhitespace(line.substring(hashIdx))
            if (prefix.isNotEmpty()) {
                expanded += prefix
            }
            if (tags.isNotEmpty()) {
                expanded += tags
            }
        } else {
            expanded += line
        }
    }

    val markerIndex = expanded.indexOfFirst { it.startsWith("#") || splitSectionLabel(it) != null }
    val trimmed = if (markerIndex >= 0) expanded.drop(markerIndex) else expanded
    val filtered = trimmed.filterNot { isNoiseMetadataLine(it, metadataTokens) }

    val result = mutableListOf<String>()
    for (line in filtered) {
        if (line.startsWith("#")) {
            if (result.lastOrNull() != tagLabel) {
                result += tagLabel
            }
            result += normalizeTagLine(line)
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

private fun normalizeInlineWhitespace(text: String): String {
    return text.replace(Regex("\\s+"), " ").trim()
}

private fun normalizeTagLine(line: String): String {
    val tags = TAG_TOKEN_REGEX.findAll(line).map { it.value }.toList()
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
    if (Regex("^(hp\\s*\\d{2,3}|(1st|2nd)\\s*\\d{2,3})$").matches(lowered)) {
        return true
    }

    val tokens = lowered.split(" ").filter { it.isNotBlank() }
    if (tokens.isNotEmpty() && tokens.all { token ->
            token in metadataTokens || Regex("^\\d{2,3}$").matches(token)
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

private fun Modifier.clearFocusOnTap(focusManager: FocusManager): Modifier {
    return pointerInput(focusManager) {
        awaitEachGesture {
            awaitFirstDown(
                requireUnconsumed = false,
                pass = PointerEventPass.Initial,
            )
            focusManager.clearFocus(force = true)
            waitForUpOrCancellation(pass = PointerEventPass.Initial)
        }
    }
}

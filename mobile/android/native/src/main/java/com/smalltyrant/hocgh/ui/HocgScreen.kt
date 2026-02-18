package com.smalltyrant.hocgh.ui

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
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.focus.FocusManager
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
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
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions

private val SECTION_LABELS = listOf(
    "カードタイプ",
    "タグ",
    "レアリティ",
    "推しスキル",
    "SP推しスキル",
    "アーツ",
    "エクストラ",
    "Bloomレベル",
    "キーワード",
    "LIFE",
    "HP",
)

@Composable
fun HocgScreen(
    viewModel: HocgViewModel = viewModel(),
    themeMode: AppThemeMode,
    onThemeModeChange: (AppThemeMode) -> Unit,
) {
    val state = viewModel.state
    val config = androidx.compose.ui.platform.LocalConfiguration.current
    val isMobileLayout = config.screenWidthDp < 900
    val focusManager = LocalFocusManager.current

    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = androidx.compose.runtime.rememberCoroutineScope()

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
        gesturesEnabled = isMobileLayout,
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
                }
            }
        },
    ) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
        ) { innerPadding ->
            if (isMobileLayout) {
                MobileLayout(
                    state = state,
                    innerPadding = innerPadding,
                    onSearchQueryChanged = viewModel::onSearchQueryChanged,
                    onOpenMenu = { scope.launch { drawerState.open() } },
                    onDismissKeyboard = { focusManager.clearFocus() },
                    onSelectPrint = viewModel::onSelectPrint,
                    onToggleImagePanel = viewModel::onToggleImagePanel,
                )
            } else {
                DesktopLayout(
                    state = state,
                    innerPadding = innerPadding,
                    onSearchQueryChanged = viewModel::onSearchQueryChanged,
                    onDismissKeyboard = { focusManager.clearFocus() },
                    onSelectPrint = viewModel::onSelectPrint,
                )
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
) {
    val listHeight = scaledHeightDp(ratio = 0.30f, minPx = 190, maxPx = 360)
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
            DetailPanel(koText = state.detailKoText, scrollable = false)
        }
    }
}

@Composable
private fun DesktopLayout(
    state: HocgUiState,
    innerPadding: androidx.compose.foundation.layout.PaddingValues,
    onSearchQueryChanged: (String) -> Unit,
    onDismissKeyboard: () -> Unit,
    onSelectPrint: (Long) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(innerPadding)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
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

        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = state.searchQuery,
            onValueChange = onSearchQueryChanged,
            label = { Text("카드번호 / 이름 / 태그 / 한국어 본문 검색") },
            enabled = !state.updateRunning,
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { onDismissKeyboard() }),
        )

        UpdateStatusBlock(state)
        HorizontalDivider()

        Row(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.weight(3f)) {
                Text("목록", modifier = Modifier.padding(start = 10.dp, top = 4.dp), style = MaterialTheme.typography.titleSmall)
                Panel(modifier = Modifier.fillMaxSize()) {
                    ResultsList(state = state, onSelect = onSelectPrint)
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
                    DetailPanel(koText = state.detailKoText, scrollable = true)
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
            )
        }
    }
}

@Composable
private fun ResultItem(row: PrintRow, selected: Boolean, onClick: () -> Unit) {
    val displayName = row.nameKo.ifBlank {
        row.nameJa.ifBlank { "(이름 없음)" }
    }
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
private fun DetailPanel(koText: String, scrollable: Boolean) {
    val lines = remember(koText) {
        koText.lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
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
        if (lines.isEmpty()) {
            Text("(한국어 본문 없음)", style = MaterialTheme.typography.bodyMedium)
            return@Column
        }

        SectionChip("한국어")
        for (line in lines) {
            DetailLine(line)
        }
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
    if (SECTION_LABELS.contains(line)) {
        SectionChip(line)
        return
    }

    for (label in SECTION_LABELS) {
        val prefix = "$label "
        if (line.startsWith(prefix)) {
            Text(
                text = buildAnnotatedString {
                    pushStyle(SpanStyle(fontWeight = FontWeight.Bold))
                    append(label)
                    pop()
                    append(line.removePrefix(label))
                },
                style = MaterialTheme.typography.bodyMedium,
            )
            return
        }
    }

    Text(line, style = MaterialTheme.typography.bodyMedium)
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
private fun scaledHeightDp(ratio: Float, minPx: Int, maxPx: Int): Dp {
    val config = androidx.compose.ui.platform.LocalConfiguration.current
    val scaled = (config.screenHeightDp * ratio).roundToInt()
    return scaled.coerceIn(minPx, maxPx).dp
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

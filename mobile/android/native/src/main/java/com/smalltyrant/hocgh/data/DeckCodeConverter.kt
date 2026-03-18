package com.smalltyrant.hocgh.data

import android.util.Base64
import com.smalltyrant.hocgh.model.DeckCardCandidate
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

// ──────────────────────────────────────────────
// HoloDuel 덱 코드 포맷
// O:<oshiID>|D:<id>x<n>,...|C:<id>x<n>,...
// → Base64 (Android-standard)
// ──────────────────────────────────────────────

object DeckCodeConverter {

    // ─── 카드 분류 helpers ───

    fun isOshi(card: DeckCardCandidate): Boolean =
        card.cardType.contains("오시") || card.cardType.contains("推し")

    fun isYell(card: DeckCardCandidate): Boolean {
        if (card.cardNumber.uppercase().startsWith("HY")) return true
        val c = card.color.lowercase()
        val t = card.cardType.lowercase()
        return c.contains("옐") || c.contains("yell") || c.contains("エール") ||
            t.contains("yell") || t.contains("エール")
    }

    // ─── HoloDuel Export ───

    data class HoloDuelEntry(val cardNumber: String, val qty: Int)

    /**
     * entries: (cardNumber, qty, card) 목록 → HoloDuel Base64 코드
     * 오시 카드가 없으면 null 반환
     */
    fun exportHoloDuel(entries: List<Triple<String, Int, DeckCardCandidate>>): String? {
        var oshiId: String? = null
        val deck = mutableListOf<HoloDuelEntry>()
        val cheer = mutableListOf<HoloDuelEntry>()

        for ((cn, qty, card) in entries) {
            when {
                isOshi(card) -> oshiId = cn
                isYell(card) -> cheer += HoloDuelEntry(cn, qty)
                else         -> deck  += HoloDuelEntry(cn, qty)
            }
        }
        val oshi = oshiId ?: return null

        val deckPart  = deck.joinToString(",")  { "${it.cardNumber}x${it.qty}" }
        val cheerPart = cheer.joinToString(",") { "${it.cardNumber}x${it.qty}" }
        val raw = "O:$oshi|D:$deckPart|C:$cheerPart"
        return Base64.encodeToString(raw.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
    }

    // ─── HoloDuel Import ───

    data class HoloDuelDeck(
        val oshiCardNumber: String,
        val deckEntries: List<HoloDuelEntry>,
        val cheerEntries: List<HoloDuelEntry>,
    )

    fun importHoloDuel(code: String): HoloDuelDeck? {
        val trimmed = code.trim()
        val raw = runCatching {
            Base64.decode(trimmed, Base64.DEFAULT).toString(Charsets.UTF_8)
        }.getOrNull() ?: return null

        val parts = raw.split("|")
        if (parts.size != 3) return null

        val oshiPart  = parts.firstOrNull { it.startsWith("O:") } ?: return null
        val deckPart  = parts.firstOrNull { it.startsWith("D:") } ?: return null
        val cheerPart = parts.firstOrNull { it.startsWith("C:") } ?: return null

        val oshi = oshiPart.removePrefix("O:").trim()
        if (oshi.isEmpty()) return null

        fun parseEntries(str: String): List<HoloDuelEntry>? {
            val body = str.removePrefix(str.take(2))   // drop "D:" or "C:"
            if (body.isEmpty()) return emptyList()
            return body.split(",").map { token ->
                val p = token.split("x")
                if (p.size != 2) return null
                val qty = p[1].toIntOrNull()?.takeIf { it > 0 } ?: return null
                HoloDuelEntry(p[0], qty)
            }
        }

        val deck  = parseEntries(deckPart)  ?: return null
        val cheer = parseEntries(cheerPart) ?: return null
        return HoloDuelDeck(oshi, deck, cheer)
    }

    // ─── holoDelta Export / Import ───

    data class HoloDeltaEntry(val cardNumber: String, val qty: Int, val artIndex: Int)
    data class HoloDeltaDeck(
        val deckName: String?,
        val oshiCardNumber: String,
        val oshiArtIndex: Int,
        val deckEntries: List<HoloDeltaEntry>,
        val cheerEntries: List<HoloDeltaEntry>,
    )

    fun exportHoloDelta(entries: List<Triple<String, Int, DeckCardCandidate>>, title: String): String? {
        var oshi: JSONArray? = null
        val deck = JSONArray()
        val cheer = JSONArray()

        for ((cn, qty, card) in entries) {
            val artIndex = deltaArtIndex(card)
            val row = JSONArray().apply {
                put(cn)
                put(qty)
                put(artIndex)
            }
            when {
                isOshi(card) -> oshi = JSONArray().apply { put(cn); put(artIndex) }
                isYell(card) -> cheer.put(row)
                else -> deck.put(row)
            }
        }
        val oshiRow = oshi ?: return null

        return JSONObject().apply {
            put("deckName", title)
            put("oshi", oshiRow)
            put("deck", deck)
            put("cheerDeck", cheer)
        }.toString()
    }

    fun importHoloDelta(code: String): HoloDeltaDeck? {
        val trimmed = code.trim()
        if (trimmed.isEmpty()) return null

        val json = runCatching {
            if (trimmed.startsWith("{")) {
                JSONObject(trimmed)
            } else {
                val raw = decodeBase64UrlSafe(trimmed) ?: return null
                JSONObject(String(raw, StandardCharsets.UTF_8))
            }
        }.getOrNull() ?: return null

        val oshi = json.optJSONArray("oshi") ?: return null
        val oshiCardNumber = oshi.optString(0).takeIf { it.isNotEmpty() } ?: return null
        val oshiArtIndex = oshi.optInt(1, Int.MIN_VALUE).takeIf { it != Int.MIN_VALUE } ?: return null

        fun parseList(key: String): List<HoloDeltaEntry>? {
            val arr = json.optJSONArray(key) ?: return emptyList()
            val result = mutableListOf<HoloDeltaEntry>()
            for (i in 0 until arr.length()) {
                val row = arr.optJSONArray(i) ?: return null
                val cardNumber = row.optString(0).takeIf { it.isNotEmpty() } ?: return null
                val qty = row.optInt(1, 0)
                if (qty <= 0) return null
                val artIndex = row.optInt(2, Int.MIN_VALUE).takeIf { it != Int.MIN_VALUE } ?: return null
                result += HoloDeltaEntry(cardNumber, qty, artIndex)
            }
            return result
        }

        val deck = parseList("deck") ?: return null
        val cheer = parseList("cheerDeck") ?: return null
        val deckName = json.optString("deckName", "").trim().ifEmpty { null }

        return HoloDeltaDeck(
            deckName = deckName,
            oshiCardNumber = oshiCardNumber,
            oshiArtIndex = oshiArtIndex,
            deckEntries = deck,
            cheerEntries = cheer,
        )
    }

    // ─── Bushiroad (DeckLog) ───

    data class BushiCard(val cardNumber: String, val num: Int, val manageId: String)
    data class BushiDeck(
        val deckId: String,
        val title: String,
        val pList: List<BushiCard>,
        val list: List<BushiCard>,
        val subList: List<BushiCard>,
    )

    /** DeckLog 코드 또는 URL → BushiDeck  (IO 디스패처에서 실행) */
    suspend fun fetchBushiDeck(codeOrURL: String): BushiDeck = withContext(Dispatchers.IO) {
        val normalizedCode = normalizeBushiCode(codeOrURL)
        require(normalizedCode.isNotEmpty() && normalizedCode.all { it.isLetterOrDigit() }) {
            "올바르지 않은 부시나비 코드입니다."
        }

        val proxyBaseUrl = "https://hocg-deck-convert-api.onrender.com"
        val apiUrl = URL("$proxyBaseUrl/view-deck")
        val conn = apiUrl.openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36")
        conn.connectTimeout = 15000
        conn.readTimeout    = 20000

        val body = JSONObject().apply {
            put("game_title_id", 9)
            put("code", normalizedCode)
        }.toString()
        OutputStreamWriter(conn.outputStream).use { it.write(body) }

        val text = conn.inputStream.bufferedReader().readText()
        conn.disconnect()
        parseBushiResponse(text, normalizedCode)
    }

    /** 현재 덱 → DeckLog 업로드 → URL 반환  (IO 디스패처에서 실행) */
    suspend fun publishBushiDeck(
        entries: List<Triple<String, Int, DeckCardCandidate>>,
        title: String,
        manageIdLookup: (Long) -> Int?,
    ): String = withContext(Dispatchers.IO) {

        val pList   = JSONArray()
        val mainList = JSONArray()
        val subList = JSONArray()

        for ((cn, qty, card) in entries) {
            val mid = manageIdLookup(card.printId)?.toString() ?: ""
            val item = JSONObject().apply {
                put("card_number", cn)
                put("num", qty)
                put("manage_id", mid)
            }
            when {
                isOshi(card) -> pList.put(item)
                isYell(card) -> subList.put(item)
                else         -> mainList.put(item)
            }
        }

        val safeTitle = title.take(25).ifBlank { "덱" }
        val body = JSONObject().apply {
            put("game_title_id", 9)
            put("deck_id", "")
            put("title", safeTitle)
            put("p_list", pList)
            put("list", mainList)
            put("sub_list", subList)
        }.toString()

        val deckLogBaseUrl = "https://decklog.bushiroad.com"
        val proxyBaseUrl = "https://hocg-deck-convert-api.onrender.com"
        val apiUrl  = URL("$proxyBaseUrl/publish-deck")
        val conn = apiUrl.openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36")
        conn.connectTimeout = 15000
        conn.readTimeout    = 20000

        OutputStreamWriter(conn.outputStream).use { it.write(body) }

        val respText = conn.inputStream.bufferedReader().readText()
        conn.disconnect()

        val json = JSONObject(respText)
        val deckId = json.optString("deck_id", "").takeIf { it.isNotEmpty() }
            ?: error("부시나비 업로드 실패: ${respText.take(200)}")

        "$deckLogBaseUrl/view/$deckId"
    }

    // ─── private helpers ───

    fun normalizeBushiCode(rawInput: String): String {
        val trimmed = rawInput.trim()
        if (trimmed.isEmpty()) return ""

        val lower = trimmed.lowercase()
        val extracted = when {
            lower.startsWith("https://decklog-en.bushiroad.com/ja/view/") ->
                trimmed.drop("https://decklog-en.bushiroad.com/ja/view/".length)
            lower.startsWith("https://decklog-en.bushiroad.com/view/") ->
                trimmed.drop("https://decklog-en.bushiroad.com/view/".length)
            lower.startsWith("https://decklog.bushiroad.com/view/") ->
                trimmed.drop("https://decklog.bushiroad.com/view/".length)
            else -> trimmed
        }

        val withoutQuery = extracted.substringBefore('?')
        val withoutHash = withoutQuery.substringBefore('#')
        return withoutHash.trim().trim('/').lowercase()
    }

    private fun decodeBase64UrlSafe(text: String): ByteArray? {
        var fixed = text.replace('-', '+').replace('_', '/')
        val rem = fixed.length % 4
        if (rem != 0) {
            fixed += "=".repeat(4 - rem)
        }
        return runCatching {
            Base64.decode(fixed, Base64.DEFAULT)
        }.getOrNull()
    }

    private fun deltaArtIndex(card: DeckCardCandidate): Int {
        if (card.illustrations.isEmpty()) return 0
        val idx = card.illustrations.indexOfFirst { it.rarity == card.rarity }
        return if (idx >= 0) idx else 0
    }

    private fun parseBushiResponse(text: String, code: String): BushiDeck {
        val json = JSONObject(text)
        require(json.has("deck_id")) { "덱을 찾을 수 없습니다. 코드: $code" }

        fun parseList(key: String): List<BushiCard> {
            val arr = json.optJSONArray(key) ?: return emptyList()
            val result = mutableListOf<BushiCard>()
            for (i in 0 until arr.length()) {
                val item = arr.optJSONObject(i) ?: continue
                val cn  = item.optString("card_number").takeIf { it.isNotEmpty() } ?: continue
                val num = item.optInt("num", 0).takeIf { it > 0 } ?: continue
                val mid = item.optString("manage_id", "")
                result += BushiCard(cn, num, mid)
            }
            return result
        }

        return BushiDeck(
            deckId  = json.optString("deck_id", code),
            title   = json.optString("title", ""),
            pList   = parseList("p_list"),
            list    = parseList("list"),
            subList = parseList("sub_list"),
        )
    }
}

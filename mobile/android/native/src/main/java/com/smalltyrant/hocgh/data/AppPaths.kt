package com.smalltyrant.hocgh.data

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import java.io.File

private const val APP_NAME = "hOCG_H"
private const val DB_FILE_NAME = "hololive_ocg.sqlite"
private const val IMAGE_BASE_URL = "https://hololive-official-cardgame.com"
private val SAFE_CARD_NUMBER_RE = Regex("[^A-Za-z0-9._-]+")
private val ABSOLUTE_URI_RE = Regex("^[A-Za-z][A-Za-z0-9+.-]*:")

class AppPaths(private val context: Context) {
    val rootDir: File = File(context.filesDir, APP_NAME).apply { mkdirs() }
    val dbFile: File = File(rootDir, DB_FILE_NAME)
    val imageDir: File = File(rootDir, "images").apply { mkdirs() }
    val deckDir: File = File(rootDir, "decks").apply { mkdirs() }
    val deckLibraryFile: File = File(deckDir, "deck_library.json")

    fun localImageFile(cardNumber: String, variant: String = ""): File {
        val safe = sanitizeCardNumber(cardNumber)
        val suffix = variant.trim().takeIf { it.isNotEmpty() }?.let { "__${sanitizeCardNumber(it)}" } ?: ""
        return File(imageDir, "$safe$suffix.png")
    }

    fun resolveImageUrl(imageUrl: String): String {
        val input = imageUrl.trim()
        if (input.isEmpty()) {
            return ""
        }
        if (input.startsWith("//")) {
            return "https:${input}"
        }
        if (ABSOLUTE_URI_RE.containsMatchIn(input)) {
            return Uri.parse(input).toString()
        }
        val base = Uri.parse(IMAGE_BASE_URL)
        val fragmentSplit = input.split('#', limit = 2)
        val pathAndQuery = fragmentSplit[0]
        val fragment = fragmentSplit.getOrNull(1)
        val querySplit = pathAndQuery.split('?', limit = 2)
        val relative = querySplit[0].removePrefix("/")
        val query = querySplit.getOrNull(1)

        return base.buildUpon().apply {
            if (relative.isNotEmpty()) {
                appendEncodedPath(relative)
            }
            if (query != null) {
                encodedQuery(query)
            }
            if (fragment != null) {
                encodedFragment(fragment)
            }
        }.build().toString()
    }

    /**
     * Mobile builds intentionally do not bundle hololive_ocg.sqlite.
     * The app creates its private data directory first and downloads the DB
     * from the GitHub DB release on first launch/update.
     */
    fun copyBundledDbIfMissing(): Boolean = false

    /** No bundled DB fallback exists; users recover by downloading the DB again. */
    fun restoreBundledDb(): Boolean = false

    fun hasNetworkConnection(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return true
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun sanitizeCardNumber(cardNumber: String): String {
        val stripped = cardNumber.trim().replace('/', '_')
        val safe = SAFE_CARD_NUMBER_RE.replace(stripped, "_")
        return safe.ifEmpty { "unknown" }
    }
}

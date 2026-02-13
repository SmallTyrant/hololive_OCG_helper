package com.smalltyrant.hocgh.data

import android.content.Context
import java.io.File

private const val APP_NAME = "hOCG_H"
private const val DB_FILE_NAME = "hololive_ocg.sqlite"
private const val IMAGE_BASE_URL = "https://hololive-official-cardgame.com"
private val SAFE_CARD_NUMBER_RE = Regex("[^A-Za-z0-9._-]+")

class AppPaths(private val context: Context) {
    val rootDir: File = File(context.filesDir, APP_NAME).apply { mkdirs() }
    val dbFile: File = File(rootDir, DB_FILE_NAME)
    val imageDir: File = File(rootDir, "images").apply { mkdirs() }

    fun localImageFile(cardNumber: String): File {
        val safe = sanitizeCardNumber(cardNumber)
        return File(imageDir, "$safe.png")
    }

    fun resolveImageUrl(imageUrl: String): String {
        val input = imageUrl.trim()
        if (input.isEmpty()) {
            return ""
        }
        if (input.startsWith("http://") || input.startsWith("https://")) {
            return input
        }
        val base = if (IMAGE_BASE_URL.endsWith('/')) IMAGE_BASE_URL.dropLast(1) else IMAGE_BASE_URL
        return if (input.startsWith('/')) "$base$input" else "$base/$input"
    }

    fun copyBundledDbIfMissing(): Boolean {
        return copyBundledDb(forceReplace = false)
    }

    fun restoreBundledDb(): Boolean {
        return copyBundledDb(forceReplace = true)
    }

    private fun copyBundledDb(forceReplace: Boolean): Boolean {
        if (!forceReplace && dbFile.exists() && dbFile.length() > 0) {
            return false
        }
        dbFile.parentFile?.mkdirs()
        return runCatching {
            context.assets.open(DB_FILE_NAME).use { input ->
                val temp = File(dbFile.parentFile, "${dbFile.name}.tmp")
                if (temp.exists()) {
                    temp.delete()
                }
                temp.outputStream().use { output ->
                    input.copyTo(output)
                }
                if (dbFile.exists()) {
                    dbFile.delete()
                }
                temp.renameTo(dbFile)
            }
            true
        }.getOrDefault(false)
    }

    private fun sanitizeCardNumber(cardNumber: String): String {
        val stripped = cardNumber.trim().replace('/', '_')
        val safe = SAFE_CARD_NUMBER_RE.replace(stripped, "_")
        return safe.ifEmpty { "unknown" }
    }
}

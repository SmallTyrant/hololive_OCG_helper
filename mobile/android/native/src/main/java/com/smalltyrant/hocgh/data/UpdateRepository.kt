package com.smalltyrant.hocgh.data

import android.database.sqlite.SQLiteDatabase
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.IOException
import java.time.Duration

private const val GITHUB_REPO = "SmallTyrant/hololive_OCG_helper"
private const val LATEST_RELEASE_API = "https://api.github.com/repos/$GITHUB_REPO/releases/latest"
private const val LATEST_DB_DIRECT_URL = "https://github.com/$GITHUB_REPO/releases/latest/download/hololive_ocg.sqlite"
private val DB_EXTENSIONS = listOf(".sqlite", ".sqlite3", ".db")

data class ReleaseDbInfo(
    val tag: String,
    val assetName: String,
    val assetUrl: String,
    val assetUpdatedAt: String,
    val publishedAt: String,
    val createdAt: String,
)

class UpdateRepository {
    private val http = OkHttpClient.Builder()
        .callTimeout(Duration.ofSeconds(120))
        .build()

    fun getLatestReleaseDbInfo(): ReleaseDbInfo {
        val payload = fetchLatestReleasePayload()
        return releaseDbInfoFromPayload(payload)
    }

    fun fetchRemoteDbDate(): String? {
        return runCatching {
            val info = getLatestReleaseDbInfo()
            formatIsoDateOrNull(
                info.assetUpdatedAt.ifEmpty {
                    info.publishedAt.ifEmpty { info.createdAt }
                },
            )
        }.getOrNull()
    }

    fun downloadLatestDb(targetDbFile: File): ReleaseDbInfo {
        val releaseInfo = runCatching { getLatestReleaseDbInfo() }.getOrElse {
            ReleaseDbInfo(
                tag = "latest",
                assetName = "hololive_ocg.sqlite",
                assetUrl = LATEST_DB_DIRECT_URL,
                assetUpdatedAt = "",
                publishedAt = "",
                createdAt = "",
            )
        }

        targetDbFile.parentFile?.mkdirs()
        val tempFile = File(targetDbFile.parentFile, "${targetDbFile.name}.download")

        try {
            val request = Request.Builder()
                .url(releaseInfo.assetUrl)
                .header("User-Agent", "hOCG_H/1.1")
                .header("Accept", "application/octet-stream")
                .build()

            http.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw IOException("DB asset HTTP ${response.code}")
                }
                val body = response.body ?: throw IOException("DB asset body is empty")
                tempFile.outputStream().use { output ->
                    body.byteStream().use { input ->
                        input.copyTo(output)
                    }
                }
            }

            validateSqlite(tempFile)
            replaceFile(tempFile, targetDbFile)
            writeReleaseMeta(targetDbFile, releaseInfo)
            return releaseInfo
        } finally {
            if (tempFile.exists()) {
                tempFile.delete()
            }
        }
    }

    private fun fetchLatestReleasePayload(): JSONObject {
        val request = Request.Builder()
            .url(LATEST_RELEASE_API)
            .header("User-Agent", "hOCG_H/1.1")
            .header("Accept", "application/vnd.github+json")
            .build()

        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("GitHub API HTTP ${response.code}")
            }
            val body = response.body?.string().orEmpty()
            if (body.isBlank()) {
                throw IOException("GitHub API response body is empty")
            }
            return JSONObject(body)
        }
    }

    private fun releaseDbInfoFromPayload(payload: JSONObject): ReleaseDbInfo {
        val tag = payload.optString("tag_name", "latest")
        val publishedAt = payload.optString("published_at", "")
        val createdAt = payload.optString("created_at", "")
        val assets = payload.optJSONArray("assets") ?: JSONArray()

        val picked = pickAsset(assets)
        val assetName = picked.first
        val assetUrl = picked.second

        var updatedAt = ""
        for (i in 0 until assets.length()) {
            val item = assets.optJSONObject(i) ?: continue
            val name = item.optString("name", "")
            val url = item.optString("browser_download_url", "")
            if (name == assetName || url == assetUrl) {
                updatedAt = item.optString("updated_at", "")
                break
            }
        }

        return ReleaseDbInfo(
            tag = tag,
            assetName = assetName,
            assetUrl = assetUrl,
            assetUpdatedAt = updatedAt,
            publishedAt = publishedAt,
            createdAt = createdAt,
        )
    }

    private fun pickAsset(assets: JSONArray): Pair<String, String> {
        for (preferred in listOf("hololive_ocg.sqlite")) {
            for (i in 0 until assets.length()) {
                val item = assets.optJSONObject(i) ?: continue
                val name = item.optString("name", "")
                val url = item.optString("browser_download_url", "")
                if (name == preferred && url.isNotBlank()) {
                    return name to url
                }
            }
        }

        for (i in 0 until assets.length()) {
            val item = assets.optJSONObject(i) ?: continue
            val name = item.optString("name", "")
            val url = item.optString("browser_download_url", "")
            if (url.isNotBlank() && DB_EXTENSIONS.any { ext -> name.endsWith(ext) }) {
                return name to url
            }
        }

        return "hololive_ocg.sqlite" to LATEST_DB_DIRECT_URL
    }

    private fun validateSqlite(dbFile: File) {
        if (!dbFile.exists() || !dbFile.isFile || dbFile.length() <= 0L) {
            throw IOException("downloaded DB file is missing or empty")
        }

        FileInputStream(dbFile).use { input ->
            val header = ByteArray(16)
            val read = input.read(header)
            if (read != 16 || !header.contentEquals("SQLite format 3\u0000".toByteArray())) {
                throw IOException("downloaded file is not a valid SQLite database")
            }
        }

        SQLiteDatabase.openDatabase(
            dbFile.absolutePath,
            null,
            SQLiteDatabase.OPEN_READONLY,
        ).useDb { db ->
            val hasPrints = db.rawQuery(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prints'",
                null,
            ).useCursor { cursor -> cursor.moveToFirst() }
            if (!hasPrints) {
                throw IOException("downloaded DB is missing prints table")
            }
        }
    }

    private fun writeReleaseMeta(dbFile: File, info: ReleaseDbInfo) {
        runCatching {
            SQLiteDatabase.openDatabase(
                dbFile.absolutePath,
                null,
                SQLiteDatabase.OPEN_READWRITE,
            ).useDb { db ->
                db.execSQL("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

                val values = mapOf(
                    "release_tag" to info.tag,
                    "release_asset_name" to info.assetName,
                    "release_asset_updated_at" to info.assetUpdatedAt,
                    "release_published_at" to info.publishedAt,
                    "release_created_at" to info.createdAt,
                )

                db.beginTransaction()
                try {
                    for ((key, value) in values) {
                        if (value.isBlank()) {
                            continue
                        }
                        db.execSQL(
                            """
                            INSERT INTO meta(key, value)
                            VALUES(?, ?)
                            ON CONFLICT(key) DO UPDATE SET value = excluded.value
                            """.trimIndent(),
                            arrayOf(key, value),
                        )
                    }
                    db.setTransactionSuccessful()
                } finally {
                    db.endTransaction()
                }
            }
        }
    }

    private fun replaceFile(source: File, target: File) {
        if (target.exists() && !target.delete()) {
            throw IOException("failed to replace existing DB file")
        }
        if (!source.renameTo(target)) {
            source.inputStream().use { input ->
                target.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
            source.delete()
        }
    }
}

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
private const val DB_RELEASE_TAG = "DB"
private const val DB_RELEASE_API = "https://api.github.com/repos/$GITHUB_REPO/releases/tags/$DB_RELEASE_TAG"
private const val DB_DIRECT_URL = "https://github.com/$GITHUB_REPO/releases/download/$DB_RELEASE_TAG/hololive_ocg.sqlite"
private const val APP_RELEASE_TAG = "install_file1"
private const val APP_APK_ASSET_NAME = "app-release.apk"
private const val APP_APK_DIRECT_URL = "https://github.com/$GITHUB_REPO/releases/download/$APP_RELEASE_TAG/$APP_APK_ASSET_NAME"
private const val APP_VERSION_JSON_URL = "https://github.com/$GITHUB_REPO/releases/download/$APP_RELEASE_TAG/version.json"
private val DB_EXTENSIONS = listOf(".sqlite", ".sqlite3", ".db")

data class ReleaseDbInfo(
    val tag: String,
    val assetName: String,
    val assetUrl: String,
    val assetUpdatedAt: String,
    val assetDigest: String,
    val publishedAt: String,
    val createdAt: String,
) {
    val effectiveDateSource: String
        get() = assetUpdatedAt.ifBlank {
            publishedAt.ifBlank { createdAt }
        }

    val updateMarker: String?
        get() = assetDigest.ifBlank { assetUpdatedAt }.ifBlank { null }
}

data class ReleaseApkInfo(
    val tag: String,
    val assetName: String,
    val assetUrl: String,
    val assetUpdatedAt: String,
    val versionName: String,
    val versionCode: Long,
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
            formatIsoDateOrNull(info.effectiveDateSource)
        }.getOrNull()
    }

    fun fetchLatestApkInfo(): ReleaseApkInfo {
        return runCatching {
            fetchVersionJsonApkInfo()
        }.getOrElse {
            ReleaseApkInfo(
                tag = APP_RELEASE_TAG,
                assetName = APP_APK_ASSET_NAME,
                assetUrl = APP_APK_DIRECT_URL,
                assetUpdatedAt = "",
                versionName = "1.0",
                versionCode = 100,
            )
        }
    }

    fun downloadLatestDb(targetDbFile: File): ReleaseDbInfo {
        val releaseInfo = runCatching { getLatestReleaseDbInfo() }.getOrElse {
            ReleaseDbInfo(
                tag = DB_RELEASE_TAG,
                assetName = "hololive_ocg.sqlite",
                assetUrl = DB_DIRECT_URL,
                assetUpdatedAt = "",
                assetDigest = "",
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
        return fetchReleasePayload(DB_RELEASE_API)
    }

    private fun fetchReleasePayload(url: String): JSONObject {
        val request = Request.Builder()
            .url(url)
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
        var digest = ""
        for (i in 0 until assets.length()) {
            val item = assets.optJSONObject(i) ?: continue
            val name = item.optString("name", "")
            val url = item.optString("browser_download_url", "")
            if (name == assetName || url == assetUrl) {
                updatedAt = item.optString("updated_at", "")
                digest = normalizeHash(item.optString("digest", ""))
                break
            }
        }

        return ReleaseDbInfo(
            tag = tag,
            assetName = assetName,
            assetUrl = assetUrl,
            assetUpdatedAt = updatedAt,
            assetDigest = digest,
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

        return "hololive_ocg.sqlite" to DB_DIRECT_URL
    }

    private fun fetchVersionJsonApkInfo(): ReleaseApkInfo {
        val request = Request.Builder()
            .url(APP_VERSION_JSON_URL)
            .header("User-Agent", "hOCG_H/1.1")
            .header("Accept", "application/json")
            .build()

        val payload = http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("Version JSON HTTP ${response.code}")
            }
            val body = response.body?.string().orEmpty()
            if (body.isBlank()) {
                throw IOException("Version JSON body is empty")
            }
            JSONObject(body)
        }

        val versionName = payload.optString("versionName", "").ifBlank {
            payload.optString("version", "1.0")
        }
        val fallbackCode = versionCodeFromName(versionName)
        val versionCode = payload.optLong("versionCode", fallbackCode).takeIf { it > 0 } ?: fallbackCode
        val downloadUrl = payload.optString("apkUrl", "").ifBlank {
            payload.optString("downloadUrl", APP_APK_DIRECT_URL)
        }

        return ReleaseApkInfo(
            tag = payload.optString("tag", APP_RELEASE_TAG),
            assetName = APP_APK_ASSET_NAME,
            assetUrl = downloadUrl,
            assetUpdatedAt = payload.optString("updatedAt", ""),
            versionName = versionName,
            versionCode = versionCode,
        )
    }

    private fun versionCodeFromName(versionName: String): Long {
        val parts = versionName.split('.')
            .mapNotNull { it.toIntOrNull() }
        if (parts.isEmpty()) {
            return 100
        }
        val major = parts.getOrElse(0) { 1 }
        val minor = parts.getOrElse(1) { 0 }
        val patch = parts.getOrElse(2) { 0 }
        return major * 100L + minor * 10L + patch
    }

    private fun normalizeHash(raw: String?): String {
        val value = raw?.trim()?.lowercase().orEmpty()
        return if (value.startsWith("sha256:")) value.removePrefix("sha256:").trim() else value
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
                    "release_asset_digest" to info.assetDigest,
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

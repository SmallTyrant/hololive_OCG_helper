package com.smalltyrant.hocgh.data

import com.smalltyrant.hocgh.model.ImageState
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.time.Duration

class ImageRepository(private val paths: AppPaths) {
    private val http = OkHttpClient.Builder()
        .callTimeout(Duration.ofSeconds(30))
        .build()
    private val offlineImageMessage = "네트워크 연결이 필요합니다.\n또는 캐시된 이미지가 없습니다."

    private val lock = Any()
    private val downloading = mutableSetOf<String>()

    private fun shouldIgnoreLegacyCache(cardNumber: String): Boolean {
        val normalized = cardNumber.trim().uppercase()
        return normalized.startsWith("HY")
    }

    private fun cachedLocalFile(cardNumber: String, imageUrl: String, variant: String): File? {
        val resolved = paths.resolveImageUrl(imageUrl)
        val current = paths.localImageFile(cardNumber, variant, resolved)
        if (current.exists()) {
            return current
        }
        if (!shouldIgnoreLegacyCache(cardNumber)) {
            val legacy = paths.legacyLocalImageFile(cardNumber, variant)
            if (legacy.exists()) {
                return legacy
            }
        }
        return null
    }

    fun resolveLocalOrRemote(cardNumber: String, imageUrl: String, variant: String = ""): ImageState {
        if (cardNumber.isBlank()) {
            return ImageState.Placeholder("이미지 없음")
        }
        val local = cachedLocalFile(cardNumber, imageUrl, variant)
        if (local != null) {
            return ImageState.Local(local)
        }
        val resolved = paths.resolveImageUrl(imageUrl)
        if (resolved.isBlank()) {
            return ImageState.Placeholder("이미지 URL 없음")
        }

        if (!paths.hasNetworkConnection()) {
            return ImageState.Error(offlineImageMessage)
        }
        return ImageState.Remote(resolved)
    }

    fun downloadIfNeeded(cardNumber: String, imageUrl: String, variant: String = ""): ImageState {
        if (cardNumber.isBlank()) {
            return ImageState.Placeholder("이미지 없음")
        }

        val local = cachedLocalFile(cardNumber, imageUrl, variant)
        if (local != null) {
            return ImageState.Local(local)
        }

        val resolved = paths.resolveImageUrl(imageUrl)
        if (resolved.isBlank()) {
            return ImageState.Placeholder("이미지 URL 없음")
        }
        val destination = paths.localImageFile(cardNumber, variant, resolved)

        val shouldDownload = synchronized(lock) {
            val downloadKey = "$cardNumber|$variant|$resolved"
            if (downloading.contains(downloadKey)) {
                false
            } else {
                downloading += downloadKey
                true
            }
        }

        if (!shouldDownload) {
            return ImageState.Remote(resolved)
        }

        return try {
            download(resolved, destination)
            ImageState.Local(destination)
        } catch (_: Throwable) {
            if (!paths.hasNetworkConnection()) {
                ImageState.Error(offlineImageMessage)
            } else {
                ImageState.Error("이미지 로딩 실패")
            }
        } finally {
            synchronized(lock) {
                downloading -= "$cardNumber|$variant|$resolved"
            }
        }
    }

    private fun download(url: String, destination: File) {
        destination.parentFile?.mkdirs()
        val temp = File(destination.parentFile, "${destination.name}.tmp")
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "hOCG_H/1.1")
            .build()

        try {
            http.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw IOException("image HTTP ${response.code}")
                }
                val body = response.body ?: throw IOException("image body is empty")
                temp.outputStream().use { output ->
                    body.byteStream().use { input ->
                        input.copyTo(output)
                    }
                }
            }

            if (destination.exists()) {
                destination.delete()
            }
            if (!temp.renameTo(destination)) {
                temp.inputStream().use { input ->
                    destination.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
            }
        } finally {
            if (temp.exists()) {
                temp.delete()
            }
        }
    }
}

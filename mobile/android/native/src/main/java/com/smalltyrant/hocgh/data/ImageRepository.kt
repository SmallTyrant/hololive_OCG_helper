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

    private val lock = Any()
    private val downloading = mutableSetOf<String>()

    fun resolveLocalOrRemote(cardNumber: String, imageUrl: String): ImageState {
        if (cardNumber.isBlank()) {
            return ImageState.Placeholder("이미지 없음")
        }
        val local = paths.localImageFile(cardNumber)
        if (local.exists()) {
            return ImageState.Local(local)
        }
        val resolved = paths.resolveImageUrl(imageUrl)
        if (resolved.isBlank()) {
            return ImageState.Placeholder("이미지 URL 없음")
        }
        return ImageState.Remote(resolved)
    }

    fun downloadIfNeeded(cardNumber: String, imageUrl: String): ImageState {
        if (cardNumber.isBlank()) {
            return ImageState.Placeholder("이미지 없음")
        }

        val local = paths.localImageFile(cardNumber)
        if (local.exists()) {
            return ImageState.Local(local)
        }

        val resolved = paths.resolveImageUrl(imageUrl)
        if (resolved.isBlank()) {
            return ImageState.Placeholder("이미지 URL 없음")
        }

        val shouldDownload = synchronized(lock) {
            if (downloading.contains(cardNumber)) {
                false
            } else {
                downloading += cardNumber
                true
            }
        }

        if (!shouldDownload) {
            return ImageState.Remote(resolved)
        }

        return try {
            download(resolved, local)
            ImageState.Local(local)
        } catch (_: Throwable) {
            ImageState.Error("이미지 로딩 실패")
        } finally {
            synchronized(lock) {
                downloading -= cardNumber
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

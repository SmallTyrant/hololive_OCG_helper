package com.smalltyrant.hocgh.ui

import java.util.Locale

enum class PreferredLanguage(
    val value: String,
    val label: String,
) {
    KOREAN("ko", "한국어"),
    JAPANESE("ja", "일본어"),
    ;

    companion object {
        fun fromValue(value: String?): PreferredLanguage {
            return entries.firstOrNull { it.value == value } ?: KOREAN
        }

        fun fromSystemLocale(): PreferredLanguage {
            return when (Locale.getDefault().language.lowercase(Locale.ROOT)) {
                "ja" -> JAPANESE
                else -> KOREAN
            }
        }
    }
}

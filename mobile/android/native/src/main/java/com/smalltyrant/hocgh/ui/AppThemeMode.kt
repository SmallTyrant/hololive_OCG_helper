package com.smalltyrant.hocgh.ui

enum class AppThemeMode(val value: String, val label: String) {
    SYSTEM("system", "시스템 기본"),
    LIGHT("light", "라이트 모드"),
    DARK("dark", "다크 모드"),
    ;

    companion object {
        fun fromValue(raw: String?): AppThemeMode {
            return entries.firstOrNull { it.value == raw } ?: SYSTEM
        }
    }
}

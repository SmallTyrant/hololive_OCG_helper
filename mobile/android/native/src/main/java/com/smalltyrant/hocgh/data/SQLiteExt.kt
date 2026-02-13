package com.smalltyrant.hocgh.data

import android.database.Cursor
import android.database.sqlite.SQLiteDatabase

internal inline fun <T> Cursor.useCursor(block: (Cursor) -> T): T {
    return use(block)
}

internal inline fun <T> SQLiteDatabase.useDb(block: (SQLiteDatabase) -> T): T {
    return try {
        block(this)
    } finally {
        close()
    }
}

internal fun Cursor.getStringOrNull(index: Int): String? {
    if (index < 0 || isNull(index)) {
        return null
    }
    return getString(index)
}

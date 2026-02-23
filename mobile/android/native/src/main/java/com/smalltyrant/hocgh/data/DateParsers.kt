package com.smalltyrant.hocgh.data

import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset

fun formatIsoDateOrNull(rawInput: String?): String? {
    val raw = rawInput?.trim().orEmpty()
    if (raw.isEmpty()) {
        return null
    }

    val candidates = linkedSetOf(raw)
    if (raw.endsWith("Z")) {
        candidates.add(raw.removeSuffix("Z") + "+00:00")
    }
    if (" " in raw && "T" !in raw) {
        candidates.add(raw.replace(" ", "T"))
    }

    for (value in candidates) {
        runCatching {
            return Instant.parse(value).atOffset(ZoneOffset.UTC).toLocalDate().toString()
        }
        runCatching {
            return OffsetDateTime.parse(value).withOffsetSameInstant(ZoneOffset.UTC).toLocalDate().toString()
        }
        runCatching {
            return LocalDateTime.parse(value).toLocalDate().toString()
        }
        runCatching {
            return LocalDate.parse(value).toString()
        }
    }
    return null
}

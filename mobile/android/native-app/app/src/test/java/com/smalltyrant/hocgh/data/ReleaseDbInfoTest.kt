package com.smalltyrant.hocgh.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ReleaseDbInfoTest {
    @Test
    fun `effective date source prefers asset updated at`() {
        val info = ReleaseDbInfo(
            tag = "DB",
            assetName = "hololive_ocg.sqlite",
            assetUrl = "https://example.com/db.sqlite",
            assetUpdatedAt = "2026-04-17T00:00:00Z",
            assetDigest = "",
            publishedAt = "2026-04-16T00:00:00Z",
            createdAt = "2026-04-15T00:00:00Z",
        )

        assertEquals("2026-04-17T00:00:00Z", info.effectiveDateSource)
    }

    @Test
    fun `effective date source falls back to published then created`() {
        val publishedInfo = ReleaseDbInfo(
            tag = "DB",
            assetName = "hololive_ocg.sqlite",
            assetUrl = "https://example.com/db.sqlite",
            assetUpdatedAt = "",
            assetDigest = "",
            publishedAt = "2026-04-16T00:00:00Z",
            createdAt = "2026-04-15T00:00:00Z",
        )
        val createdInfo = publishedInfo.copy(publishedAt = "")

        assertEquals("2026-04-16T00:00:00Z", publishedInfo.effectiveDateSource)
        assertEquals("2026-04-15T00:00:00Z", createdInfo.effectiveDateSource)
    }

    @Test
    fun `update marker prefers digest and falls back to date`() {
        val digestInfo = ReleaseDbInfo(
            tag = "DB",
            assetName = "hololive_ocg.sqlite",
            assetUrl = "https://example.com/db.sqlite",
            assetUpdatedAt = "2026-04-17T00:00:00Z",
            assetDigest = "abc123",
            publishedAt = "",
            createdAt = "",
        )
        val dateInfo = digestInfo.copy(assetDigest = "")
        val emptyInfo = dateInfo.copy(assetUpdatedAt = "")

        assertEquals("abc123", digestInfo.updateMarker)
        assertEquals("2026-04-17T00:00:00Z", dateInfo.updateMarker)
        assertNull(emptyInfo.updateMarker)
    }
}

package com.smalltyrant.hocgh.data

import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class AppPathsTest {
    private val paths = AppPaths(ApplicationProvider.getApplicationContext())

    @Test
    fun `blank input returns empty string`() {
        assertEquals("", paths.resolveImageUrl("   "))
    }

    @Test
    fun `protocol relative url is upgraded to https`() {
        assertEquals(
            "https://example.com/card.png",
            paths.resolveImageUrl("//example.com/card.png"),
        )
    }

    @Test
    fun `absolute url is preserved`() {
        assertEquals(
            "https://cdn.example.com/card.png?v=2#front",
            paths.resolveImageUrl("https://cdn.example.com/card.png?v=2#front"),
        )
    }

    @Test
    fun `relative path is resolved against official site`() {
        assertEquals(
            "https://hololive-official-cardgame.com/wp-content/card.png",
            paths.resolveImageUrl("/wp-content/card.png"),
        )
    }

    @Test
    fun `relative path keeps query and fragment`() {
        assertEquals(
            "https://hololive-official-cardgame.com/wp-content/card.png?v=2#front",
            paths.resolveImageUrl("/wp-content/card.png?v=2#front"),
        )
    }

    @Test
    fun `non http absolute scheme is not treated as relative path`() {
        assertEquals(
            "data:image/png;base64,abcd",
            paths.resolveImageUrl("data:image/png;base64,abcd"),
        )
    }
}

@RunWith(RobolectricTestRunner::class)
class AppPathsBundledDbTest {
    private val paths = AppPaths(ApplicationProvider.getApplicationContext())

    @Test
    fun `mobile build does not copy a bundled database`() {
        assertEquals(false, paths.copyBundledDbIfMissing())
        assertEquals(false, paths.restoreBundledDb())
    }
}

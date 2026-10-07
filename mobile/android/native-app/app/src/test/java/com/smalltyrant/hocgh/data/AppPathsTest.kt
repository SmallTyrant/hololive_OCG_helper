package com.smalltyrant.hocgh.data

import android.Manifest
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.PackageManager
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
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

    @Test
    fun `app declares network state permission`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val packageInfo = context.packageManager.getPackageInfo(
            context.packageName,
            PackageManager.GET_PERMISSIONS,
        )

        assertTrue(packageInfo.requestedPermissions?.contains(Manifest.permission.ACCESS_NETWORK_STATE) == true)
    }

    @Test
    fun `network permission failure does not crash image fallback`() {
        val base = ApplicationProvider.getApplicationContext<Context>()
        val deniedContext = object : ContextWrapper(base) {
            override fun getSystemService(name: String): Any? {
                if (name == Context.CONNECTIVITY_SERVICE) {
                    throw SecurityException("network state permission denied")
                }
                return super.getSystemService(name)
            }
        }

        assertTrue(AppPaths(deniedContext).hasNetworkConnection())
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

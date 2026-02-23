package com.smalltyrant.hocgh

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.smalltyrant.hocgh.ui.AppThemeMode
import com.smalltyrant.hocgh.ui.HocgScreen
import com.smalltyrant.hocgh.ui.PreferredLanguage

private const val PREFS_NAME = "hocg_settings"
private const val PREF_THEME_MODE = "theme_mode"
private const val PREF_PREFERRED_LANGUAGE = "preferred_language"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val prefs = remember { getSharedPreferences(PREFS_NAME, MODE_PRIVATE) }
            var themeMode by remember {
                mutableStateOf(
                    AppThemeMode.fromValue(
                        prefs.getString(PREF_THEME_MODE, AppThemeMode.SYSTEM.value),
                    ),
                )
            }
            var preferredLanguage by remember {
                mutableStateOf(
                    PreferredLanguage.fromValue(
                        prefs.getString(
                            PREF_PREFERRED_LANGUAGE,
                            PreferredLanguage.fromSystemLocale().value,
                        ),
                    ),
                )
            }
            val useDarkTheme = when (themeMode) {
                AppThemeMode.SYSTEM -> isSystemInDarkTheme()
                AppThemeMode.LIGHT -> false
                AppThemeMode.DARK -> true
            }

            MaterialTheme(
                colorScheme = if (useDarkTheme) darkColorScheme() else lightColorScheme(),
            ) {
                Surface {
                    HocgScreen(
                        themeMode = themeMode,
                        onThemeModeChange = { nextMode ->
                            themeMode = nextMode
                            prefs.edit().putString(PREF_THEME_MODE, nextMode.value).apply()
                        },
                        preferredLanguage = preferredLanguage,
                        onPreferredLanguageChange = { nextLanguage ->
                            preferredLanguage = nextLanguage
                            prefs.edit().putString(PREF_PREFERRED_LANGUAGE, nextLanguage.value).apply()
                        },
                    )
                }
            }
        }
    }
}

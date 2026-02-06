package com.hololive.ocghelper

import android.database.sqlite.SQLiteDatabase
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val dbStatus = copyBundledDbIfPresent()

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    HomeScreen(dbStatus)
                }
            }
        }
    }

    private fun copyBundledDbIfPresent(): String {
        val dbName = "hololive_ocg.sqlite"
        val dbFile = getDatabasePath(dbName)
        dbFile.parentFile?.mkdirs()

        if (!dbFile.exists()) {
            runCatching {
                assets.open(dbName).use { input ->
                    dbFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
            }.onFailure {
                return "assets DB 없음(빌드는 가능). DB를 포함해 다시 빌드하세요."
            }
        }

        return runCatching {
            SQLiteDatabase.openDatabase(dbFile.path, null, SQLiteDatabase.OPEN_READONLY).use { db ->
                val cursor = db.rawQuery("SELECT name FROM sqlite_master WHERE type='table'", null)
                val count = cursor.use {
                    var total = 0
                    while (it.moveToNext()) total++
                    total
                }
                "DB 로드 성공: 테이블 ${count}개 감지"
            }
        }.getOrElse {
            "DB 열기 실패"
        }
    }
}

@Composable
private fun HomeScreen(dbStatus: String) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(text = "hOCG_H", style = MaterialTheme.typography.headlineSmall)
        Text(text = "Android Kotlin 네이티브 앱 초기화 완료")
        Text(text = dbStatus)
    }
}

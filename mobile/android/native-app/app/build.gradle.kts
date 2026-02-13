plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.smalltyrant.hocgh"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.smalltyrant.hocgh"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("../../native/src/main/java")
            assets.srcDirs("src/main/assets")
        }
    }
}

val syncBundledDb by tasks.registering {
    group = "assets"
    description = "Copies root data/hololive_ocg.sqlite into app assets when available"

    doLast {
        val repoRoot = rootProject.projectDir.resolve("../../..").normalize()
        val src = repoRoot.resolve("data/hololive_ocg.sqlite")
        val assetsDir = project.layout.projectDirectory.dir("src/main/assets").asFile
        val dst = assetsDir.resolve("hololive_ocg.sqlite")

        assetsDir.mkdirs()

        if (!src.exists() || !src.isFile || src.length() <= 0L) {
            logger.lifecycle("[syncBundledDb] skipped: source DB not found at ${src.absolutePath}")
            return@doLast
        }

        src.copyTo(dst, overwrite = true)
        logger.lifecycle("[syncBundledDb] copied DB -> ${dst.absolutePath}")
    }
}

tasks.named("preBuild") {
    dependsOn(syncBundledDb)
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("io.coil-kt:coil-compose:2.7.0")

    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

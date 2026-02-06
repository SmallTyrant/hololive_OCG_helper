import java.nio.file.Files
import java.nio.file.StandardCopyOption

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hololive.ocghelper"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.hololive.ocghelper"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
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
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.15"
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

val syncBundledDb by tasks.registering {
    val sourceDb = rootProject.file("../../data/hololive_ocg.sqlite")
    val assetDir = layout.projectDirectory.dir("src/main/assets")
    val targetDb = assetDir.file("hololive_ocg.sqlite").asFile

    outputs.file(targetDb)

    doLast {
        assetDir.asFile.mkdirs()
        if (sourceDb.exists()) {
            Files.copy(sourceDb.toPath(), targetDb.toPath(), StandardCopyOption.REPLACE_EXISTING)
            logger.lifecycle("Bundled DB copied: ${sourceDb.absolutePath} -> ${targetDb.absolutePath}")
        } else {
            logger.lifecycle(
                "Bundled DB not found at ${sourceDb.absolutePath}. Build continues without prepackaged DB."
            )
            if (targetDb.exists()) {
                targetDb.delete()
            }
        }
    }
}

tasks.named("preBuild") {
    dependsOn(syncBundledDb)
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation(platform("androidx.compose:compose-bom:2025.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")

    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

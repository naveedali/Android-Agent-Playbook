"""Tiny fake Android projects for tests. Only the files detection reads."""

import os
import tempfile


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


COMPOSE_HILT = {
    "gradlew": "#!/bin/sh\n",
    "settings.gradle.kts": '''pluginManagement { includeBuild("build-logic") }
rootProject.name = "TaskFlow"
include(":app")
include(
    ":core:data",
    ":core:ui", // shared design system
)
include(":feature:home")
// include(":feature:old")
''',
    "build.gradle.kts": "plugins { alias(libs.plugins.android.application) apply false }\n",
    "gradle/libs.versions.toml": '''[versions]
agp = "8.13.0"
kotlin = "2.2.20"
minSdk = "26"
compose-bom = "2026.01.00"
hilt = "2.57"
room = "2.8.0"
[libraries]
androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "compose-bom" }
hilt-android = { group = "com.google.dagger", name = "hilt-android", version.ref = "hilt" }
androidx-room-runtime = { group = "androidx.room", name = "room-runtime", version.ref = "room" }
kotlinx-coroutines-test = { group = "org.jetbrains.kotlinx", name = "kotlinx-coroutines-test", version = "1.10.0" }
junit = { group = "junit", name = "junit", version = "4.13.2" }
turbine = { group = "app.cash.turbine", name = "turbine", version = "1.2.0" }
mockk = { group = "io.mockk", name = "mockk", version = "1.14.0" }
androidx-compose-ui-test-junit4 = { group = "androidx.compose.ui", name = "ui-test-junit4" }
androidx-navigation-compose = { group = "androidx.navigation", name = "navigation-compose", version = "2.9.0" }
[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
ktlint = { id = "org.jlleitschuh.gradle.ktlint", version = "13.0.0" }
''',
    "build-logic/convention/build.gradle.kts": "plugins { `kotlin-dsl` }\nkotlin { jvmToolchain(17) }\n",
    "gradle/wrapper/gradle-wrapper.properties": "distributionUrl=https\\://services.gradle.org/distributions/gradle-9.1.0-bin.zip\n",
    "app/build.gradle.kts": '''plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
}
android {
    compileSdk = 36
    defaultConfig {
        minSdk = libs.versions.minSdk.get().toInt()
        targetSdk = 36
    }
    buildFeatures { compose = true }
}
''',
    "core/data/build.gradle.kts": "plugins { alias(libs.plugins.android.library) }\n",
    "core/ui/build.gradle.kts": "plugins { id(\"com.android.library\") }\n",
    "feature/home/build.gradle.kts": "plugins { id(\"taskflow.android.feature\") }\n",
}

VIEWS_COMPOSE_GROOVY = {
    "gradlew": "#!/bin/sh\n",
    "settings.gradle": "rootProject.name = 'LegacyShop'\ninclude ':app', ':feature:cart'\n",
    "build.gradle": "buildscript { dependencies { classpath 'com.android.tools.build:gradle:7.4.2' } }\n",
    "app/build.gradle": '''plugins {
    id 'com.android.application'
    id 'kotlin-kapt'
}
android {
    compileSdkVersion 34
    defaultConfig {
        minSdkVersion 21
        targetSdkVersion 34
    }
    kotlinOptions { jvmTarget = '1.8' }
    buildFeatures { viewBinding true; compose true }
}
dependencies {
    implementation "androidx.compose.ui:ui:1.9.0"
    implementation "io.insert-koin:koin-android:4.0.0"
    testImplementation "junit:junit:4.13.2"
    testImplementation "org.mockito:mockito-core:5.0.0"
}
''',
    "app/src/main/res/layout/activity_main.xml": "<LinearLayout/>\n",
    "feature/cart/build.gradle": "plugins { id 'com.android.library' }\n",
}

KMP = {
    "gradlew": "#!/bin/sh\n",
    "settings.gradle.kts": 'rootProject.name = "NotesKmp"\ninclude(":shared")\ninclude(":androidApp")\n',
    "build.gradle.kts": "",
    "gradle/libs.versions.toml": '''[libraries]
sqldelight-runtime = { module = "app.cash.sqldelight:runtime", version = "2.1.0" }
koin-core = { module = "io.insert-koin:koin-core", version = "4.0.0" }
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version = "1.10.0" }
[plugins]
kotlinMultiplatform = { id = "org.jetbrains.kotlin.multiplatform", version = "2.2.0" }
composeMultiplatform = { id = "org.jetbrains.compose", version = "1.9.0" }
androidApplication = { id = "com.android.application", version = "8.13.0" }
''',
    "shared/build.gradle.kts": '''plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidLibrary)
}
kotlin { androidTarget(); iosArm64(); sourceSets { commonTest.dependencies { implementation(kotlin("test")) } } }
''',
    "androidApp/build.gradle.kts": "plugins { alias(libs.plugins.androidApplication); alias(libs.plugins.composeMultiplatform) }\n",
}


FLAVORED = {
    "gradlew": "#!/bin/sh\n",
    "settings.gradle.kts": 'rootProject.name = "Shopper"\ninclude(":app", ":core:network")\n',
    "build.gradle.kts": "",
    "app/build.gradle.kts": '''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    compileSdk = 35
    defaultConfig { minSdk = 24 }
    flavorDimensions += "env"
    productFlavors {
        create("prod") {
            dimension = "env"
        }
        create("dev") {
            dimension = "env"
            applicationIdSuffix = ".dev"
        }
    }
    buildFeatures { compose = true }
}
dependencies { testImplementation("junit:junit:4.13.2") }
''',
    "core/network/build.gradle.kts": 'plugins { id("com.android.library") }\n',
}


def make(files):
    root = tempfile.mkdtemp(prefix="aap-")
    for rel, text in files.items():
        _write(root, rel, text)
    return root

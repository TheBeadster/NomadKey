plugins { id("com.android.application"); id("com.chaquo.python") }
android {
    namespace = "org.nomadkey.host"
    compileSdk = 36
    defaultConfig {
        applicationId = "org.nomadkey.host.dev"
        minSdk = 26
        targetSdk = 36
        versionCode = 2
        versionName = "0.1-dev2"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64") }
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    lint { abortOnError = true }
}
dependencies {
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
}
chaquopy {
    defaultConfig {
        version = "3.11"
        pip {
            install(rootProject.file("vendor/nomadkey-0.1.0.dev10-py3-none-any.whl").absolutePath)
            install("rns==1.5.7")
            install("lxmf==1.2.1")
            install("cryptography==42.0.8")
        }
    }
}

[app]
title = UUS
package.name = uus_app
package.domain = com.uus

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf

# Вказуємо Python 3.12
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pymysql==1.1.1

# Дозволи
android.permissions = INTERNET, ACCESS_NETWORK_STATE

# Налаштування Android 15 (API 35)
android.api = 35
android.minapi = 24
android.ndk = 25b

# Архітектури
android.archs = arm64-v8a, armeabi-v7a

# Підпис (debug для тестів)
android.debug_artifact = 1
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1

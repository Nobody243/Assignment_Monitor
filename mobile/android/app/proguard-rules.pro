# Kept when code shrinking is on (-Pminify=true). Flutter's own rules come with the Flutter Gradle plugin.

# flutter_local_notifications reads its saved notifications with Gson, by field name
-keep class com.dexterous.** { *; }
-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod
-dontwarn com.google.errorprone.annotations.**

# WorkManager instantiates the plugin's worker by name
-keep class androidx.work.** { *; }
-keep class dev.fluttercommunity.workmanager.** { *; }

# local_auth shows its prompt through androidx.biometric
-keep class androidx.biometric.** { *; }

package com.nobody243.assignment_monitor_mobile

import android.os.Bundle
import android.view.WindowManager
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * FlutterFragmentActivity (not FlutterActivity) because the biometric prompt of the app lock needs a FragmentActivity.
 *
 * FLAG_SECURE keeps screenshots and screen recordings black and blanks the app's preview in the recent-apps list. It is on
 * from the first frame; Dart (lib/secure_screen.dart) turns it off again only if the user switched the setting off.
 */
class MainActivity : FlutterFragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "am/secure").setMethodCallHandler { call, result ->
            if (call.method == "set") {
                val on = call.argument<Boolean>("on") ?: true
                runOnUiThread {
                    if (on) window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
                    else window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
                }
                result.success(null)
            } else {
                result.notImplemented()
            }
        }
    }
}

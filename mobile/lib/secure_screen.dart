import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;
import 'package:flutter/services.dart';

/// Android's FLAG_SECURE: while it is on, screenshots and screen recording show black, and the app's preview in the
/// recent-apps list is blank, so grades are not visible there. The native side (MainActivity.kt) turns it on as the
/// app starts; this switches it to match the setting.
class SecureScreen {
  static const _channel = MethodChannel('am/secure');

  static Future<void> set(bool on) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await _channel.invokeMethod<void>('set', {'on': on});
    } catch (_) {
      // a build without the native part (a test, say) simply has no flag to set
    }
  }
}

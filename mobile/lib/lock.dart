import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:local_auth/local_auth.dart';

/// The phone's own lock (fingerprint, face, or the PIN, pattern or password) used to guard the app. The app never sees
/// the fingerprint or the PIN: Android answers yes or no.
abstract class Locker {
  /// Whether the phone has a screen lock or biometrics set up that can be asked.
  Future<bool> available();

  /// Asks the phone to verify the person. True only when it said yes.
  Future<bool> verify(String reason);
}

class DeviceLocker implements Locker {
  final _auth = LocalAuthentication();

  @override
  Future<bool> available() async {
    if (kIsWeb) return false;
    try {
      return await _auth.isDeviceSupported();
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> verify(String reason) async {
    try {
      return await _auth.authenticate(localizedReason: reason, persistAcrossBackgrounding: true);
    } catch (_) {
      return false;   // cancelled, too many tries, or no lock set up: stay locked
    }
  }
}

/// When the app locks itself, decided in one place so it is tested without a phone.
class LockPolicy {
  const LockPolicy({this.after = const Duration(seconds: 30)});

  /// How long the app may sit in the background before it asks again. Short trips (a notification, a copy from another
  /// app) do not interrupt; leaving it for longer does.
  final Duration after;

  bool shouldLock({required bool enabled, required DateTime? leftAt, required DateTime now}) =>
      enabled && leftAt != null && now.difference(leftAt) >= after;
}

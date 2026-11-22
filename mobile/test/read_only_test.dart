import 'dart:io';

import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  _startupTest();
  test('the phone app is read-only: no hidden browser, portal sign-in or downloads', () {
    final pubspec = File('pubspec.yaml').readAsStringSync();
    for (final p in ['webview_flutter', 'file_picker', 'html:']) {
      expect(pubspec.contains(p), isFalse, reason: '$p must stay out of the phone app');
    }
    for (final f in ['portal.dart', 'portal_sync.dart', 'screens/portal_signin.dart', 'screens/lectures.dart']) {
      expect(File('lib/$f').existsSync(), isFalse, reason: '$f was removed');
    }
    expect(File('lib/main.dart').readAsStringSync().contains('Lectures'), isFalse);
  });

  test('release builds keep what the notification plugin needs', () {
    final rules = File('android/app/proguard-rules.pro').readAsStringSync();
    expect(rules.contains('com.google.gson.reflect.TypeToken'), isTrue);
    expect(rules.contains('com.dexterous'), isTrue);
  });
}

class _BrokenVault implements Vault {
  @override Future<String?> read(String key) async => throw StateError('keystore not ready');
  @override Future<void> write(String key, String value) async {}
  @override Future<void> delete(String key) async {}
}

void _startupTest() {
  test('a keystore that throws on the first start does not leave the app stuck on loading', () async {
    SharedPreferences.setMockInitialValues({});
    final m = AppModel(Prefs(), store: Store(vault: _BrokenVault()), splashMin: Duration.zero);
    await m.start();
    expect(m.phase, Phase.signedOut);
  });
}

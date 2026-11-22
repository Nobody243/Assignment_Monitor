import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
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

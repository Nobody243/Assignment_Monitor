import 'package:assignment_monitor_mobile/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('the status bar icons and clock are dark on a light page and light on a dark page, in every palette', () {
    for (final p in palettes) {
      final light = buildTheme(p, Brightness.light).appBarTheme.systemOverlayStyle!;
      final dark = buildTheme(p, Brightness.dark).appBarTheme.systemOverlayStyle!;
      expect(light.statusBarIconBrightness, Brightness.dark, reason: '${p.label} light');
      expect(dark.statusBarIconBrightness, Brightness.light, reason: '${p.label} dark');
      expect(light.systemNavigationBarIconBrightness, Brightness.dark);
      expect(dark.systemNavigationBarIconBrightness, Brightness.light);
      expect(light.statusBarColor, Colors.transparent);
    }
  });
}

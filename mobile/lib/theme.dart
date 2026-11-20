import 'package:flutter/material.dart';

/// The four desktop palettes as Material 3 color schemes. Ember (the website's orange) is the default.
class Palette {
  const Palette(this.key, this.label, this.seed);
  final String key;
  final String label;
  final Color seed;
}

const palettes = [
  Palette('ember', 'Ember', Color(0xFFE8552B)),
  Palette('royal', 'Royal', Color(0xFF3558D9)),
  Palette('ink', 'Ink', Color(0xFF3A3A3A)),
  Palette('forest', 'Forest', Color(0xFF2F8F4E)),
];

ThemeData buildTheme(Palette p, Brightness b) {
  final scheme = ColorScheme.fromSeed(seedColor: p.seed, brightness: b);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: b == Brightness.light ? const Color(0xFFFFFAF6) : const Color(0xFF14110F),
    cardTheme: CardThemeData(elevation: 0, color: scheme.surfaceContainerLow, margin: EdgeInsets.zero, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20))),
    navigationBarTheme: NavigationBarThemeData(height: 64, backgroundColor: scheme.surfaceContainer, indicatorColor: scheme.primaryContainer),
    chipTheme: ChipThemeData(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
    appBarTheme: const AppBarTheme(centerTitle: false, scrolledUnderElevation: 0, backgroundColor: Colors.transparent),
  );
}

/// Status colours that carry meaning, kept apart from the palette so a palette never changes what "late" looks like.
class Status {
  static const Color late = Color(0xFFC1121F);
  static Color warn(Brightness b) => b == Brightness.light ? const Color(0xFF8A5300) : const Color(0xFFF2B84B);
  static Color good(Brightness b) => b == Brightness.light ? const Color(0xFF1B7A43) : const Color(0xFF6BD69A);
  static Color bad(Brightness b) => b == Brightness.light ? late : const Color(0xFFFF8A8A);
}

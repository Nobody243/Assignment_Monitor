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
  final base = ColorScheme.fromSeed(seedColor: p.seed, brightness: b);
  final dark = b == Brightness.dark;
  // Same seed, but surfaces are warm neutrals one step apart (so a card reads against the page) and the
  // secondary text is kept well above AA contrast. The accent only appears where something is actionable.
  final scheme = base.copyWith(
    surface: dark ? const Color(0xFF16120F) : const Color(0xFFFFFAF6),
    surfaceContainerLowest: dark ? const Color(0xFF110E0C) : const Color(0xFFFFFFFF),
    surfaceContainerLow: dark ? const Color(0xFF1E1916) : const Color(0xFFFBF1EA),
    surfaceContainer: dark ? const Color(0xFF241E1A) : const Color(0xFFF6EAE1),
    surfaceContainerHigh: dark ? const Color(0xFF2D2621) : const Color(0xFFF0E2D8),
    surfaceContainerHighest: dark ? const Color(0xFF383029) : const Color(0xFFE9D8CB),
    onSurface: dark ? const Color(0xFFF4EBE5) : const Color(0xFF241A15),
    onSurfaceVariant: dark ? const Color(0xFFCDBFB6) : const Color(0xFF5A4A41),
    outlineVariant: dark ? const Color(0xFF4A3F37) : const Color(0xFFD9C6B9),
  );
  return ThemeData(
    useMaterial3: true,
    pageTransitionsTheme: const PageTransitionsTheme(builders: {TargetPlatform.android: FadeForwardsPageTransitionsBuilder()}),
    colorScheme: scheme,
    scaffoldBackgroundColor: scheme.surface,
    cardTheme: CardThemeData(elevation: 0, color: scheme.surfaceContainer, margin: EdgeInsets.zero, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20))),
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

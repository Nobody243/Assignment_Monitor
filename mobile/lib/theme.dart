import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show SystemUiOverlayStyle;

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

/// The phone's status bar and navigation bar to match the page: dark icons and clock on a light page, light ones on a dark
/// page. A transparent AppBar makes Flutter guess "dark background" and draw white icons, which vanish on a light page.
SystemUiOverlayStyle overlayStyle(Brightness b, Color page) {
  final lightPage = b == Brightness.light;
  return SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: lightPage ? Brightness.dark : Brightness.light,
    statusBarBrightness: b,   // iOS: the same, named from the bar's side
    systemNavigationBarColor: page,
    systemNavigationBarIconBrightness: lightPage ? Brightness.dark : Brightness.light,
    systemNavigationBarDividerColor: Colors.transparent,
    systemNavigationBarContrastEnforced: false,
  );
}

ThemeData buildTheme(Palette p, Brightness b) {
  final base = ColorScheme.fromSeed(seedColor: p.seed, brightness: b, dynamicSchemeVariant: p.key == 'ink' ? DynamicSchemeVariant.neutral : (b == Brightness.light ? DynamicSchemeVariant.vibrant : DynamicSchemeVariant.tonalSpot));   // Ink stays grey; a vibrant grey turns teal
  final dark = b == Brightness.dark;
  // The surfaces take the palette's hue (a few percent of it, so a card still reads against the page and the text stays
  // above AA contrast), so Royal looks blue-grey, Forest green-grey, Ember warm and Ink neutral. Before, every palette
  // shared the same warm surfaces and only the small accents changed.
  final hue = HSLColor.fromColor(p.seed).hue;
  final neutral = p.key == 'ink';
  Color tone(double s, double l) => HSLColor.fromAHSL(1, hue, neutral ? 0.03 : s, l).toColor();
  final scheme = base.copyWith(
    surface: dark ? tone(0.22, 0.075) : tone(0.60, 0.975),
    surfaceContainerLowest: dark ? tone(0.22, 0.05) : const Color(0xFFFFFFFF),
    surfaceContainerLow: dark ? tone(0.22, 0.105) : tone(0.50, 0.96),
    surfaceContainer: dark ? tone(0.22, 0.135) : tone(0.45, 0.94),
    surfaceContainerHigh: dark ? tone(0.20, 0.17) : tone(0.42, 0.91),
    surfaceContainerHighest: dark ? tone(0.20, 0.21) : tone(0.40, 0.87),
    onSurface: dark ? tone(0.30, 0.94) : tone(0.45, 0.10),
    onSurfaceVariant: dark ? tone(0.18, 0.80) : tone(0.25, 0.30),
    outlineVariant: dark ? tone(0.18, 0.27) : tone(0.30, 0.80),
    // the vibrant scheme's accent is welcome, but its tinted containers (the hero card) turn neon in green and yellow palettes
    primaryContainer: dark ? base.primaryContainer : Color.lerp(base.primaryContainer, Colors.white, 0.45),
  );
  return ThemeData(
    useMaterial3: true,
    pageTransitionsTheme: const PageTransitionsTheme(builders: {TargetPlatform.android: FadeForwardsPageTransitionsBuilder()}),
    colorScheme: scheme,
    scaffoldBackgroundColor: scheme.surface,
    cardTheme: CardThemeData(elevation: 0, color: scheme.surfaceContainer, margin: EdgeInsets.zero, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20))),
    navigationBarTheme: NavigationBarThemeData(height: 64, backgroundColor: scheme.surfaceContainer, indicatorColor: scheme.primaryContainer, labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(fontSize: 12, fontWeight: s.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500, color: s.contains(WidgetState.selected) ? scheme.primary : scheme.onSurfaceVariant))),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: scheme.primary, linearTrackColor: scheme.primaryContainer),
    switchTheme: SwitchThemeData(trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? scheme.primary : null)),
    chipTheme: ChipThemeData(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
    appBarTheme: AppBarTheme(centerTitle: false, scrolledUnderElevation: 0, backgroundColor: Colors.transparent, systemOverlayStyle: overlayStyle(b, scheme.surface)),
  );
}

/// Status colours that carry meaning, kept apart from the palette so a palette never changes what "late" looks like.
class Status {
  static const Color late = Color(0xFFC1121F);
  static Color warn(Brightness b) => b == Brightness.light ? const Color(0xFF8A5300) : const Color(0xFFF2B84B);
  static Color good(Brightness b) => b == Brightness.light ? const Color(0xFF1B7A43) : const Color(0xFF6BD69A);
  static Color bad(Brightness b) => b == Brightness.light ? late : const Color(0xFFFF8A8A);
}

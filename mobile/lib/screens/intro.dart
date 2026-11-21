import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../model.dart';
import '../theme.dart';
import 'widgets.dart';

/// The first thing a new user sees: the launch mark that matches the native launch screen, then (after a beat) a short
/// intro, shown once. Both are drawn in the app's own colours and icons.
class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 96, this.progress = 1});
  final double size;

  /// 0 to 1: how much of the logo is drawn. 1 is the finished logo; the launch screen animates it from 0.
  final double progress;
  @override
  Widget build(BuildContext context) => Container(
        width: size, height: size,
        decoration: BoxDecoration(color: BrandLogo.orange, borderRadius: BorderRadius.circular(size * 0.23)),
        child: CustomPaint(painter: BrandLogo(progress)),
      );
}

/// The logo: a ring that is nearly closed (time running out) with a tick inside (the deadline met) and a dot in the
/// gap. The numbers are in a 512-unit square and match tools/make_mobile_icon.py, which draws the app icon, so the
/// icon, the launch screen and this mark are one drawing. [progress] draws it in: the ring first, then the tick, then
/// the dot.
class BrandLogo extends CustomPainter {
  const BrandLogo(this.progress);
  final double progress;

  static const orange = Color(0xFFE8552B);
  static const _white = Color(0xFFFFFAF6);
  static const _sand = Color(0xFFFFE0CD);
  static const _stroke = 44.0, _ringR = 138.0;

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 512 * 0.86;                 // 0.86 keeps the mark clear of the tile's edge, as in the icon
    canvas.translate(size.width * 0.07, size.height * 0.07);
    canvas.scale(k, k);
    double part(double from, double to) => ((progress - from) / (to - from)).clamp(0.0, 1.0);

    final ringT = Curves.easeInOut.transform(part(0.0, 0.55));
    final tickT = Curves.easeOut.transform(part(0.45, 0.85));
    final dotT = Curves.easeOutBack.transform(part(0.78, 1.0));

    final pen = Paint()..color = _white..style = PaintingStyle.stroke..strokeWidth = _stroke..strokeCap = StrokeCap.round..strokeJoin = StrokeJoin.round;
    if (ringT > 0) {
      canvas.drawArc(Rect.fromCircle(center: const Offset(256, 256), radius: _ringR), -60 * 3.141592653589793 / 180, 270 * 3.141592653589793 / 180 * ringT, false, pen);
    }
    if (tickT > 0) {
      final path = Path()..moveTo(196, 262)..lineTo(240, 306)..lineTo(322, 214);
      for (final m in path.computeMetrics()) {
        canvas.drawPath(m.extractPath(0, m.length * tickT), pen);
      }
    }
    if (dotT > 0) canvas.drawCircle(const Offset(220, 123), 20 * dotT, Paint()..color = _sand);
  }

  @override
  bool shouldRepaint(BrandLogo old) => old.progress != progress;
}

/// Shown while the app starts. It continues the native launch screen (same colours, same mark), then says what it is
/// doing while the saved data is read, GitHub is asked for anything new and the reminders are planned.
class BrandSplash extends StatelessWidget {
  const BrandSplash({super.key, this.model});
  final AppModel? model;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    // the same background as Android's own launch screen (see flutter_native_splash in pubspec.yaml), so the two read as one
    // screen instead of a flash between two colours; the palette's colours arrive with the app itself
    final launch = t.brightness == Brightness.dark ? const Color(0xFF16120F) : const Color(0xFFFFFAF6);
    return Scaffold(
      backgroundColor: launch,
      body: Center(
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: 1),
          duration: const Duration(milliseconds: 1300),
          curve: Curves.linear,
          builder: (_, p, _) {
           final v = Curves.easeOutBack.transform((p * 1.4).clamp(0.0, 1.0));   // the tile settles first, the logo draws in after
           return Column(mainAxisSize: MainAxisSize.min, children: [
            Transform.scale(scale: 0.86 + 0.14 * v, child: BrandMark(size: 104, progress: Curves.easeInOut.transform(((p - 0.1) / 0.9).clamp(0.0, 1.0)))),
            const SizedBox(height: 22),
            Opacity(opacity: (v * 1.4 - 0.4).clamp(0, 1), child: Text('Assignment Monitor', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800, letterSpacing: 0.3))),
            const SizedBox(height: 28),
            Opacity(
              opacity: (v * 2 - 1).clamp(0, 1),
              child: SizedBox(
                width: 150,
                child: Column(children: [
                  ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(minHeight: 4, color: t.colorScheme.primary, backgroundColor: t.colorScheme.surfaceContainerHighest)),
                  const SizedBox(height: 14),
                  SizedBox(
                    height: 20,
                    child: model == null
                        ? const SizedBox.shrink()
                        : ListenableBuilder(
                            listenable: model!,
                            builder: (_, _) => AnimatedSwitcher(
                              duration: const Duration(milliseconds: 260),
                              child: Text(model!.loadingStep, key: ValueKey(model!.loadingStep), textAlign: TextAlign.center, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                            ),
                          ),
                  ),
                ]),
              ),
            ),
          ]);
          },
        ),
      ),
    );
  }
}

class IntroScreen extends StatefulWidget {
  const IntroScreen({super.key, required this.model});
  final AppModel model;
  @override
  State<IntroScreen> createState() => _IntroScreenState();
}

class _IntroScreenState extends State<IntroScreen> {
  final _pages = PageController();
  int page = 0;
  static const _count = 3;

  @override
  void dispose() { _pages.dispose(); super.dispose(); }

  void _next() {
    HapticFeedback.selectionClick();
    if (page == _count - 1) {
      widget.model.finishIntro();
    } else {
      _pages.nextPage(duration: const Duration(milliseconds: 420), curve: Curves.easeOutCubic);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final last = page == _count - 1;
    return Scaffold(
      body: SafeArea(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 12, 0),
            child: Row(children: [
              const BrandMark(size: 36),
              const SizedBox(width: 10),
              Expanded(child: Text('Assignment Monitor', maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800))),
              AnimatedOpacity(
                opacity: last ? 0 : 1, duration: const Duration(milliseconds: 200),
                child: TextButton(onPressed: last ? null : widget.model.finishIntro, child: const Text('Skip')),
              ),
            ]),
          ),
          Expanded(
            child: PageView(
              controller: _pages,
              onPageChanged: (i) => setState(() => page = i),
              children: const [
                _Slide(art: _CountdownArt(), title: 'Never miss a deadline', body: 'Every assignment counts down on your phone, with reminders you choose: a day before, three hours before, an hour before.'),
                _Slide(art: _AttendanceArt(), title: 'Know how many classes you can miss', body: 'Attendance shows exactly how many hours you can still skip and stay above the minimum, class by class and for the whole semester.'),
                _Slide(art: _PrivacyArt(), title: 'Your data stays yours', body: "Sign in once with your university login. It stays in this phone's secure storage and goes only to the university portal, never through a server of ours. You can also let your own private GitHub repository keep checking while the phone is off."),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
            child: Row(children: [
              Row(children: [
                for (var i = 0; i < _count; i++)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 260), curve: Curves.easeOutCubic,
                    margin: const EdgeInsets.only(right: 6),
                    width: i == page ? 26 : 8, height: 8,
                    decoration: BoxDecoration(color: i == page ? t.colorScheme.primary : t.colorScheme.outlineVariant, borderRadius: BorderRadius.circular(99)),
                  ),
              ]),
              const Spacer(),
              FilledButton.icon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 52), padding: const EdgeInsets.symmetric(horizontal: 24)),
                onPressed: _next,
                iconAlignment: IconAlignment.end,
                icon: Icon(last ? LucideIcons.check : LucideIcons.arrowRight, size: 20),
                label: Text(last ? 'Get started' : 'Next'),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Slide extends StatelessWidget {
  const _Slide({required this.art, required this.title, required this.body});
  final Widget art;
  final String title, body;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(child: Center(child: Reveal(index: 0, child: art))),
        Reveal(index: 1, child: Text(title, style: t.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, height: 1.1))),
        const SizedBox(height: 12),
        Reveal(index: 2, child: Text(body, style: t.textTheme.bodyLarge?.copyWith(color: t.colorScheme.onSurfaceVariant, height: 1.4))),
        const SizedBox(height: 12),
      ]),
    );
  }
}

// ----------------------------------------------------------------------------------------------- the three pictures
/// A tile like the Today hero, with a countdown, so the first slide shows what the app will look like.
class _CountdownArt extends StatelessWidget {
  const _CountdownArt();
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return SizedBox(width: 300, child: Column(mainAxisSize: MainAxisSize.min, children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: t.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(28)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Pill('DUE SOON', color: t.colorScheme.onPrimaryContainer),
            const Spacer(),
            Flexible(child: Text('8h 4m', maxLines: 1, style: t.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer))),
          ]),
          const SizedBox(height: 14),
          Text('Usability test report', style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700, color: t.colorScheme.onPrimaryContainer)),
          Text('Human Computer Interaction', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.85))),
        ]),
      ),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: t.colorScheme.surfaceContainer, borderRadius: BorderRadius.circular(22)),
        child: Row(children: [
          Icon(LucideIcons.bellRing, size: 20, color: t.colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(child: Text('Reminder: due in 3 hours', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600))),
          Text('Snooze', style: t.textTheme.labelLarge?.copyWith(color: t.colorScheme.primary, fontWeight: FontWeight.w700)),
        ]),
      ),
    ]));
  }
}

class _AttendanceArt extends StatelessWidget {
  const _AttendanceArt();
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    return Container(
      width: 300, padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(color: t.colorScheme.surfaceContainer, borderRadius: BorderRadius.circular(28)),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        SizedBox(width: 124, height: 124, child: Stack(alignment: Alignment.center, children: [
          const SizedBox.expand(child: CircularProgressIndicator(value: 0.84, strokeWidth: 12, strokeCap: StrokeCap.round, color: Color(0xFF6BD69A), backgroundColor: Color(0x266BD69A))),
          Column(mainAxisSize: MainAxisSize.min, children: [
            Text('84%', style: t.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
            Text('attendance', style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
          ]),
        ])),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(color: Status.good(b).withValues(alpha: 0.14), borderRadius: BorderRadius.circular(16)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(LucideIcons.circleCheck, size: 18, color: Status.good(b)),
            const SizedBox(width: 8),
            Flexible(child: Text('You can miss 4.3 h more', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700, color: Status.good(b)))),
          ]),
        ),
      ]),
    );
  }
}

class _PrivacyArt extends StatelessWidget {
  const _PrivacyArt();
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    Widget node(IconData i, String label, {bool accent = false}) => Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(color: accent ? t.colorScheme.primary : t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(20)),
            child: Icon(i, size: 28, color: accent ? t.colorScheme.onPrimary : t.colorScheme.onSurface),
          ),
          const SizedBox(height: 8),
          Text(label, style: t.textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w600)),
        ]);
    Widget link() => Padding(padding: const EdgeInsets.only(bottom: 24), child: Icon(LucideIcons.arrowRight, size: 20, color: t.colorScheme.onSurfaceVariant));
    return Column(mainAxisSize: MainAxisSize.min, children: [
      FittedBox(fit: BoxFit.scaleDown, child: Row(mainAxisSize: MainAxisSize.min, children: [
        node(LucideIcons.graduationCap, 'University portal'),
        const SizedBox(width: 14), link(), const SizedBox(width: 14),
        node(LucideIcons.smartphone, 'This phone', accent: true),
        const SizedBox(width: 14), link(), const SizedBox(width: 14),
        node(LucideIcons.lock, 'Your private repo'),
      ])),
      const SizedBox(height: 22),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(color: t.colorScheme.surfaceContainer, borderRadius: BorderRadius.circular(16)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(LucideIcons.keyRound, size: 18, color: t.colorScheme.onSurfaceVariant),
          const SizedBox(width: 8),
          Flexible(child: Text('Your login stays on this phone', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600))),
        ]),
      ),
    ]);
  }
}

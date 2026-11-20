import 'package:flutter/material.dart';

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});
  final String text;
  final String? trailing;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(children: [
        Text(text, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
        const Spacer(),
        if (trailing != null) Text(trailing!, style: t.textTheme.labelLarge?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      ]),
    );
  }
}

class Muted extends StatelessWidget {
  const Muted(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Text(text, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
      );
}

class AttentionRow extends StatelessWidget {
  const AttentionRow({super.key, required this.icon, required this.color, required this.title, required this.detail, this.onTap});
  final IconData icon;
  final Color color;
  final String title, detail;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => ListTile(
        onTap: onTap,
        leading: Icon(icon, color: color),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(detail),
      );
}

/// A tinted pill used for time left, status and filters.
class Pill extends StatelessWidget {
  const Pill(this.text, {super.key, this.color});
  final String text;
  final Color? color;
  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.onSurfaceVariant;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99), border: Border.all(color: c.withValues(alpha: 0.25))),
      child: Text(text, style: Theme.of(context).textTheme.labelMedium?.copyWith(color: c, fontWeight: FontWeight.w600)),
    );
  }
}

/// A stable, muted colour per course (low saturation, so it marks a subject without competing with the status colours).
const _courseColors = [
  Color(0xFFB46A55), Color(0xFF7E9275), Color(0xFF6F86A3), Color(0xFFB39A5C),
  Color(0xFF8C7089), Color(0xFF5F8A89), Color(0xFF8A8478), Color(0xFFA4766F),
];
Color courseColor(String name) => _courseColors[name.codeUnits.fold<int>(7, (a, b) => (a * 31 + b) & 0x7fffffff) % _courseColors.length];

/// Fades and lifts its child in; later items (higher [index]) arrive a moment after the earlier ones.
class Reveal extends StatelessWidget {
  const Reveal({super.key, required this.index, required this.child});
  final int index;
  final Widget child;
  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 320 + index.clamp(0, 8) * 70),
      curve: Curves.easeOutCubic,
      builder: (_, v, c) => Opacity(opacity: v, child: Transform.translate(offset: Offset(0, (1 - v) * 16), child: c)),
      child: child,
    );
  }
}

/// A calm empty state: an icon, a line, and optionally what to do next.
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, this.hint});
  final IconData icon;
  final String title;
  final String? hint;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 72, height: 72, decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, shape: BoxShape.circle), child: Icon(icon, size: 32, color: t.colorScheme.onSurfaceVariant)),
          const SizedBox(height: 16),
          Text(title, textAlign: TextAlign.center, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          if (hint != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(hint!, textAlign: TextAlign.center, style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant))),
        ]),
      ),
    );
  }
}

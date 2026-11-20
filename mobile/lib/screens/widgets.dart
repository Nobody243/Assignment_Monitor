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
        Flexible(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700))),
        const SizedBox(width: 12),
        if (trailing != null) Expanded(child: Text(trailing!, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.end, style: t.textTheme.labelLarge?.copyWith(color: t.colorScheme.onSurfaceVariant))) else const Spacer(),
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

/// The one page transition for secondary pages: the new page slides in a little from the right while fading.
Route<T> slideRoute<T>(Widget page) => PageRouteBuilder<T>(
      transitionDuration: const Duration(milliseconds: 320),
      reverseTransitionDuration: const Duration(milliseconds: 240),
      pageBuilder: (_, _, _) => page,
      transitionsBuilder: (_, a, sa, child) {
        final slide = Tween(begin: const Offset(0.10, 0), end: Offset.zero).chain(CurveTween(curve: Curves.easeOutCubic));
        final under = Tween(begin: Offset.zero, end: const Offset(-0.04, 0)).chain(CurveTween(curve: Curves.easeOutCubic));
        return SlideTransition(position: under.animate(sa), child: FadeTransition(opacity: CurvedAnimation(parent: a, curve: Curves.easeOut), child: SlideTransition(position: slide.animate(a), child: child)));
      },
    );

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

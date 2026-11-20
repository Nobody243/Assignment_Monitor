import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import 'data.dart' show Clock;
import 'model.dart';
import 'screens/attendance.dart';
import 'data.dart' show Summary;
import 'screens/more.dart';
import 'screens/settings.dart';
import 'screens/signin.dart';
import 'screens/today.dart';
import 'screens/work.dart';
import 'theme.dart';
import 'logic.dart' show agoLabel;
import 'reminders.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Reminders.init();
  runApp(const AssignmentMonitorApp());
}

class AssignmentMonitorApp extends StatefulWidget {
  const AssignmentMonitorApp({super.key});
  @override
  State<AssignmentMonitorApp> createState() => _AppState();
}

class _AppState extends State<AssignmentMonitorApp> with WidgetsBindingObserver {
  final prefs = Prefs();
  late final model = AppModel(prefs);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    prefs.addListener(() => setState(() {}));
    model.addListener(() => setState(() {}));
    model.start();
  }

  @override
  void dispose() { WidgetsBinding.instance.removeObserver(this); super.dispose(); }

  /// Coming back to the app is the moment to look for a newer summary, and to pick up Snooze / Done tapped on a notification.
  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed && model.phase == Phase.ready && !model.demo) {
      prefs.load().then((_) => model.refresh());
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assignment Monitor',
      debugShowCheckedModeBanner: false,
      themeMode: prefs.mode,
      theme: buildTheme(prefs.palette, Brightness.light),
      darkTheme: buildTheme(prefs.palette, Brightness.dark),
      home: switch (model.phase) {
        Phase.loading => const Scaffold(body: Center(child: CircularProgressIndicator())),
        Phase.ready => Shell(model: model, prefs: prefs),
        _ => SignInScreen(model: model),
      },
    );
  }
}

class Shell extends StatefulWidget {
  const Shell({super.key, required this.model, required this.prefs});
  final AppModel model;
  final Prefs prefs;
  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> with SingleTickerProviderStateMixin {
  int tab = 0;
  late Clock clock = widget.model.clock;
  Timer? tick;
  late final AnimationController _menu = AnimationController(vsync: this, duration: const Duration(milliseconds: 380));
  late final Animation<double> _t = CurvedAnimation(parent: _menu, curve: Curves.easeOutCubic, reverseCurve: Curves.easeInCubic);

  static const _titles = ['Today', 'Work', 'Attendance', 'Exams'];

  @override
  void initState() {
    super.initState();
    tick = Timer.periodic(const Duration(seconds: 30), (_) => setState(() {}));   // the countdowns move
  }

  @override
  void dispose() { tick?.cancel(); _menu.dispose(); super.dispose(); }

  void goto(int i) => setState(() => tab = i);
  void _toggleMenu() => _menu.isDismissed ? _menu.forward() : _menu.reverse();

  /// Menu rows: 0..3 are the bottom-bar screens, the rest open over them.
  Future<void> _pick(int i, Summary s, DateTime now) async {
    if (i <= 3) {
      goto(i);
      _menu.reverse();
      return;
    }
    await _menu.reverse();
    if (!mounted) return;
    switch (i) {
      case 4: openPage(context, 'Timetable', TimetablePage(summary: s, now: now));
      case 5: openPage(context, 'Results and GPA', ResultsPage(summary: s));
      case 6: openPage(context, 'Settings', SettingsHub(summary: s, prefs: widget.prefs, model: widget.model));
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.model, s = m.summary!, now = clock.now(), t = Theme.of(context);
    final w = MediaQuery.of(context).size.width;
    final todo = s.work.where((x) => x.todo && x.open && !widget.prefs.done.contains(x.id)).length;
    return PopScope(
      canPop: _menu.isDismissed,
      onPopInvokedWithResult: (didPop, _) { if (!didPop) _menu.reverse(); },
      child: ColoredBox(
        color: t.colorScheme.surfaceContainerLowest,
        child: Stack(children: [
          // the menu sits underneath; the app slides aside to uncover it
          _SideMenu(summary: s, model: m, selected: tab, todo: todo, progress: _t, onPick: (i) => _pick(i, s, now), onSignOut: () { _menu.reverse(); m.signOut(); }),
          AnimatedBuilder(
            animation: _t,
            builder: (context, child) {
              final v = _t.value;
              return Transform(
                alignment: Alignment.centerLeft,
                transform: Matrix4.identity()..translateByDouble(w * 0.72 * v, 0, 0, 1)..scaleByDouble(1 - 0.10 * v, 1 - 0.10 * v, 1, 1),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(32 * v),
                  child: Stack(children: [
                    child!,
                    if (v > 0) Positioned.fill(child: GestureDetector(behavior: HitTestBehavior.opaque, onTap: _menu.reverse, child: ColoredBox(color: Colors.black.withValues(alpha: 0.10 * v)))),
                  ]),
                ),
              );
            },
            child: GestureDetector(
              // a swipe that starts at the left edge pulls the menu out (rows inside the app keep their own swipes)
              onHorizontalDragUpdate: (d) { if (d.localPosition.dx < 28 || !_menu.isDismissed) _menu.value += d.delta.dx / (w * 0.72); },
              onHorizontalDragEnd: (d) { if (_menu.isDismissed) return; (_menu.value > 0.45 || d.primaryVelocity! > 400) && d.primaryVelocity! > -400 ? _menu.forward() : _menu.reverse(); },
              child: _body(m, s, now, todo),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _body(AppModel m, Summary s, DateTime now, int todo) {
    final t = Theme.of(context);
    final pages = [
      TodayScreen(summary: s, now: now, prefs: widget.prefs, onOpenWork: () => goto(1), onOpenAttendance: () => goto(2)),
      WorkScreen(summary: s, now: now, prefs: widget.prefs),
      AttendanceScreen(summary: s),
      ExamsPage(summary: s, now: now),
    ];
    final stale = !m.demo && (m.age?.inHours ?? 0) >= 24;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(icon: AnimatedIcon(icon: AnimatedIcons.menu_arrow, progress: _t), tooltip: 'Menu', onPressed: _toggleMenu),
        title: AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          transitionBuilder: (c, a) => FadeTransition(opacity: a, child: SlideTransition(position: Tween(begin: const Offset(0, 0.3), end: Offset.zero).animate(a), child: c)),
          child: Text(_titles[tab], key: ValueKey(tab), style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
        actions: [
          if (!m.demo) m.refreshing
              ? const Padding(padding: EdgeInsets.all(14), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
              : IconButton(icon: const Icon(Icons.sync), tooltip: 'Check for new data', onPressed: m.refresh),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          if (!m.demo && (m.error != null || stale)) _Banner(model: m),
          Expanded(
            child: RefreshIndicator(
              onRefresh: m.refresh,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 260),
                switchInCurve: Curves.easeOutCubic,
                transitionBuilder: (c, a) => FadeTransition(opacity: a, child: SlideTransition(position: Tween(begin: const Offset(0, 0.02), end: Offset.zero).animate(a), child: c)),
                child: KeyedSubtree(key: ValueKey(tab), child: pages[tab]),
              ),
            ),
          ),
        ]),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: Container(
          height: 68,
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: t.colorScheme.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(99),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: t.brightness == Brightness.dark ? 0.45 : 0.12), blurRadius: 24, offset: const Offset(0, 8))],
          ),
          child: Row(children: [
            _NavItem(icon: Icons.today_outlined, selectedIcon: Icons.today, label: 'Today', selected: tab == 0, onTap: () => goto(0)),
            _NavItem(icon: Icons.checklist_outlined, selectedIcon: Icons.checklist, label: 'Work', selected: tab == 1, badge: todo, onTap: () => goto(1)),
            _NavItem(icon: Icons.event_available_outlined, selectedIcon: Icons.event_available, label: 'Attendance', selected: tab == 2, onTap: () => goto(2)),
            _NavItem(icon: Icons.school_outlined, selectedIcon: Icons.school, label: 'Exams', selected: tab == 3, onTap: () => goto(3)),
          ]),
        ),
      ),
    );
  }
}

/// The menu under the app: profile, the screens, then the secondary pages, and Sign out at the bottom.
/// Rows slide in one after another as the app moves aside.
class _SideMenu extends StatelessWidget {
  const _SideMenu({required this.summary, required this.model, required this.selected, required this.todo, required this.progress, required this.onPick, required this.onSignOut});
  final Summary summary;
  final AppModel model;
  final int selected, todo;
  final Animation<double> progress;
  final void Function(int) onPick;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final w = MediaQuery.of(context).size.width;
    final items = <(int, IconData, IconData, String)>[
      (0, Icons.today_outlined, Icons.today, 'Today'),
      (1, Icons.checklist_outlined, Icons.checklist, todo > 0 ? 'Work  ·  $todo to do' : 'Work'),
      (2, Icons.event_available_outlined, Icons.event_available, 'Attendance'),
      (3, Icons.school_outlined, Icons.school, 'Exams'),
      (4, Icons.calendar_view_week_outlined, Icons.calendar_view_week, 'Timetable'),
      (5, Icons.calculate_outlined, Icons.calculate, 'Results and GPA'),
      (6, Icons.tune, Icons.tune, 'Settings'),
    ];
    // row i is fully in by the time the app has moved (0.25 + 0.06 i) of the way; it starts at 0.06 i
    Widget staggered(int i, Widget child) => AnimatedBuilder(
          animation: progress,
          builder: (_, c) {
            final v = Interval((0.06 * i).clamp(0.0, 0.6), (0.4 + 0.06 * i).clamp(0.0, 1.0), curve: Curves.easeOutCubic).transform(progress.value);
            return Opacity(opacity: v, child: Transform.translate(offset: Offset(-24 * (1 - v), 0), child: c));
          },
          child: child,
        );
    return SafeArea(
      child: SizedBox(
        width: w * 0.74,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 24, 8, 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            staggered(0, Row(children: [
              CircleAvatar(radius: 28, backgroundColor: t.colorScheme.primaryContainer,
                  child: Text(summary.studentName.trim().isEmpty ? '?' : summary.studentName.trim()[0].toUpperCase(), style: t.textTheme.titleLarge?.copyWith(color: t.colorScheme.onPrimaryContainer, fontWeight: FontWeight.w800))),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(summary.studentName, maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                Text(model.demo ? 'Demo data' : [summary.semester, if (model.age != null) 'read ${agoLabel(model.age!)}'].where((e) => e.isNotEmpty).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ])),
            ])),
            const SizedBox(height: 28),
            for (final (i, it) in items.indexed)
              staggered(i + 1, Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: _MenuRow(icon: selected == it.$1 ? it.$3 : it.$2, label: it.$4, selected: it.$1 <= 3 && selected == it.$1, onTap: () => onPick(it.$1)),
              )),
            const Spacer(),
            staggered(items.length + 1, Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _MenuRow(icon: Icons.logout, label: model.demo ? 'Leave the demo' : 'Sign out', selected: false, onTap: onSignOut),
              Padding(padding: const EdgeInsets.fromLTRB(16, 8, 8, 0), child: Text('Your portal password never touches this phone.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant))),
            ])),
          ]),
        ),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({required this.icon, required this.label, required this.selected, required this.onTap});
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final fg = selected ? t.colorScheme.onPrimaryContainer : t.colorScheme.onSurface;
    return Material(
      color: selected ? t.colorScheme.primaryContainer : Colors.transparent,
      borderRadius: BorderRadius.circular(99),
      child: InkWell(
        borderRadius: BorderRadius.circular(99), onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(children: [
            Icon(icon, size: 22, color: fg),
            const SizedBox(width: 14),
            Expanded(child: Text(label, style: t.textTheme.titleSmall?.copyWith(color: fg, fontWeight: selected ? FontWeight.w800 : FontWeight.w600))),
          ]),
        ),
      ),
    );
  }
}

/// Said plainly when the phone cannot be sure the numbers are current: offline, or the repository has gone quiet.
class _Banner extends StatelessWidget {
  const _Banner({required this.model});
  final AppModel model;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final made = DateTime.now().difference(model.summary!.generatedAt);
    final text = model.error != null
        ? '${model.error} Showing what was read ${model.fetchedAt == null ? 'earlier' : agoLabel(model.age!)}.'
        : 'The last cloud check was ${agoLabel(made)}. Check that cloud checks are still on.';
    return Material(
      color: t.colorScheme.errorContainer,
      child: InkWell(
        onTap: model.refresh,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(children: [
            Icon(Icons.cloud_off_outlined, size: 18, color: t.colorScheme.onErrorContainer),
            const SizedBox(width: 10),
            Expanded(child: Text(text, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onErrorContainer))),
          ]),
        ),
      ),
    );
  }
}

/// One slot of the floating bar: the selected one grows into a pill with its name; the icon pops and the name slides in.
class _NavItem extends StatelessWidget {
  const _NavItem({required this.icon, required this.selectedIcon, required this.label, required this.selected, required this.onTap, this.badge = 0});
  final IconData icon, selectedIcon;
  final String label;
  final bool selected;
  final int badge;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Expanded(
      flex: selected ? 3 : 1,
      child: Semantics(
        button: true, selected: selected, label: label,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () { HapticFeedback.selectionClick(); onTap(); },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 280), curve: Curves.easeOutBack,
            decoration: BoxDecoration(color: selected ? t.colorScheme.primary : Colors.transparent, borderRadius: BorderRadius.circular(99)),
            alignment: Alignment.center,
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              TweenAnimationBuilder<double>(
                key: ValueKey(selected),
                tween: Tween(begin: selected ? 0.7 : 1.0, end: 1.0),
                duration: const Duration(milliseconds: 320), curve: Curves.easeOutBack,
                builder: (_, v, c) => Transform.scale(scale: v, child: c),
                child: Badge(isLabelVisible: badge > 0 && !selected, label: Text('$badge'), child: Icon(selected ? selectedIcon : icon, size: 24, color: selected ? t.colorScheme.onPrimary : t.colorScheme.onSurfaceVariant)),
              ),
              AnimatedSize(
                duration: const Duration(milliseconds: 280), curve: Curves.easeOutCubic,
                child: selected
                    ? Padding(padding: const EdgeInsets.only(left: 6), child: Text(label, maxLines: 1, softWrap: false, overflow: TextOverflow.fade, style: t.textTheme.labelLarge?.copyWith(color: t.colorScheme.onPrimary, fontWeight: FontWeight.w700)))
                    : const SizedBox.shrink(),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

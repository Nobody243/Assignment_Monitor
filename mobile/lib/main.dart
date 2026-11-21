import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback, SystemUiOverlayStyle;
import 'package:lucide_icons_flutter/lucide_icons.dart';

import 'data.dart' show Clock;
import 'model.dart';
import 'screens/announcements.dart';
import 'screens/attendance.dart';
import 'screens/first_run.dart';
import 'screens/cloud_setup_screens.dart' show CloudSetupWizard;
import 'screens/intro.dart';
import 'screens/lectures.dart';
import 'screens/lock_screen.dart';
import 'data.dart' show Summary;
import 'screens/more.dart';
import 'screens/results.dart';
import 'screens/settings.dart';
import 'screens/signin.dart';
import 'screens/timetable.dart';
import 'screens/today.dart';
import 'screens/work.dart';
import 'theme.dart';
import 'logic.dart' show agoLabel;
import 'background.dart';
import 'reminders.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // The first frame comes first: until it is drawn Android keeps showing its still launch screen, so nothing slow or
  // stuck below may hold it up. Reminders and the background check set themselves up beside the splash, each with a limit.
  runApp(const AssignmentMonitorApp());
  unawaited(_setUpPlugins());
}

Future<void> _setUpPlugins() async {
  try { await Reminders.init().timeout(const Duration(seconds: 15)); } catch (e) { debugPrint('reminders: $e'); }
  // keeps the two-hourly check in step with the setting (Android only)
  try { await BackgroundCheck.applySaved().timeout(const Duration(seconds: 15)); } catch (e) { debugPrint('background: $e'); }
}

/// The data section each screen shows, for its own refresh: Today (0) and anything unlisted refresh everything.
const sectionOfTab = <int, String>{1: 'assignments', 2: 'attendance', 3: 'exams', 4: 'announcements', 5: 'timetable', 6: 'results', 7: 'lectures'};

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
    if (s == AppLifecycleState.paused) model.noteLeft(DateTime.now());
    if (s == AppLifecycleState.resumed) model.noteBack(DateTime.now());
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
      // screens without an app bar (sign-in, splash, lock) also get a status bar that can be read on their page
      builder: (context, child) {
        final th = Theme.of(context);
        return AnnotatedRegion<SystemUiOverlayStyle>(value: overlayStyle(th.brightness, th.colorScheme.surface), child: child ?? const SizedBox.shrink());
      },
      home: AnimatedSwitcher(
        duration: const Duration(milliseconds: 420),
        switchInCurve: Curves.easeOut,
        child: model.locked && model.phase != Phase.loading ? LockScreen(key: const ValueKey('lock'), model: model) : switch (model.phase) {
          Phase.loading => BrandSplash(key: const ValueKey('splash'), model: model),
          Phase.ready => Shell(key: const ValueKey('shell'), model: model, prefs: prefs),
          Phase.signedOut when !model.introSeen => IntroScreen(key: const ValueKey('intro'), model: model),
          _ => SignInScreen(key: const ValueKey('signin'), model: model),
        },
      ),
    );
  }
}

/// How far the app slides aside to show the menu: most of the width on a phone, a fixed width on anything wider.
double menuShift(double width) => (width * 0.72).clamp(0.0, 340.0);

/// The widest the screens grow. Wider than this (a tablet, a phone on its side) the content stays a readable column in the
/// middle instead of stretching edge to edge.
const maxContentWidth = 680.0;

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
  Animation<double> get _t => _menu;

  /// Pull-to-refresh and the refresh button: a screen reads only its own part of the portal again; Today reads everything.
  Future<void> _refreshHere() {
    final s = sectionOfTab[tab];
    return s == null ? widget.model.refresh() : widget.model.refreshSection(s);
  }

  static const _titles = ['Today', 'Assignments', 'Attendance', 'Exams', 'Announcements', 'Timetable', 'Results & GPA', 'Lectures', 'Settings'];
  int _dir = 1;   // which way the last tab change went, so the new screen arrives from that side

  @override
  void initState() {
    super.initState();
    tick = Timer.periodic(const Duration(seconds: 30), (_) => setState(() {}));   // the countdowns move
    // the first time there is real data: reminder setup, then the lock offer (once)
    if (widget.model.firstRunDue) WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) runFirstRun(context, widget.model); });
  }

  @override
  void dispose() { tick?.cancel(); _menu.dispose(); super.dispose(); }

  void goto(int i) => setState(() { _dir = i >= tab ? 1 : -1; tab = i; });

  /// Settles the menu open or shut. `fling` runs a spring from wherever the menu is right now, keeps the speed of the
  /// finger, can be interrupted by the next tap or drag, and always ends exactly on 0 or 1.
  TickerFuture _settle(bool open, [double velocity = 0]) => _menu.fling(velocity: open ? (velocity < 1.6 ? 1.6 : velocity) : (velocity > -1.6 ? -1.6 : velocity));
  /// A tap on the menu button reverses whatever the menu is doing: opening becomes closing and the other way round.
  void _toggleMenu() => _settle(!(_menu.isAnimating ? _menu.velocity > 0 : _menu.value >= 0.5));

  void _dragUpdate(DragUpdateDetails d, double w) { _menu.stop(); _menu.value = (_menu.value + d.delta.dx / w).clamp(0.0, 1.0); }
  void _dragEnd(DragEndDetails d, double w) {
    final v = (d.primaryVelocity ?? 0) / w;   // menu-widths per second
    _settle(v.abs() > 0.8 ? v > 0 : _menu.value > 0.5, v);
  }

  /// Every menu row is a section of the app: the bar and the menu stay, only the screen changes.
  void _pick(int i) {
    goto(i);
    _settle(false);
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.model, s = m.summary!, now = clock.now(), t = Theme.of(context);
    final w = MediaQuery.of(context).size.width;
    final todo = s.work.where((x) => x.todo && x.open && !widget.prefs.done.contains(x.id)).length;
    return PopScope(
      canPop: tab == 0 && _menu.value == 0 && !_menu.isAnimating,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop) return;
        if (_menu.value > 0 || _menu.isAnimating) { _settle(false); } else { goto(0); }
      },
      child: ColoredBox(
        color: t.colorScheme.surfaceContainerLowest,
        child: Stack(children: [
          // the menu sits underneath; the app slides aside to uncover it
          _SideMenu(summary: s, model: m, selected: tab, todo: todo, progress: _t, onPick: _pick, onSignOut: () { _settle(false); m.signOut(); }),
          AnimatedBuilder(
            animation: _menu,
            builder: (context, child) {
              final v = _menu.value;
              return Transform(
                alignment: Alignment.centerLeft,
                transform: Matrix4.identity()..translateByDouble(menuShift(w) * v, 0, 0, 1)..scaleByDouble(1 - 0.10 * v, 1 - 0.10 * v, 1, 1),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(32 * v),
                  child: Stack(children: [
                    child!,
                    // open (or opening): tapping or dragging the app closes the menu
                    if (v > 0) Positioned.fill(child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () => _settle(false),
                      onHorizontalDragUpdate: (d) => _dragUpdate(d, menuShift(w)),
                      onHorizontalDragEnd: (d) => _dragEnd(d, menuShift(w)),
                      child: ColoredBox(color: Colors.black.withValues(alpha: 0.10 * v)),
                    ))
                    // closed: only a thin strip on the left edge pulls the menu out, so rows that swipe keep their gestures
                    else Positioned(left: 0, top: 0, bottom: 0, width: 22, child: GestureDetector(
                      behavior: HitTestBehavior.translucent,
                      onHorizontalDragUpdate: (d) => _dragUpdate(d, menuShift(w)),
                      onHorizontalDragEnd: (d) => _dragEnd(d, menuShift(w)),
                    )),
                  ]),
                ),
              );
            },
            child: _body(m, s, now, todo),
          ),
        ]),
      ),
    );
  }

  Widget _body(AppModel m, Summary s, DateTime now, int todo) {
    final t = Theme.of(context);
    final pages = [
      TodayScreen(summary: s, now: now, prefs: widget.prefs, onOpenWork: () => goto(1), onOpenAttendance: () => goto(2), onOpenAnnouncements: () => goto(4)),
      WorkScreen(summary: s, now: now, prefs: widget.prefs, model: m),
      AttendanceScreen(summary: s),
      ExamsPage(summary: s, now: now),
      AnnouncementsScreen(summary: s, prefs: widget.prefs, now: now),
      TimetableScreen(summary: s, now: now),
      ResultsPage(summary: s),
      LecturesScreen(summary: s, model: m),
      SettingsHub(summary: s, prefs: widget.prefs, model: m),
    ];
    final stale = !m.demo && (m.age?.inHours ?? 0) >= 24;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(icon: AnimatedIcon(icon: AnimatedIcons.menu_arrow, progress: _t), tooltip: 'Menu', onPressed: _toggleMenu),
        title: AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          layoutBuilder: (current, previous) => Stack(alignment: Alignment.centerLeft, children: [...previous, ?current]),
          transitionBuilder: (c, a) => FadeTransition(opacity: a, child: c),
          child: Text(_titles[tab], key: ValueKey(tab), style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
        actions: [
          if (!m.demo) m.refreshing
              ? const Padding(padding: EdgeInsets.all(14), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
              : IconButton(icon: const Icon(LucideIcons.refreshCw, size: 20), tooltip: sectionOfTab.containsKey(tab) ? 'Check for new ${_titles[tab].toLowerCase()}' : 'Check for new data', onPressed: _refreshHere),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          if (!m.demo && m.refreshing && m.portalMode) _SyncBar(model: m),
          if (!m.demo && (m.error != null || stale || (m.portalMode && m.syncSkipped.isNotEmpty))) _Banner(model: m),
          if (m.offerCloud) _CloudOffer(model: m),
          Expanded(
            child: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: maxContentWidth), child: RefreshIndicator(
              onRefresh: _refreshHere,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 320),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                layoutBuilder: (current, previous) => Stack(alignment: Alignment.topCenter, children: [...previous, ?current]),
                transitionBuilder: (c, a) {
                  final mine = (c.key as ValueKey<int>).value;
                  final dx = mine == tab ? 0.06 * _dir : -0.06 * _dir;   // arriving from one side, leaving to the other
                  return FadeTransition(opacity: a, child: SlideTransition(position: Tween(begin: Offset(dx, 0), end: Offset.zero).animate(a), child: c));
                },
                child: KeyedSubtree(key: ValueKey(tab), child: pages[tab]),
              ),
            ))),
          ),
        ]),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: Center(heightFactor: 1, child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 480), child: Container(
          height: 68,
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: t.colorScheme.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(99),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: t.brightness == Brightness.dark ? 0.45 : 0.12), blurRadius: 24, offset: const Offset(0, 8))],
          ),
          child: Row(children: [
            _NavItem(icon: LucideIcons.layoutDashboard, label: 'Today', selected: tab == 0, onTap: () => goto(0)),
            _NavItem(icon: LucideIcons.clipboardList, label: 'Assignments', selected: tab == 1, badge: todo, onTap: () => goto(1)),
            _NavItem(icon: LucideIcons.userCheck, label: 'Attendance', selected: tab == 2, onTap: () => goto(2)),
            _NavItem(icon: LucideIcons.graduationCap, label: 'Exams', selected: tab == 3, onTap: () => goto(3)),
          ]),
        ))),
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
    final items = <(int, IconData, String)>[
      (0, LucideIcons.layoutDashboard, 'Today'),
      (1, LucideIcons.clipboardList, 'Assignments'),
      (2, LucideIcons.userCheck, 'Attendance'),
      (3, LucideIcons.graduationCap, 'Exams'),
      (4, LucideIcons.megaphone, 'Announcements'),
      (5, LucideIcons.calendarRange, 'Timetable'),
      (6, LucideIcons.chartNoAxesColumn, 'Results & GPA'),
      (7, LucideIcons.bookOpen, 'Lectures'),
      (8, LucideIcons.settings, 'Settings'),
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
        width: menuShift(w) + 14,
        // scrollable, so a large text size or a short screen never pushes Sign out off the bottom
        child: LayoutBuilder(builder: (context, box) => SingleChildScrollView(child: ConstrainedBox(constraints: BoxConstraints(minHeight: box.maxHeight), child: IntrinsicHeight(child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 24, 8, 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            staggered(0, Row(children: [
              CircleAvatar(radius: 28, backgroundColor: t.colorScheme.primaryContainer,
                  child: Text(summary.studentName.trim().isEmpty ? '?' : summary.studentName.trim()[0].toUpperCase(), style: t.textTheme.titleLarge?.copyWith(color: t.colorScheme.onPrimaryContainer, fontWeight: FontWeight.w800))),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(summary.studentName, maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                Text(model.demo ? 'Demo data' : [summary.semester, if (model.age != null) 'updated ${agoLabel(model.age!)}'].where((e) => e.isNotEmpty).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ])),
            ])),
            const SizedBox(height: 28),
            for (final (i, it) in items.indexed)
              staggered(i + 1, Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: _MenuRow(icon: it.$2, label: it.$3, count: it.$1 == 1 ? todo : it.$1 == 4 ? model.newAnnouncements : 0, selected: selected == it.$1, onTap: () => onPick(it.$1)),
              )),
            const Spacer(),
            staggered(items.length + 1, Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _MenuRow(icon: LucideIcons.logOut, label: model.demo ? 'Leave the demo' : 'Sign out', selected: false, onTap: onSignOut),
              Padding(padding: const EdgeInsets.fromLTRB(16, 8, 8, 0), child: Text('Your portal password is never stored on this phone.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant))),
            ])),
          ]),
        ))))),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({required this.icon, required this.label, required this.selected, required this.onTap, this.count = 0});
  final int count;
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
            if (count > 0) Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3), decoration: BoxDecoration(color: fg.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(99)), child: Text('$count', style: t.textTheme.labelMedium?.copyWith(color: fg, fontWeight: FontWeight.w800))),
          ]),
        ),
      ),
    );
  }
}

/// Said plainly when the phone cannot be sure the numbers are current: offline, or the repository has gone quiet.
/// A progress bar under the app bar while the portal is being read, with what it is doing and how far it has got, so a check
/// that is still going can be told from one that has finished.
class _SyncBar extends StatelessWidget {
  const _SyncBar({required this.model});
  final AppModel model;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final n = model.syncTotal, d = model.syncDone;
    final step = model.syncStep.isEmpty ? 'Working' : model.syncStep;
    return Material(
      color: t.colorScheme.surfaceContainer,
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        LinearProgressIndicator(value: n == 0 ? null : ((d + 0.35) / n).clamp(0.0, 1.0), minHeight: 3, color: t.colorScheme.primary, backgroundColor: t.colorScheme.primaryContainer),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: Row(children: [
            Expanded(child: Text(n == 0 ? step : '$step  ·  ${(d + 1).clamp(1, n)} of $n', maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant))),
          ]),
        ),
      ]),
    );
  }
}

/// Offered once, after the portal works: let GitHub also check while the phone is off. The portal login is reused, not asked for again.
class _CloudOffer extends StatelessWidget {
  const _CloudOffer({required this.model});
  final AppModel model;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Material(
      color: t.colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
        child: Row(children: [
          Icon(LucideIcons.cloud, size: 20, color: t.colorScheme.onPrimaryContainer),
          const SizedBox(width: 12),
          Expanded(child: Text('Want checks to keep running when the phone is off? GitHub can do that for free, in your own private repository.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onPrimaryContainer))),
          TextButton(onPressed: model.hideCloudOffer, child: const Text('Not now')),
          FilledButton(
            onPressed: () async {
              final c = await model.savedPortalLogin();
              if (context.mounted) await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CloudSetupWizard(model: model, prefill: c)));
            },
            child: const Text('Set up'),
          ),
        ]),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({required this.model});
  final AppModel model;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final made = DateTime.now().difference(model.summary!.generatedAt);
    final missing = model.syncSkipped.map((k) => const {'assignments': 'assignments', 'attendance': 'attendance', 'exams': 'exam seats', 'results': 'results', 'timetable': 'timetable', 'announcements': 'announcements', 'lectures': 'lectures'}[k] ?? k).join(', ');
    final text = model.error == null && model.portalMode && model.syncSkipped.isNotEmpty
        ? 'The portal did not give back: $missing. Pull down to try again.'
        : model.error != null
        ? '${model.error} Showing what was read ${model.fetchedAt == null ? 'earlier' : agoLabel(model.age!)}.'
        : model.portalMode ? 'The phone last read the portal ${agoLabel(made)}. Pull down to read it again.' : 'The last cloud check was ${agoLabel(made)}. Check that cloud checks are still on.';
    return Material(
      color: t.colorScheme.errorContainer,
      child: InkWell(
        onTap: model.refresh,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(children: [
            Icon(LucideIcons.cloudOff, size: 18, color: t.colorScheme.onErrorContainer),
            const SizedBox(width: 10),
            Expanded(child: Text(text, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onErrorContainer))),
          ]),
        ),
      ),
    );
  }
}

/// One slot of the floating bar. The four slots are always the same width, so they never move under a finger; the
/// selected one lights up as a pill and shows its name under the icon. A count sits on the icon as a small badge.
class _NavItem extends StatelessWidget {
  const _NavItem({required this.icon, required this.label, required this.selected, required this.onTap, this.badge = 0});
  final IconData icon;
  final String label;
  final bool selected;
  final int badge;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final fg = selected ? t.colorScheme.onPrimary : t.colorScheme.onSurfaceVariant;
    return Expanded(
      child: Semantics(
        button: true, selected: selected, label: badge > 0 ? '$label, $badge to do' : label,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () { if (!selected) HapticFeedback.selectionClick(); onTap(); },
          child: Center(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 240), curve: Curves.easeOutCubic,
              height: 54,
              margin: const EdgeInsets.symmetric(horizontal: 3),
              decoration: BoxDecoration(color: selected ? t.colorScheme.primary : Colors.transparent, borderRadius: BorderRadius.circular(99)),
              alignment: Alignment.center,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                SizedBox(
                  width: 28, height: 24,
                  child: Stack(clipBehavior: Clip.none, alignment: Alignment.center, children: [
                    Icon(icon, size: 22, color: fg),
                    if (badge > 0 && !selected) Positioned(
                      right: -4, top: -6,
                      child: Container(
                        constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                        padding: const EdgeInsets.symmetric(horizontal: 3.5),
                        alignment: Alignment.center,
                        decoration: BoxDecoration(color: t.colorScheme.primary, borderRadius: BorderRadius.circular(99), border: Border.all(color: t.colorScheme.surfaceContainerHigh, width: 2)),
                        child: Text(badge > 9 ? '9+' : '$badge', style: TextStyle(fontSize: 9.5, height: 1.1, fontWeight: FontWeight.w800, color: t.colorScheme.onPrimary)),
                      ),
                    ),
                  ]),
                ),
                AnimatedSize(
                  duration: const Duration(milliseconds: 240), curve: Curves.easeOutCubic,
                  child: selected
                      ? Padding(padding: const EdgeInsets.only(top: 1), child: Text(label, maxLines: 1, softWrap: false, overflow: TextOverflow.clip, textScaler: MediaQuery.textScalerOf(context).clamp(maxScaleFactor: 1.1), style: TextStyle(fontSize: 11, height: 1.1, fontWeight: FontWeight.w700, color: fg)))
                      : const SizedBox(width: 0, height: 0),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

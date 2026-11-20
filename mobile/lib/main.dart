import 'dart:async';

import 'package:flutter/material.dart';

import 'data.dart' show Clock;
import 'model.dart';
import 'screens/attendance.dart';
import 'data.dart' show Summary;
import 'screens/more.dart';
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

class _ShellState extends State<Shell> {
  int tab = 0;
  late Clock clock = widget.model.clock;
  Timer? tick;
  final _scaffold = GlobalKey<ScaffoldState>();

  static const _titles = ['Today', 'Work', 'Attendance', 'Exams'];

  @override
  void initState() {
    super.initState();
    tick = Timer.periodic(const Duration(seconds: 30), (_) => setState(() {}));   // the countdowns move
  }

  @override
  void dispose() { tick?.cancel(); super.dispose(); }

  void goto(int i) => setState(() => tab = i);

  /// Drawer rows: 0..3 are the bottom-bar screens, the rest open over them.
  void _drawerPick(int i, Summary s, DateTime now) {
    Navigator.of(context).pop();   // close the drawer
    switch (i) {
      case 0: case 1: case 2: case 3: goto(i);
      case 4: openPage(context, 'Timetable', TimetablePage(summary: s, now: now));
      case 5: openPage(context, 'Results and GPA calculator', ResultsPage(summary: s));
      case 6: openPage(context, 'Settings', SettingsPage(summary: s, prefs: widget.prefs, model: widget.model));
    }
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.model, s = m.summary!, now = clock.now(), t = Theme.of(context);
    final pages = [
      TodayScreen(summary: s, now: now, prefs: widget.prefs, onOpenWork: () => goto(1), onOpenAttendance: () => goto(2)),
      WorkScreen(summary: s, now: now, prefs: widget.prefs),
      AttendanceScreen(summary: s),
      ExamsPage(summary: s, now: now),
    ];
    final stale = !m.demo && (m.age?.inHours ?? 0) >= 24;
    final todo = s.work.where((w) => w.todo && w.open && !widget.prefs.done.contains(w.id)).length;
    return Scaffold(
      key: _scaffold,
      appBar: AppBar(
        leading: IconButton(icon: const Icon(Icons.menu), tooltip: 'Menu', onPressed: () => _scaffold.currentState?.openDrawer()),
        title: Text(_titles[tab], style: const TextStyle(fontWeight: FontWeight.w700)),
        actions: [
          if (!m.demo) m.refreshing
              ? const Padding(padding: EdgeInsets.all(14), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
              : IconButton(icon: const Icon(Icons.sync), tooltip: 'Check for new data', onPressed: m.refresh),
          IconButton(icon: const Icon(Icons.tune), tooltip: 'Settings', onPressed: () => openPage(context, 'Settings', SettingsPage(summary: s, prefs: widget.prefs, model: m))),
        ],
      ),
      drawer: NavigationDrawer(
        selectedIndex: tab,
        onDestinationSelected: (i) => _drawerPick(i, s, now),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 28, 16, 16),
            child: Row(children: [
              CircleAvatar(radius: 26, backgroundColor: t.colorScheme.primaryContainer,
                  child: Text(s.studentName.trim().isEmpty ? '?' : s.studentName.trim()[0].toUpperCase(), style: t.textTheme.titleLarge?.copyWith(color: t.colorScheme.onPrimaryContainer, fontWeight: FontWeight.w800))),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.studentName, maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                Text(m.demo ? 'Demo data' : [s.semester, if (m.age != null) 'read ${agoLabel(m.age!)}'].where((e) => e.isNotEmpty).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ])),
            ]),
          ),
          const NavigationDrawerDestination(icon: Icon(Icons.today_outlined), selectedIcon: Icon(Icons.today), label: Text('Today')),
          NavigationDrawerDestination(icon: const Icon(Icons.checklist_outlined), selectedIcon: const Icon(Icons.checklist), label: Text(todo > 0 ? 'Work  ·  $todo to do' : 'Work')),
          const NavigationDrawerDestination(icon: Icon(Icons.event_available_outlined), selectedIcon: Icon(Icons.event_available), label: Text('Attendance')),
          const NavigationDrawerDestination(icon: Icon(Icons.school_outlined), selectedIcon: Icon(Icons.school), label: Text('Exams')),
          const Padding(padding: EdgeInsets.fromLTRB(28, 12, 28, 12), child: Divider()),
          const NavigationDrawerDestination(icon: Icon(Icons.calendar_view_week_outlined), label: Text('Timetable')),
          const NavigationDrawerDestination(icon: Icon(Icons.calculate_outlined), label: Text('Results and GPA')),
          const NavigationDrawerDestination(icon: Icon(Icons.tune), label: Text('Settings')),
          Padding(
            padding: const EdgeInsets.fromLTRB(28, 16, 28, 8),
            child: Text('Your portal password never touches this phone.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          if (!m.demo && (m.error != null || stale)) _Banner(model: m),
          Expanded(
            child: RefreshIndicator(
              onRefresh: m.refresh,
              child: AnimatedSwitcher(duration: const Duration(milliseconds: 200), child: KeyedSubtree(key: ValueKey(tab), child: pages[tab])),
            ),
          ),
        ]),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: goto,
        destinations: [
          const NavigationDestination(icon: Icon(Icons.today_outlined), selectedIcon: Icon(Icons.today), label: 'Today'),
          NavigationDestination(icon: Badge(isLabelVisible: todo > 0, label: Text('$todo'), child: const Icon(Icons.checklist_outlined)), selectedIcon: const Icon(Icons.checklist), label: 'Work'),
          const NavigationDestination(icon: Icon(Icons.event_available_outlined), selectedIcon: Icon(Icons.event_available), label: 'Attendance'),
          const NavigationDestination(icon: Icon(Icons.school_outlined), selectedIcon: Icon(Icons.school), label: 'Exams'),
        ],
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

import 'dart:async';

import 'package:flutter/material.dart';

import 'data.dart' show Clock;
import 'model.dart';
import 'screens/attendance.dart';
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

  @override
  void initState() {
    super.initState();
    tick = Timer.periodic(const Duration(seconds: 30), (_) => setState(() {}));   // the countdowns move
  }

  @override
  void dispose() { tick?.cancel(); super.dispose(); }

  void goto(int i) => setState(() => tab = i);

  @override
  Widget build(BuildContext context) {
    final m = widget.model, s = m.summary!, now = clock.now();
    final pages = [
      TodayScreen(summary: s, now: now, prefs: widget.prefs, onOpenWork: () => goto(1), onOpenAttendance: () => goto(2)),
      WorkScreen(summary: s, now: now, prefs: widget.prefs),
      AttendanceScreen(summary: s),
      MoreScreen(summary: s, now: now, prefs: widget.prefs, model: m),
    ];
    final stale = !m.demo && (m.age?.inHours ?? 0) >= 24;
    return Scaffold(
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
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today_outlined), selectedIcon: Icon(Icons.today), label: 'Today'),
          NavigationDestination(icon: Icon(Icons.checklist_outlined), selectedIcon: Icon(Icons.checklist), label: 'Work'),
          NavigationDestination(icon: Icon(Icons.event_available_outlined), selectedIcon: Icon(Icons.event_available), label: 'Attendance'),
          NavigationDestination(icon: Icon(Icons.apps_outlined), selectedIcon: Icon(Icons.apps), label: 'More'),
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

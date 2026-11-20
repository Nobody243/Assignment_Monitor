import 'dart:async';

import 'package:flutter/material.dart';

import 'data.dart';
import 'screens/attendance.dart';
import 'screens/more.dart';
import 'screens/today.dart';
import 'screens/work.dart';
import 'theme.dart';

void main() => runApp(const AssignmentMonitorApp());

class AssignmentMonitorApp extends StatefulWidget {
  const AssignmentMonitorApp({super.key});
  @override
  State<AssignmentMonitorApp> createState() => _AppState();
}

/// App-wide choices the Settings screen changes: palette, light or dark, and which deadlines were snoozed or done.
class Prefs extends ChangeNotifier {
  Palette palette = palettes.first;
  ThemeMode mode = ThemeMode.system;
  List<int> leads = [24, 3, 1];
  final Set<String> done = {};
  final Map<String, DateTime> snoozed = {};
  void update(void Function() f) { f(); notifyListeners(); }
}

class _AppState extends State<AssignmentMonitorApp> {
  final prefs = Prefs();
  late final Future<Summary> summary = Summary.load();

  @override
  void initState() {
    super.initState();
    prefs.addListener(() => setState(() {}));
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assignment Monitor',
      debugShowCheckedModeBanner: false,
      themeMode: prefs.mode,
      theme: buildTheme(prefs.palette, Brightness.light),
      darkTheme: buildTheme(prefs.palette, Brightness.dark),
      home: FutureBuilder<Summary>(
        future: summary,
        builder: (context, snap) {
          if (!snap.hasData) return const Scaffold(body: Center(child: CircularProgressIndicator()));
          return Shell(summary: snap.data!, prefs: prefs);
        },
      ),
    );
  }
}

class Shell extends StatefulWidget {
  const Shell({super.key, required this.summary, required this.prefs});
  final Summary summary;
  final Prefs prefs;
  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int tab = 0;
  late final Clock clock = Clock(widget.summary.generatedAt);
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
    final s = widget.summary, now = clock.now();
    final pages = [
      TodayScreen(summary: s, now: now, prefs: widget.prefs, onOpenWork: () => goto(1), onOpenAttendance: () => goto(2)),
      WorkScreen(summary: s, now: now, prefs: widget.prefs),
      AttendanceScreen(summary: s),
      MoreScreen(summary: s, now: now, prefs: widget.prefs),
    ];
    return Scaffold(
      body: SafeArea(child: AnimatedSwitcher(duration: const Duration(milliseconds: 200), child: KeyedSubtree(key: ValueKey(tab), child: pages[tab]))),
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

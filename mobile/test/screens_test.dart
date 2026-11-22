import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/reminders.dart';
import 'package:assignment_monitor_mobile/screens/announcements.dart';
import 'package:assignment_monitor_mobile/screens/results.dart';
import 'package:assignment_monitor_mobile/screens/settings.dart';
import 'package:assignment_monitor_mobile/screens/signin.dart';
import 'package:assignment_monitor_mobile/screens/work.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late Summary summary;

  setUp(() { SharedPreferences.setMockInitialValues({}); Reminders.forceSupported = false; });

  Future<void> phone(WidgetTester tester, Widget body) async {
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
    summary = (await tester.runAsync(Summary.load))!;
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: body)));
    await tester.pump(const Duration(milliseconds: 600));
  }

  testWidgets('announcements: filter by course, expand for the text, and looking marks them read', (tester) async {
    final prefs = Prefs()..annSeen = DateTime(2026, 11, 17);
    final fixture = (await tester.runAsync(Summary.load))!;
    await phone(tester, AnnouncementsScreen(summary: fixture, prefs: prefs, now: fixture.generatedAt));
    final all = fixture.announcements;
    expect(all, isNotEmpty);
    expect(find.text(all.first.title), findsOneWidget);
    expect(find.text(all.first.text), findsNothing);                  // collapsed
    await tester.tap(find.text(all.first.title));
    await tester.pumpAndSettle();
    expect(find.text(all.first.text), findsOneWidget);                // expanded
    final course = ({for (final n in all) n.course}.toList()..sort()).first;   // the first course chip, alphabetically
    await tester.tap(find.byType(ChoiceChip).at(1));
    await tester.pumpAndSettle();
    for (final n in all.where((n) => n.course != course)) { expect(find.text(n.title), findsNothing, reason: '${n.title} belongs to another course'); }
    for (final n in all.where((n) => n.course == course)) { expect(find.text(n.title), findsOneWidget); }
    await tester.pump(const Duration(seconds: 2));                    // after a moment the list counts as read
    expect(prefs.annSeen!.isAfter(DateTime(2026, 11, 17)), isTrue);
  });

  testWidgets('results: the calculator works out GPA, CGPA and a target from tapped grades', (tester) async {
    await phone(tester, Builder(builder: (c) => const SizedBox()));
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: ResultsPage(summary: summary))));
    await tester.pumpAndSettle();
    expect(find.text('CUMULATIVE GPA'), findsOneWidget);
    expect(find.text(summary.cgpa!.toStringAsFixed(2)), findsWidgets);
    await tester.tap(find.text('Calculator'));
    await tester.pumpAndSettle();
    expect(find.text('Semester GPA'), findsOneWidget);
    // two courses of 3 credit hours each: an A and a B make 3.50
    await tester.tap(find.text('A').first);
    await tester.pumpAndSettle();
    expect(find.text('4.00'), findsWidgets);   // one graded course so far: 4.00
    await tester.tap(find.text('B').at(1));    // the B chip of the second course
    await tester.pumpAndSettle();
    expect(find.text('3.50'), findsWidgets);
    // the transcript can fill in "where you stand now"
    await tester.scrollUntilVisible(find.text('Use my transcript'), 300, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('Use my transcript'));
    await tester.pumpAndSettle();
    expect(find.text(summary.cgpa!.toStringAsFixed(2)), findsWidgets);
  });

  testWidgets('work: swiping a row right marks it done, with an undo', (tester) async {
    final prefs = Prefs();
    await phone(tester, Builder(builder: (c) => const SizedBox()));
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: WorkScreen(summary: summary, now: summary.generatedAt, prefs: prefs))));
    await tester.pumpAndSettle();
    final first = summary.work.where((w) => w.todo).first;
    await tester.drag(find.byType(Dismissible).first, const Offset(500, 0));
    await tester.pumpAndSettle();
    expect(prefs.done, isNotEmpty);
    expect(prefs.done.first, first.id);
    expect(find.text('Marked done. No more reminders for it.'), findsOneWidget);
    await tester.tap(find.text('Undo'));
    await tester.pumpAndSettle();
    expect(prefs.done, isEmpty);
  });

  testWidgets('work: swiping left snoozes for an hour', (tester) async {
    final prefs = Prefs();
    await phone(tester, Builder(builder: (c) => const SizedBox()));
    final now = summary.generatedAt;
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: WorkScreen(summary: summary, now: now, prefs: prefs))));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(Dismissible).first, const Offset(-500, 0));
    await tester.pumpAndSettle();
    expect(prefs.snoozed.values.single, now.add(const Duration(hours: 1)));
  });

  testWidgets('settings: reminder lead times can be changed and are kept', (tester) async {
    final prefs = Prefs();
    await phone(tester, Builder(builder: (c) => const SizedBox()));
    final model = AppModel(prefs)..summary = summary..demo = true;
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: RemindersSettings(prefs: prefs, model: model))));
    await tester.pumpAndSettle();
    expect(prefs.leads, [24, 3, 1]);
    await tester.tap(find.text('6 h'));
    await tester.pumpAndSettle();
    expect(prefs.leads, [24, 6, 3, 1]);
    await tester.tap(find.text('1 day'));
    await tester.pumpAndSettle();
    expect(prefs.leads, [6, 3, 1]);
    expect((await SharedPreferences.getInstance()).getStringList('leads'), ['6', '3', '1']);
  });

  testWidgets('sign-in: shows the code to type on GitHub while waiting, and an error if it failed', (tester) async {
    final model = AppModel(Prefs());
    await phone(tester, ListenableBuilder(listenable: model, builder: (_, _) => SignInScreen(model: model)));
    await tester.scrollUntilVisible(find.text('Look around with demo data'), 150, scrollable: find.byType(Scrollable).first);
    expect(find.text('Sign in (read-only, recommended)'), findsOneWidget);
    expect(find.text('Set up from this phone'), findsOneWidget);
    expect(find.text('Look around with demo data'), findsOneWidget);
    model.code = DeviceCode('dc', 'ABCD-1234', 'https://github.com/login/device', 5, 900);
    model.phase = Phase.signingIn;
    model.notifyListeners();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('ABCD-1234'), findsOneWidget);
    expect(find.text('Open GitHub'), findsOneWidget);
    model..code = null..phase = Phase.signedOut..error = 'You declined the request on GitHub.';
    model.notifyListeners();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('You declined the request on GitHub.'), findsOneWidget);
  });

  testWidgets('sign-in: waiting for the first cloud check explains what to do', (tester) async {
    final model = AppModel(Prefs())..phase = Phase.waiting..login = 'alex';
    await phone(tester, SignInScreen(model: model));
    expect(find.textContaining('alex/assignment-monitor-cloud'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Check again'), 200);
    expect(find.text('Check again'), findsOneWidget);
  });

  testWidgets('sign-in: the read-only token page explains the steps and rejects a bad token', (tester) async {
    final model = AppModel(Prefs());
    await phone(tester, ListenableBuilder(listenable: model, builder: (_, _) => TokenSignInPage(model: model)));
    expect(find.textContaining('assignment-monitor-cloud'), findsOneWidget);
    expect(find.text('Open GitHub token page'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'not a token');
    await tester.scrollUntilVisible(find.widgetWithText(FilledButton, 'Sign in'), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(find.textContaining('does not look like a GitHub token'), findsOneWidget);
  });
}

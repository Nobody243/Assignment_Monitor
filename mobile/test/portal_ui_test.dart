import 'dart:convert';
import 'dart:io';

import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/screens/portal_signin.dart';
import 'package:assignment_monitor_mobile/screens/settings.dart';
import 'package:assignment_monitor_mobile/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

/// The screens added for the Full app, at the sizes that break layouts: a small phone, large text, light and dark.
void main() {
  final summary = Summary(jsonDecode(File('assets/summary.json').readAsStringSync()) as Map<String, dynamic>);

  Future<void> show(WidgetTester tester, Widget Function() build, {double scale = 1, Size size = const Size(320, 568), Brightness b = Brightness.light}) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 1; tester.view.physicalSize = size;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      theme: buildTheme(palettes.first, b),
      builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(scale)), child: child!),
      home: build(),
    ));
    await tester.pump(const Duration(milliseconds: 700));
  }

  AppModel model() => AppModel(Prefs()..setupDone = true, store: MemoryStore(), splashMin: Duration.zero);   // the first-run sheet has been seen

  for (final b in Brightness.values) {
    for (final scale in [1.0, 2.0]) {
      final label = '${b.name}, text ${scale}x';

      testWidgets('portal sign-in form, with an error and with the way out ($label)', (tester) async {
        final m = model();
        await show(tester, () => PortalSignInPage(model: m), scale: scale, b: b);
        expect(tester.takeException(), isNull);
        final state = tester.state(find.byType(PortalSignInPage)) as dynamic;
        state.setState(() { state.failed = const SignInResult.failed(SignInProblem.blocked, 'The portal is asking for a captcha, which the phone cannot solve on its own.'); });
        await tester.pump();
        expect(tester.takeException(), isNull);
        await tester.scrollUntilVisible(find.text('Use my GitHub cloud checks instead'), 100, scrollable: find.byType(Scrollable).first);
        expect(find.text('Use my GitHub cloud checks instead'), findsOneWidget);
      });

      testWidgets('shell while the portal is read: progress bar, offer banner and a missing-parts banner ($label)', (tester) async {
        final m = model()..summary = summary..portalMode = true..phase = Phase.ready..cloudOfferHidden = false..refreshing = true
          ..syncStep = 'Reading attendance'..syncDone = 1..syncTotal = 7..syncSkipped = ['lectures', 'exams'];
        await show(tester, () => ListenableBuilder(listenable: m, builder: (_, _) => Shell(model: m, prefs: m.prefs)), scale: scale, b: b);
        expect(find.textContaining('Reading attendance'), findsOneWidget);
        expect(find.textContaining('2 of 7'), findsOneWidget);
        expect(tester.takeException(), isNull);
        // when the read is over the next strip shows: what is missing first, then the offer
        m.refreshing = false; m.notifyListeners();
        await tester.pump(const Duration(milliseconds: 400));
        expect(find.textContaining('did not give back: lectures, exam seats'), findsOneWidget);
        expect(tester.takeException(), isNull);
        m.syncSkipped = const []; m.notifyListeners();
        await tester.pump(const Duration(milliseconds: 400));
        expect(find.textContaining('GitHub can do that'), findsNothing, reason: 'a 320 x 568 screen is too small for the offer: it waits for Settings');
        expect(tester.takeException(), isNull);
      });

      testWidgets('settings in the Full app and in GitHub mode, and the read report ($label)', (tester) async {
        final m = model()..summary = summary..portalMode = true..syncReport = ['assignments: 12 assignments in 5 courses (6.1 s)', 'lectures: could not be read (StateError)'];
        await show(tester, () => Scaffold(body: SettingsHub(summary: summary, prefs: m.prefs, model: m)), scale: scale, b: b);
        expect(find.text('What the phone read'), findsOneWidget);
        expect(tester.takeException(), isNull);
        final g = model()..summary = summary;
        await show(tester, () => Scaffold(body: SettingsHub(summary: summary, prefs: g.prefs, model: g)), scale: scale, b: b);
        expect(find.text('University login'), findsOneWidget, reason: 'a GitHub user can add the university login later');
        await tester.pumpWidget(MaterialApp(home: SyncReportPage(model: m)));
        await tester.pump();
        expect(find.textContaining('could not be read'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  }

  for (final b in Brightness.values) {
    testWidgets('the offer shows on a normal phone at normal text and then sits on its own strip (${b.name})', (tester) async {
      final m = model()..summary = summary..portalMode = true..phase = Phase.ready..cloudOfferHidden = false;
      await show(tester, () => ListenableBuilder(listenable: m, builder: (_, _) => Shell(model: m, prefs: m.prefs)), size: const Size(390, 844), b: b);
      expect(find.textContaining('GitHub can do that'), findsOneWidget);
      expect(find.text('Set up'), findsOneWidget);
      expect(find.text('Not now'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Not now'));
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.textContaining('GitHub can do that'), findsNothing);
    });
  }

  testWidgets('the account screen tells the truth in each mode', (tester) async {
    final portalModel = model()..summary = summary..portalMode = true;
    await show(tester, () => Scaffold(body: AccountSettings(summary: summary, model: portalModel)), size: const Size(390, 844));
    expect(find.textContaining('University portal'), findsWidgets);
    expect(find.text('Last read from the portal'), findsOneWidget);
    expect(find.text('Delete downloaded files'), findsOneWidget);
    expect(find.textContaining('GitHub:'), findsNothing);
    final cloudModel = model()..summary = summary..login = 'alex';
    await show(tester, () => Scaffold(body: AccountSettings(summary: summary, model: cloudModel)), size: const Size(390, 844));
    expect(find.text('Last read from GitHub'), findsOneWidget);
    expect(find.text('Delete downloaded files'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  test('deleting downloads removes every file, counts them, and signing out does it too', () async {
    SharedPreferences.setMockInitialValues({});
    final dir = Directory.systemTemp.createTempSync('dl_test');
    final sub = Directory('${dir.path}/downloads/Course/Week 01')..createSync(recursive: true);
    File('${sub.path}/a.pdf').writeAsBytesSync([1, 2, 3]);
    File('${sub.path}/b.pdf').writeAsBytesSync([4]);
    final m = AppModel(Prefs()..setupDone = true, store: MemoryStore(), filesDir: () async => Directory('${dir.path}/downloads'));
    expect(await m.clearDownloads(), 2);
    expect(Directory('${dir.path}/downloads').existsSync(), isFalse);
    expect(await m.clearDownloads(), 0, reason: 'nothing there is not an error');
    Directory('${dir.path}/downloads').createSync(recursive: true);
    File('${dir.path}/downloads/c.pdf').writeAsBytesSync([9]);
    await m.forgetPortal();
    expect(await m.clearDownloads(), 1);
    dir.deleteSync(recursive: true);
  });
}

import 'dart:convert';

import 'package:assignment_monitor_mobile/alerts.dart';
import 'package:assignment_monitor_mobile/background.dart';
import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/reminders.dart';
import 'package:assignment_monitor_mobile/screens/first_run.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';
import 'lock_test.dart' show FakeLocker;

Summary summaryWith(String name, {List<Map<String, dynamic>> notes = const []}) => Summary({
      'schema': 1, 'generated_at': '2026-11-20T10:00:00', 'student': {'name': name}, 'assignments': [], 'attendance': [],
      'exams': [], 'timetable': [], 'announcements': notes,
    });

void main() {
  setUp(() { SharedPreferences.setMockInitialValues({}); Reminders.forceSupported = false; });

  group('the saved summary is kept in the keystore, not in plain preferences', () {
    test('saving writes it to the vault and nowhere in preferences', () async {
      final vault = MemoryVault();
      final store = Store(vault: vault);
      await store.saveSession('tok', 'alex');
      await store.saveSummary(summaryWith('Alex Morgan'), 'W/"1"');
      expect(vault.data['token'], 'tok');
      expect(jsonDecode(vault.data['summary']!)['student']['name'], 'Alex Morgan');
      final prefs = await SharedPreferences.getInstance();
      for (final k in prefs.getKeys()) { expect('${prefs.get(k)}'.contains('Alex Morgan'), isFalse, reason: 'preference $k holds the summary'); }
      expect(prefs.getString('etag'), 'W/"1"');   // the ETag and login name are not secret
    });

    test('reads it back, with its ETag', () async {
      final store = Store(vault: MemoryVault());
      await store.saveSummary(summaryWith('Alex'), 'e');
      final c = await store.cached();
      expect(c.summary!.studentName, 'Alex');
      expect(c.etag, 'e');
      expect(c.fetchedAt, isNotNull);
    });

    test('a copy an earlier build left in plain preferences is moved into the vault and removed', () async {
      SharedPreferences.setMockInitialValues({'summary': jsonEncode(summaryWith('Old Copy').raw)});
      final vault = MemoryVault();
      final c = await Store(vault: vault).cached();
      expect(c.summary!.studentName, 'Old Copy');
      expect(vault.data['summary'], isNotNull);
      expect((await SharedPreferences.getInstance()).containsKey('summary'), isFalse);
    });

    test('sign out deletes the token and the summary everywhere', () async {
      final vault = MemoryVault();
      final store = Store(vault: vault);
      await store.saveSession('tok', 'alex');
      await store.saveSummary(summaryWith('Alex'), 'e');
      await store.clear();
      expect(vault.data, isEmpty);
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getKeys().where((k) => ['login', 'summary', 'etag', 'fetched'].contains(k)), isEmpty);
    });

    test('a damaged saved summary is ignored, not a crash', () async {
      final vault = MemoryVault()..data['summary'] = '{not json';
      expect((await Store(vault: vault).cached()).summary, isNull);
    });
  });

  group('what a notification shows while the app lock is on', () {
    test('a reminder says only that something is due soon', () {
      final shown = Reminders.reminderText(course: 'Database Systems', title: 'Normalisation worksheet', number: '4', hours: 3, hide: true);
      expect(shown.title, 'Assignment due soon');
      for (final private in ['Database', 'Normalisation', '3 hours']) { expect('${shown.title} ${shown.body}'.contains(private), isFalse, reason: private); }
    });

    test('without the lock it names the assignment, as before', () {
      final shown = Reminders.reminderText(course: 'Database Systems', title: 'Normalisation worksheet', number: '4', hours: 3, hide: false);
      expect(shown.title, 'Database Systems: Normalisation worksheet');
      expect(shown.body, 'Assignment 4 is due in 3 hours.');
      expect(Reminders.reminderText(course: '', title: 'T', number: '1', hours: 1, hide: false).body, 'Assignment 1 is due in 1 hour.');
      expect(Reminders.reminderText(course: 'C', title: 'T', number: '1', hide: false).body, 'Assignment 1 is still open.');
    });

    test('news and summaries are generic too', () {
      const news = (title: 'Marks posted: Quiz 2', body: 'Databases: 9/10');
      expect(Reminders.maskNews(news, hide: true).title, 'Assignment Monitor');
      expect(Reminders.maskNews(news, hide: true).body.contains('Quiz'), isFalse);
      expect(Reminders.maskNews(news, hide: false), news);
      const week = (title: 'Your week ahead: 3 due', body: 'Due next week (3): Task a');
      expect(Reminders.maskSummary(week, hide: true, daily: false).title, 'Your week ahead');
      expect(Reminders.maskSummary(week, hide: true, daily: true).title, 'Your day');
      expect(Reminders.maskSummary(week, hide: true, daily: false).body.contains('Task a'), isFalse);
      expect(Reminders.maskSummary(week, hide: false, daily: false), week);
    });

    test('the background check sends the generic text when the lock is on, the real text when it is off', () async {
      final old = summaryWith('Alex');
      final fresh = summaryWith('Alex', notes: [{'id': 'n2', 'title': 'Secret quiz result', 'course': 'Databases'}]);
      Future<List<AlertText>> run(bool lock) async {
        SharedPreferences.setMockInitialValues({'appLock': lock});
        final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = old..etagV = 'e1';
        final shown = <AlertText>[];
        await BackgroundCheck.run(store: store, source: SummarySource(MockClient((_) async => http.Response(jsonEncode(fresh.raw), 200, headers: {'etag': 'e2'}))), notify: (m, id) async => shown.add(m));
        return shown;
      }
      expect((await run(true)).single.title, 'Assignment Monitor');
      expect((await run(true)).single.body.contains('Secret'), isFalse);
      expect((await run(false)).single.title, 'New announcement: Secret quiz result');
    });
  });

  group('screenshots and the recent-apps preview', () {
    final calls = <MethodCall>[];
    setUp(() {
      calls.clear();
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('am/secure'), (c) async { calls.add(c); return null; });
    });
    tearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('am/secure'), null));

    test('is on by default and the setting is remembered', () async {
      final m = AppModel(Prefs(), store: MemoryStore(), splashMin: Duration.zero);
      expect(m.prefs.secureScreen, isTrue);
      m.setSecureScreen(false);
      await Future.delayed(const Duration(milliseconds: 20));
      expect(calls.single.method, 'set');
      expect(calls.single.arguments, {'on': false});
      expect((await SharedPreferences.getInstance()).getBool('secureScreen'), isFalse);
      m.setSecureScreen(true);
      expect(calls.last.arguments, {'on': true});
    });

    test('is applied when the app starts', () async {
      SharedPreferences.setMockInitialValues({'secureScreen': false});
      await AppModel(Prefs(), store: MemoryStore(), splashMin: Duration.zero).start();
      await Future.delayed(const Duration(milliseconds: 20));
      expect(calls.first.arguments, {'on': false});
    });
  });

  group('the first-run setup', () {
    Future<AppModel> readyModel({bool demo = false, FakeLocker? locker}) async {
      final m = AppModel(Prefs(), store: MemoryStore(), locker: locker ?? FakeLocker(), splashMin: Duration.zero)
        ..summary = summaryWith('Alex')
        ..phase = Phase.ready
        ..demo = demo;
      return m;
    }

    test('is due for a signed-in user who has not seen it, not in the demo, and only once', () async {
      expect((await readyModel()).firstRunDue, isTrue);
      expect((await readyModel(demo: true)).firstRunDue, isFalse);
      final m = await readyModel();
      m.finishFirstRun();
      expect(m.firstRunDue, isFalse);
      await Future.delayed(const Duration(milliseconds: 20));
      expect((await SharedPreferences.getInstance()).getBool('setupDone'), isTrue);
    });

    Future<void> openFlow(WidgetTester tester, AppModel model) async {
      tester.view.devicePixelRatio = 3;
      tester.view.physicalSize = const Size(390 * 3, 800 * 3);
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(home: Builder(builder: (c) => Scaffold(body: Center(child: FilledButton(onPressed: () => runFirstRun(c, model), child: const Text('go')))))));
      await tester.tap(find.text('go'));
      await tester.pumpAndSettle();
    }

    testWidgets('asks about reminders, then offers the lock, and remembers it was shown', (tester) async {
      final model = await readyModel();
      await openFlow(tester, model);
      expect(find.text('Set up your reminders'), findsOneWidget);
      await tester.tap(find.text('6 h'));
      await tester.pumpAndSettle();
      expect(model.prefs.leads, [24, 6, 3, 1]);
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();
      expect(find.text('Protect your grades?'), findsOneWidget);
      await tester.tap(find.text('Not now'));
      await tester.pumpAndSettle();
      expect(model.prefs.setupDone, isTrue);
      expect(model.prefs.appLock, isFalse);
    });

    testWidgets('"Turn on" locks the app after one successful check', (tester) async {
      final model = await readyModel();
      await openFlow(tester, model);
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Turn on'));
      await tester.pumpAndSettle();
      expect(model.prefs.appLock, isTrue);
      expect(model.prefs.setupDone, isTrue);
    });

    testWidgets('a phone with no screen lock explains why the lock stays off', (tester) async {
      tester.view.devicePixelRatio = 3;
      tester.view.physicalSize = const Size(390 * 3, 800 * 3);
      addTearDown(tester.view.reset);
      final model = await readyModel(locker: FakeLocker(isAvailable: false));
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: LockOfferDialog(model: model))));
      await tester.tap(find.text('Turn on'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Set up a screen lock'), findsOneWidget);
      expect(model.prefs.appLock, isFalse);
    });
  });
}

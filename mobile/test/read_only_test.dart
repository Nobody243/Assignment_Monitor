import 'dart:convert';

import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/reminders.dart';
import 'package:assignment_monitor_mobile/screens/settings.dart';
import 'package:assignment_monitor_mobile/screens/work.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

/// The phone reads a prepared summary (from the desktop app or the GitHub checks); the university login only adds the lecture
/// list and downloads. These tests pin that: GitHub is the source whenever it is connected, the portal is never read for the
/// data then, and nothing on the phone changes anything on the portal.
Map<String, dynamic> _summary(String name) => {
      'schema': 1, 'generated_at': '2026-11-21T10:00:00', 'student': {'name': name}, 'assignments': [], 'attendance': [],
      'exams': [], 'timetable': [], 'announcements': [],
    };

void main() {
  setUp(() { SharedPreferences.setMockInitialValues({}); Reminders.forceSupported = false; });
  const creds = PortalCredentials('01-1-1', 'pw', '1');

  Future<AppModel> make({required MemoryStore store, required List<String> portalCalls, bool login = true}) async {
    final ps = PortalStore(MemoryVault());
    if (login) await ps.save(creds);
    return AppModel(Prefs()..setupDone = true, store: store, portalStore: ps,
        source: SummarySource(MockClient((_) async => http.Response(jsonEncode(_summary('From GitHub')), 200, headers: {'etag': 'e2'}))),
        splashMin: Duration.zero,
        portalFactory: ({credentials}) { portalCalls.add('portal opened'); return Portal(OfflineBrowser(), pause: Duration.zero, signInSeconds: 0, credentials: credentials); });
  }

  Future<void> idle(AppModel m) async { for (var i = 0; i < 50 && m.refreshing; i++) { await Future<void>.delayed(const Duration(milliseconds: 20)); } }

  test('with a GitHub sign-in the data comes from GitHub even when a university login is saved, and the portal is not opened', () async {
    final calls = <String>[];
    final store = MemoryStore()..tokenV = 't'..loginV = 'alex';
    final m = await make(store: store, portalCalls: calls);
    await m.start();
    await idle(m);
    await m.refresh();
    expect(m.hasLogin, isTrue);
    expect(m.portalMode, isFalse, reason: 'the portal is not the data source');
    expect(m.summary!.studentName, 'From GitHub');
    expect(calls, isEmpty);
  });

  test('without a GitHub sign-in the saved login is the data source, as before', () async {
    final m = await make(store: MemoryStore(), portalCalls: []);
    await m.start();
    expect(m.hasLogin, isTrue);
    expect(m.portalMode, isTrue);
  });

  test('the lecture list the phone holds survives a refresh from GitHub, which does not carry lectures', () async {
    final store = MemoryStore()..tokenV = 't'..loginV = 'alex'
      ..summaryV = Summary({..._summary('Old'), 'lectures': [{'id': 'x', 'course': 'C', 'week': 1, 'title': 'Week one', 'files': []}]});
    final m = await make(store: store, portalCalls: []);
    await m.start();
    await m.refresh();
    expect(m.summary!.studentName, 'From GitHub');
    expect(m.summary!.lectures.single.title, 'Week one');
    expect(((await store.cached()).summary!.raw['lectures'] as List).length, 1, reason: 'and it is saved that way');
  });

  test('refreshing the Lectures screen reads the portal for the list even though the data is from GitHub', () async {
    final calls = <String>[];
    final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary('Old'));
    final m = await make(store: store, portalCalls: calls);
    await m.start();
    calls.clear();
    await m.refreshSection('lectures');
    expect(calls, isNotEmpty, reason: 'the portal is opened for the lecture list');
    expect(m.portalMode, isFalse);
    expect(m.summary!.studentName, 'From GitHub', reason: 'the other sections are left alone');
  });

  test('removing the login stops the portal being used and keeps the data', () async {
    final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary('Kept'));
    final m = await make(store: store, portalCalls: []);
    await m.start();
    expect(m.hasLogin, isTrue);
    await m.removePortalLogin();
    expect(m.hasLogin, isFalse);
    expect(await m.hasPortal(), isFalse);
  });

  testWidgets('the assignment sheet offers the brief with a login, and never an upload, replace or delete', (tester) async {
    final m = AppModel(Prefs(), store: MemoryStore())..hasLogin = true;
    final work = {'id': 'a', 'course': 'DB', 'title': 'Lab', 'number': '1', 'due_at': '2026-11-25T23:59:00', 'submitted': false, 'open': true,
        'urgency': 'soon', 'can_submit': true, 'has_brief': true};
    tester.view.devicePixelRatio = 1; tester.view.physicalSize = const Size(390, 900);
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: WorkScreen(
        summary: Summary({..._summary('A'), 'assignments': [work]}), now: DateTime(2026, 11, 21), prefs: m.prefs, model: m))));
    await tester.pump(const Duration(milliseconds: 600));
    await tester.tap(find.text('Lab'));
    await tester.pumpAndSettle();
    expect(find.text('Download the brief'), findsOneWidget);
    for (final text in ['Upload your work', 'Replace your submission', 'Delete your submission']) {
      expect(find.text(text), findsNothing, reason: text);
    }
    expect(phoneUploads, isFalse);
  });

  testWidgets('Settings offers the University login when there is none, and removing it when there is', (tester) async {
    Future<void> show(AppModel m) async {
      tester.view.devicePixelRatio = 1; tester.view.physicalSize = const Size(390, 900);
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: SettingsHub(summary: Summary(_summary('A')), prefs: m.prefs, model: m))));
      await tester.pump(const Duration(milliseconds: 600));
    }
    addTearDown(tester.view.reset);
    final none = AppModel(Prefs(), store: MemoryStore())..summary = Summary(_summary('A'));
    await show(none);
    expect(find.text('University login'), findsOneWidget);
    expect(find.textContaining('Add it to see lecture notes'), findsOneWidget);
    final has = AppModel(Prefs(), store: MemoryStore())..summary = Summary(_summary('A'))..hasLogin = true;
    await show(has);
    expect(find.textContaining('Tap to remove it'), findsOneWidget);
  });

  testWidgets('each Settings page has exactly one app bar and so one back button, including University login and the read report', (tester) async {
    Future<void> openPage(AppModel m, String row) async {
      tester.view.devicePixelRatio = 1; tester.view.physicalSize = const Size(390, 900);
      await tester.pumpWidget(MaterialApp(key: UniqueKey(), home: Scaffold(body: SettingsHub(summary: Summary(_summary('A')), prefs: m.prefs, model: m))));
      await tester.pump(const Duration(milliseconds: 600));
      await tester.tap(find.text(row));
      await tester.pumpAndSettle();
    }
    addTearDown(tester.view.reset);
    final none = AppModel(Prefs(), store: MemoryStore())..summary = Summary(_summary('A'));
    for (final row in ['Reminders', 'Appearance', 'University login']) {
      await openPage(none, row);
      expect(find.byType(AppBar), findsOneWidget, reason: row);
      expect(find.byType(BackButton), findsOneWidget, reason: row);
    }
    final has = AppModel(Prefs(), store: MemoryStore())..summary = Summary(_summary('A'))..hasLogin = true;
    await openPage(has, 'University login');
    expect(find.byType(AppBar), findsOneWidget, reason: 'remove login');
    final portal = AppModel(Prefs(), store: MemoryStore())..summary = Summary(_summary('A'))..portalMode = true..hasLogin = true..syncReport = ['assignments: 3 (1.0 s)'];
    await openPage(portal, 'What the phone read');
    expect(find.byType(AppBar), findsOneWidget, reason: 'read report');
    expect(find.byType(BackButton), findsOneWidget, reason: 'read report');
  });
}

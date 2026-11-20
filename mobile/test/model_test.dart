import 'dart:convert';

import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/reminders.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

Map<String, dynamic> _summary({String name = 'Alex', List<Map<String, dynamic>> announcements = const []}) => {
      'schema': 1, 'generated_at': '2026-11-20T10:00:00', 'student': {'name': name}, 'assignments': [], 'attendance': [],
      'exams': [], 'timetable': [], 'announcements': announcements,
    };

AppModel _model(MemoryStore store, http.Client client, {GithubAuth? auth}) => AppModel(Prefs(),
    store: store, auth: auth ?? GithubAuth(MockClient((_) async => http.Response('{}', 404)), Duration.zero), source: SummarySource(client),
    splashMin: Duration.zero, splashMax: const Duration(seconds: 2));

void main() {
  setUp(() { SharedPreferences.setMockInitialValues({}); Reminders.forceSupported = false; });

  group('start', () {
    test('no sign-in: signed out, and the intro is still to be shown', () async {
      final m = _model(MemoryStore(), MockClient((_) async => http.Response('', 500)));
      await m.start();
      expect(m.phase, Phase.signedOut);
      expect(m.introSeen, isFalse);
    });

    test('signed in with a saved summary: opens on it and refreshes from GitHub', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary(name: 'Old'))
        ..etagV = 'W/"1"';
      final m = _model(store, MockClient((r) async {
        expect(r.headers['If-None-Match'], 'W/"1"');
        return http.Response(jsonEncode(_summary(name: 'New')), 200, headers: {'etag': 'W/"2"'});
      }));
      await m.start();
      expect(m.phase, Phase.ready);
      expect(m.summary!.studentName, 'New');
      expect(m.etag, 'W/"2"');
      expect((await store.cached()).summary!.studentName, 'New');   // saved for the next launch
    });

    test('signed in but GitHub has no summary yet: waits, without an error', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex';
      final m = _model(store, MockClient((_) async => http.Response('{}', 404)));
      await m.start();
      expect(m.phase, Phase.waiting);
      expect(m.error, isNull);
    });
  });

  group('refresh', () {
    Future<AppModel> ready(MemoryStore store, http.Client client) async {
      final m = _model(store, client);
      await m.start();
      return m;
    }

    test('unchanged (304) keeps the summary and only refreshes the time', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary())..etagV = 'e';
      final m = await ready(store, MockClient((_) async => http.Response('', 304)));
      final before = m.fetchedAt;
      await Future.delayed(const Duration(milliseconds: 5));
      await m.refresh();
      expect(m.summary!.studentName, 'Alex');
      expect(m.fetchedAt!.isAfter(before!) || m.fetchedAt == before, isTrue);
      expect(m.error, isNull);
    });

    test('offline: the old summary stays on screen and the problem is said plainly', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary());
      var online = true;
      final m = await ready(store, MockClient((_) async { if (online) return http.Response('', 304); throw http.ClientException('down'); }));
      online = false;
      await m.refresh();
      expect(m.phase, Phase.ready);
      expect(m.summary, isNotNull);
      expect(m.error, 'No connection.');
    });

    test('a rejected token says to sign in again and keeps the data', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary());
      var bad = false;
      final m = await ready(store, MockClient((_) async => bad ? http.Response('{}', 401) : http.Response('', 304)));
      bad = true;
      await m.refresh();
      expect(m.error, contains('Sign in again'));
      expect(m.summary, isNotNull);
    });

    test('a refresh already running is not started twice', () async {
      var calls = 0;
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary());
      final m = await ready(store, MockClient((_) async { calls++; await Future.delayed(const Duration(milliseconds: 30)); return http.Response('', 304); }));
      calls = 0;
      await Future.wait([m.refresh(), m.refresh(), m.refresh()]);
      expect(calls, 1);
    });
  });

  group('sign in and out', () {
    test('the device flow signs in, saves the sign-in and loads the summary', () async {
      var polls = 0;
      final auth = GithubAuth(MockClient((r) async {
        if (r.url.path == '/login/device/code') return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'ABCD-1234', 'verification_uri': 'https://github.com/login/device', 'interval': 0, 'expires_in': 60}), 200);
        if (r.url.path == '/login/oauth/access_token') { polls++; return http.Response(jsonEncode(polls < 3 ? {'error': 'authorization_pending'} : {'access_token': 'tok'}), 200); }
        if (r.url.path == '/user') return http.Response(jsonEncode({'login': 'alex'}), 200);
        return http.Response('{}', 404);
      }), Duration.zero);
      final store = MemoryStore();
      final m = _model(store, MockClient((_) async => http.Response(jsonEncode(_summary()), 200, headers: {'etag': 'e'})), auth: auth);
      await m.signIn();
      expect(store.tokenV, 'tok');
      expect(m.login, 'alex');
      expect(m.phase, Phase.ready);
      expect(polls, 3);
    });

    test('declining on GitHub returns to the sign-in screen with a message', () async {
      final auth = GithubAuth(MockClient((r) async {
        if (r.url.path == '/login/device/code') return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'X', 'verification_uri': 'https://github.com/login/device', 'interval': 0, 'expires_in': 60}), 200);
        return http.Response(jsonEncode({'error': 'access_denied'}), 200);
      }), Duration.zero);
      final m = _model(MemoryStore(), MockClient((_) async => http.Response('', 500)), auth: auth);
      await m.signIn();
      expect(m.phase, Phase.signedOut);
      expect(m.error, contains('declined'));
      expect(m.code, isNull);
    });

    test('an expired code is reported', () async {
      final auth = GithubAuth(MockClient((r) async {
        if (r.url.path == '/login/device/code') return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'X', 'verification_uri': 'https://github.com/login/device', 'interval': 0, 'expires_in': 60}), 200);
        return http.Response(jsonEncode({'error': 'expired_token'}), 200);
      }), Duration.zero);
      final m = _model(MemoryStore(), MockClient((_) async => http.Response('', 500)), auth: auth);
      await m.signIn();
      expect(m.error, contains('expired'));
    });

    test('sign out forgets the sign-in, the summary and the data on screen', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'..summaryV = Summary(_summary());
      final m = _model(store, MockClient((_) async => http.Response('', 304)));
      await m.start();
      await m.signOut();
      expect(store.cleared, isTrue);
      expect(m.phase, Phase.signedOut);
      expect(m.summary, isNull);
      expect(m.login, isNull);
    });
  });

  group('announcements and the intro', () {
    test('the first summary sets the starting point, later posts count as new', () async {
      final store = MemoryStore()..tokenV = 't'..loginV = 'alex'
        ..summaryV = Summary(_summary(announcements: [{'id': 'a', 'title': 'A', 'course': 'C', 'posted_at': '2026-11-18T09:00:00'}]));
      final m = _model(store, MockClient((_) async => http.Response('', 304)));
      await m.start();
      expect(m.newAnnouncements, 0);   // a new install does not start with a pile of "new"
      m.summary = Summary(_summary(announcements: [
        {'id': 'b', 'title': 'B', 'course': 'C', 'posted_at': '2026-11-19T09:00:00'},
        {'id': 'a', 'title': 'A', 'course': 'C', 'posted_at': '2026-11-18T09:00:00'},
      ]));
      expect(m.newAnnouncements, 1);
    });

    test('finishing the intro is remembered', () async {
      final m = _model(MemoryStore(), MockClient((_) async => http.Response('', 500)));
      await m.start();
      await m.finishIntro();
      expect((await SharedPreferences.getInstance()).getBool('introSeen'), isTrue);
      final again = _model(MemoryStore(), MockClient((_) async => http.Response('', 500)));
      await again.start();
      expect(again.introSeen, isTrue);
    });
  });

  group('reminder plan', () {
    Summary withWork(List<Map<String, dynamic>> w) => Summary({..._summary(), 'assignments': w});
    Map<String, dynamic> a(String id, String due, {bool submitted = false, bool open = true, String urgency = 'ok'}) =>
        {'id': id, 'course': 'C', 'title': id, 'due_at': due, 'submitted': submitted, 'open': open, 'urgency': urgency};
    final now = DateTime(2026, 11, 20, 12);

    test('a reminder for each lead time that is still ahead, soonest first', () {
      final p = Reminders.plan(withWork([a('x', '2026-11-21T12:30:00')]), leads: [24, 3, 1], done: {}, snoozed: {}, now: now);
      expect(p.map((r) => r.hours), [24, 3, 1].where((h) => DateTime(2026, 11, 21, 12, 30).subtract(Duration(hours: h)).isAfter(now)).toList()..sort((x, y) => y.compareTo(x)));
      expect(p.first.at.isBefore(p.last.at) || p.length == 1, isTrue);
    });

    test('nothing for submitted, closed, overdue or done work', () {
      final s = withWork([
        a('sub', '2026-11-22T10:00:00', submitted: true), a('closed', '2026-11-22T10:00:00', open: false),
        a('late', '2026-11-22T10:00:00', urgency: 'missed'), a('done', '2026-11-22T10:00:00'),
      ]);
      expect(Reminders.plan(s, leads: [3], done: {'C#done#done'}.followedBy(['done']).toSet(), snoozed: {}, now: now).map((r) => r.work.id), isNot(contains('sub')));
      expect(Reminders.plan(s, leads: [3], done: {'done'}, snoozed: {}, now: now).map((r) => r.work.id), ['closed'].where((_) => false));
    });

    test('a lead time already past is skipped, and a snooze adds one wake-up', () {
      final s = withWork([a('x', '2026-11-20T14:00:00')]);   // due in 2 hours: the 24 h and 3 h reminders are already past
      final p = Reminders.plan(s, leads: [24, 3, 1], done: {}, snoozed: {'x': DateTime(2026, 11, 20, 12, 40)}, now: now);
      expect(p.map((r) => r.hours), [null, 1]);   // the snooze wake-up (12:40) then the 1 h reminder (13:00)
    });

    test('never more than 60 are planned', () {
      final many = [for (var i = 0; i < 40; i++) a('w$i', '2026-12-30T10:00:00')];
      expect(Reminders.plan(withWork(many), leads: [48, 24, 12, 6, 3, 1], done: {}, snoozed: {}, now: now).length, 60);
    });
  });
}

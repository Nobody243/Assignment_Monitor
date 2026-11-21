import 'dart:convert';

import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/screens/portal_signin.dart';
import 'package:assignment_monitor_mobile/source.dart' show Store;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

/// A scripted portal: tracks the address and answers the few scripts the sign-in runs.
class FakeBrowser implements PortalBrowser {
  FakeBrowser({this.loginForm = true, this.acceptPassword = 'right', this.pageHtml = '<html></html>', this.error = '', this.offline = false, this.courses = const []});
  bool loginForm, offline;
  String acceptPassword, pageHtml, error;
  List<List<String>> courses;
  String current = '';
  final opened = <String>[];
  final scripts = <String>[];
  bool closed = false;

  @override
  Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)}) async {
    if (offline) throw StateError('offline');
    opened.add(url);
    current = url;
    if (url == ssoUrl) current = 'https://$lmsHost/Student/Home.php';
  }

  @override
  Future<String> url() async => current;
  @override
  Future<String> html() async => pageHtml;
  @override
  Future<void> close() async => closed = true;

  @override
  Future<dynamic> js(String s) async {
    scripts.add(s);
    if (s.contains("!!document.querySelector('#BodyPH_tbEnrollment')")) return loginForm;
    if (s.contains('btnLogin')) {
      final m = RegExp('\'#BodyPH_tbPassword\', (".*")\\);').firstMatch(s);
      if (m != null && jsonDecode(m.group(1)!) == acceptPassword) current = 'https://$cmsHost/Sys/Student/Home.aspx';
      return null;
    }
    if (s.contains('querySelectorAll(sel)')) return error;
    if (s.contains('option[value]:not')) return courses.isNotEmpty;
    if (s.contains('JSON.stringify')) return jsonEncode(courses);
    return null;
  }
}

void main() {
  const good = PortalCredentials('01-135232-062', 'right', '1');

  test('a good sign-in leaves the login page', () async {
    final b = FakeBrowser();
    final r = await Portal(b, pause: Duration.zero).signIn(good);
    expect(r.ok, isTrue);
    expect(b.opened.single, loginUrl);
  });

  test('the password is passed as a safe string, so quotes in it cannot run as code', () async {
    final b = FakeBrowser(acceptPassword: 'a"); alert(1); ("b');
    await Portal(b, pause: Duration.zero).signIn(const PortalCredentials('x', 'a"); alert(1); ("b', '1'));
    final script = b.scripts.firstWhere((s) => s.contains('btnLogin'));
    expect(script, contains(jsonEncode('a"); alert(1); ("b')));
  });

  test('a wrong password says what the portal said, and is not mistaken for a block', () async {
    final b = FakeBrowser(error: 'Invalid enrollment or password');
    final r = await Portal(b, pause: Duration.zero, signInSeconds: 0).signIn(const PortalCredentials('x', 'wrong', '1'));
    expect(r.problem, SignInProblem.wrongDetails);
    expect(r.message, 'Invalid enrollment or password');
  });

  test('a captcha on the sign-in page is reported as blocked', () async {
    final b = FakeBrowser(pageHtml: '<div class="g-recaptcha"></div>');
    final r = await Portal(b, pause: Duration.zero).signIn(good);
    expect(r.problem, SignInProblem.blocked);
  });

  test('no answer from the portal is reported as offline', () async {
    final r = await Portal(FakeBrowser(offline: true), pause: Duration.zero).signIn(good);
    expect(r.problem, SignInProblem.offline);
  });

  test('a changed login page is reported as unexpected, not as a wrong password', () async {
    final r = await Portal(FakeBrowser(loginForm: false), pause: Duration.zero).signIn(good);
    expect(r.problem, SignInProblem.unexpected);
  });

  test('the course list comes through single sign-on and is read by name', () async {
    final b = FakeBrowser(courses: [['t1', 'Data Structures'], ['t2', 'Calculus']]);
    final p = Portal(b, pause: Duration.zero);
    await p.signIn(good);
    final list = await p.courses();
    expect(list.map((c) => c.name), ['Data Structures', 'Calculus']);
    expect(b.opened, containsAllInOrder([loginUrl, ssoUrl, assignmentsUrl]));
  });

  test('only the two university hosts are portal hosts', () {
    expect(isPortalHost(cmsHost), isTrue);
    expect(isPortalHost(lmsHost), isTrue);
    expect(isPortalHost('evil.example.com'), isFalse);
    expect(isPortalHost('cms.bahria.edu.pk.evil.com'), isFalse);
    expect(isPortalHost(null), isFalse);
  });

  test('credentials are kept in the vault only, and clear removes all three', () async {
    final v = MemoryVault();
    final s = PortalStore(v);
    expect(await s.read(), isNull);
    await s.save(good);
    final back = await s.read();
    expect(back!.enrollment, good.enrollment);
    expect(back.password, 'right');
    await s.clear();
    expect(await s.read(), isNull);
  });

  test('the campus list matches the desktop app', () {
    expect(campuses.first, ('Islamabad E-8 Campus', '1'));
    expect(campuses.length, 10);
  });

  group('model and screen', () {
    AppModel make(FakeBrowser b, MemoryVault v) => AppModel(Prefs(), store: Store(vault: v), portalStore: PortalStore(v), portalFactory: () => Portal(b, pause: Duration.zero, signInSeconds: 0));

    test('details are kept only after the portal accepts them', () async {
      SharedPreferences.setMockInitialValues({});
      final v = MemoryVault();
      final bad = make(FakeBrowser(error: 'Invalid'), v);
      final r1 = await bad.connectPortal(const PortalCredentials('x', 'wrong', '1'));
      expect(r1.result.ok, isFalse);
      expect(await bad.hasPortal(), isFalse);
      final b = FakeBrowser(courses: [['a', 'One']]);
      final ok = make(b, v);
      final r2 = await ok.connectPortal(good);
      expect(r2.result.ok, isTrue);
      expect(r2.courses, 1);
      expect(await ok.hasPortal(), isTrue);
      expect(b.closed, isTrue, reason: 'the browser session is thrown away');
      await ok.forgetPortal();
      expect(await ok.hasPortal(), isFalse);
    });

    test('empty fields are refused before anything is sent', () async {
      SharedPreferences.setMockInitialValues({});
      final b = FakeBrowser();
      final m = make(b, MemoryVault());
      final r = await m.connectPortal(const PortalCredentials('', '', '1'));
      expect(r.result.ok, isFalse);
      expect(b.opened, isEmpty);
    });

    testWidgets('a captcha shows the sentence and the way out; a wrong password does not', (tester) async {
      SharedPreferences.setMockInitialValues({});
      Future<void> run(FakeBrowser b) async {
        final m = make(b, MemoryVault());
        await tester.pumpWidget(MaterialApp(home: PortalSignInPage(model: m)));
        await tester.enterText(find.byType(TextField).at(0), '01-1-1');
        await tester.enterText(find.byType(TextField).at(1), 'pw');
        await tester.tap(find.text('Sign in'));
        await tester.pumpAndSettle();
      }
      await run(FakeBrowser(pageHtml: '<div class="g-recaptcha"></div>'));
      expect(find.textContaining('captcha'), findsWidgets);
      expect(find.text('Use my GitHub cloud checks instead'), findsOneWidget);
      await run(FakeBrowser(error: 'Invalid enrollment or password'));
      expect(find.text('Invalid enrollment or password'), findsOneWidget);
      expect(find.text('Use my GitHub cloud checks instead'), findsNothing);
    });
  });
}

import 'dart:convert';
import 'dart:typed_data';

import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/portal.dart';
import 'package:assignment_monitor_mobile/screens/cloud_setup_screens.dart' show CloudSetupWizard;
import 'package:assignment_monitor_mobile/screens/portal_signin.dart';
import 'package:assignment_monitor_mobile/source.dart' show Store;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

/// A scripted portal: tracks the address and answers the few scripts the sign-in runs.
class FakeBrowser implements PortalBrowser {
  FakeBrowser({this.rejectFirst = 0, this.loginForm = true, this.acceptPassword = 'right', this.pageHtml = '<html></html>', this.error = '', this.offline = false, this.courses = const [], this.formAfter = 0});
  bool loginForm, offline;

  /// How many looks for the sign-in form find nothing before it appears (a page that is still being drawn).
  int formAfter;
  int formPolls = 0;

  /// How many sign-in clicks the portal ignores without saying why (a page that was not ready).
  int rejectFirst;
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
  Future<void> jsThenSettle(String source, {Duration timeout = const Duration(seconds: 20)}) async {}
  @override
  Future<FetchedFile> fetchFile(String url, {int maxBytes = maxDownloadBytes}) async => throw UnimplementedError();
  @override
  Future<void> attachFile(String selector, String name, String mime, Uint8List bytes) async {}
  @override
  Future<void> close() async => closed = true;

  String typed = '';
  int clicks = 0;

  @override
  Future<dynamic> js(String s) async {
    scripts.add(s);
    if (s.contains("!!document.querySelector('#BodyPH_tbEnrollment')")) return loginForm && ++formPolls > formAfter;
    if (s.contains('JSON.stringify({t:')) return '{"t":"Maintenance","i":["btnOk"]}';
    if (s.contains('readyState')) return true;
    if (s.contains("set('#BodyPH_tbPassword'")) {
      // the line is:  set('#BodyPH_tbPassword', "<json string>");
      final line = s.split('\n').firstWhere((l) => l.contains("set('#BodyPH_tbPassword'"));
      final start = line.indexOf(', ') + 2, end = line.lastIndexOf(');');
      typed = jsonDecode(line.substring(start, end)) as String;
      return null;
    }
    if (s.contains("g('#BodyPH_tbEnrollment') ===")) return true;
    if (s.contains("btnLogin').click()")) {
      clicks++;
      if (clicks > rejectFirst && typed == acceptPassword) current = 'https://$cmsHost/Sys/Student/Home.aspx';
      return null;
    }
    if (s.contains('querySelectorAll(sel)')) return error;
    if (s.contains('option[value]:not')) return courses.isNotEmpty;
    if (s.contains('JSON.stringify')) return jsonEncode(courses);
    return null;
  }
}

/// A portal whose course list only appears on the second look.
class _SlowList extends FakeBrowser {
  _SlowList({required super.courses});
  @override
  Future<dynamic> js(String s) async {
    // the list only shows once the courses page has been opened a second time
    if (s.contains('option[value]:not')) return opened.where((u) => u == assignmentsUrl).length > 1;
    return super.js(s);
  }
}

/// A browser whose scripts throw, as a platform error from the real WebView would.
class _Broken extends FakeBrowser {
  @override
  Future<dynamic> js(String s) async => throw StateError('platform error');
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
    final script = b.scripts.firstWhere((s) => s.contains("set('#BodyPH_tbPassword'"));
    expect(script, contains(jsonEncode('a"); alert(1); ("b')));
  });

  test('a browser that breaks while signing in gives an answer, not a hang or a crash', () async {
    final r = await Portal(_Broken(), pause: Duration.zero, signInSeconds: 0).signIn(good);
    expect(r.ok, isFalse);
    expect(r.problem, SignInProblem.unexpected);
  });

  test('a sign-in form that is still being drawn when the page has loaded is waited for', () async {
    final b = FakeBrowser(formAfter: 3);
    final r = await Portal(b, pause: Duration.zero, signInSeconds: 0).signIn(good);
    expect(r.ok, isTrue);
    expect(b.opened.where((u) => u == loginUrl).length, 1, reason: 'no second try was needed');
  });

  test('an account the portal says is signed in elsewhere is told so, not reported as a changed page', () async {
    final b = FakeBrowser(loginForm: false, pageHtml: '<p>This account is already logged in on another device.</p>');
    final r = await Portal(b, pause: Duration.zero, formSeconds: 0).signIn(good);
    expect(r.problem, SignInProblem.blocked);
    expect(r.message, contains('already signed in somewhere else'));
  });

  test('a first click the portal ignores without a message is tried once more, and then works', () async {
    final b = FakeBrowser(rejectFirst: 1);
    final r = await Portal(b, pause: Duration.zero, signInSeconds: 0).signIn(good);
    expect(r.ok, isTrue);
    expect(b.opened.where((u) => u == loginUrl).length, 2, reason: 'a fresh page for the second try');
  });

  test('a real rejection (the portal gave a reason) is reported at once and the password is sent only once', () async {
    final b = FakeBrowser(error: 'Invalid enrollment or password');
    final r = await Portal(b, pause: Duration.zero, signInSeconds: 0).signIn(const PortalCredentials('x', 'wrong', '1'));
    expect(r.problem, SignInProblem.wrongDetails);
    expect(b.clicks, 1);
  });

  test('two silent rejections in a row are reported, not retried forever', () async {
    final b = FakeBrowser(rejectFirst: 5);
    final r = await Portal(b, pause: Duration.zero, signInSeconds: 0).signIn(good);
    expect(r.ok, isFalse);
    expect(b.clicks, 2);
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
    final b = FakeBrowser(loginForm: false);
    final r = await Portal(b, pause: Duration.zero, formSeconds: 0).signIn(good);
    expect(r.problem, SignInProblem.unexpected);
    expect(r.message, contains('Maintenance'), reason: 'it says what the page was, so a changed page can be told from a slow one');
    expect(b.opened.where((u) => u == loginUrl).length, 2, reason: 'a page that looked wrong is looked at once more from a fresh load');
  });

  test('the course list comes through single sign-on and is read by name', () async {
    final b = FakeBrowser(courses: [['t1', 'Data Structures'], ['t2', 'Calculus']]);
    final p = Portal(b, pause: Duration.zero);
    await p.signIn(good);
    final list = await p.courses();
    expect(list.map((c) => c.name), ['Data Structures', 'Calculus']);
    expect(b.opened, containsAllInOrder([loginUrl, ssoUrl, assignmentsUrl]));
  });

  test('a course list that does not show on the first look is looked for again through single sign-on', () async {
    final b = _SlowList(courses: [['t1', 'Calculus']]);
    final p = Portal(b, pause: Duration.zero, signInSeconds: 0, listSeconds: 0);
    await p.signIn(good);
    final list = await p.courses();
    expect(list.map((c) => c.name), ['Calculus']);
    expect(b.opened.where((u) => u == ssoUrl).length, 2, reason: 'the second look signs through again');
  });

  test('a portal that never lists the courses says so, not an empty list', () async {
    final p = Portal(FakeBrowser(), pause: Duration.zero, signInSeconds: 0, listSeconds: 0);
    await p.signIn(good);
    expect(p.courses, throwsA(isA<StateError>()));
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
    AppModel make(FakeBrowser b, MemoryVault v) => AppModel(Prefs(), store: Store(vault: v), portalStore: PortalStore(v), portalFactory: ({credentials}) => Portal(b, pause: Duration.zero, signInSeconds: 0, credentials: credentials));

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

    test('the background-checks offer shows once, only in the Full app without GitHub, and stays hidden after Not now', () async {
      SharedPreferences.setMockInitialValues({});
      final m = make(FakeBrowser(), MemoryVault());
      m..portalMode = true..phase = Phase.ready..cloudOfferHidden = false;
      expect(m.offerCloud, isTrue);
      m.login = 'alex';   // GitHub is already connected
      expect(m.offerCloud, isFalse);
      m.login = null;
      await m.hideCloudOffer();
      expect(m.offerCloud, isFalse);
      expect((await SharedPreferences.getInstance()).getBool('cloudOfferHidden'), isTrue);
    });

    testWidgets('the GitHub setup opens with the saved portal login already in it', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final m = make(FakeBrowser(), MemoryVault());
      await tester.pumpWidget(MaterialApp(home: CloudSetupWizard(model: m, prefill: good)));
      final wizard = tester.state(find.byType(CloudSetupWizard)) as dynamic;
      expect(wizard.enrollment.text, good.enrollment);
      expect(wizard.campus, good.instituteId);
    });
  });
}

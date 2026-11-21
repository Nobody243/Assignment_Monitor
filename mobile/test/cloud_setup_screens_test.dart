import 'dart:convert';

import 'package:assignment_monitor_mobile/cloud_setup.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/screens/cloud_setup_screens.dart';
import 'package:assignment_monitor_mobile/screens/signin.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fake_github.dart';
import 'helpers.dart';

const fakePassword = 'fake-portal-password-for-tests';
const fakeEnrollment = '01-123456-001';

/// github.com's device flow and the account lookup, answered at once.
http.Client authClient({String login = 'student1'}) => MockClient((r) async {
      if (r.url.path == '/login/device/code') {
        return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'ABCD-1234', 'verification_uri': 'https://github.com/login/device', 'interval': 0, 'expires_in': 900}), 200);
      }
      if (r.url.path == '/login/oauth/access_token') return http.Response(jsonEncode({'access_token': 'gho_faketoken'}), 200);
      if (r.url.path == '/user') return http.Response(jsonEncode({'login': login}), 200);
      return http.Response('{}', 404);
    });

void main() {
  late FakeGithub gh;
  late MemoryStore store;
  late AppModel model;

  setUp(() {
    gh = FakeGithub();
    store = MemoryStore();
    SharedPreferences.setMockInitialValues({});
    cloudClientFactory = (t) => CloudClient(t, client: gh.client, delay: (_) async {});
    cloudAuthFactory = () => GithubAuth(authClient(), Duration.zero);
    model = AppModel(Prefs(), store: store, source: SummarySource(MockClient((_) async => http.Response('{}', 404))));
  });
  tearDown(() {
    cloudClientFactory = (token) => CloudClient(token);
    cloudAuthFactory = () => GithubAuth();
  });

  void phone(WidgetTester tester) {
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
  }

  Future<void> tapText(WidgetTester tester, String text) async {
    final f = find.text(text);
    await tester.scrollUntilVisible(f, 150, scrollable: find.byType(Scrollable).first);   // lists build only what is near the screen
    await tester.pump();
    await tester.tap(f);
    await tester.pumpAndSettle();
  }

  Future<void> toPortalPage(WidgetTester tester) async {
    await tapText(tester, 'Read-only viewer');
    await tapText(tester, 'Set up from this phone');
    expect(find.text('What this does'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Continue'), 150, scrollable: find.byType(Scrollable).first);
    expect(tester.widget<FilledButton>(find.ancestor(of: find.text('Continue'), matching: find.byWidgetPredicate((w) => w is FilledButton))).onPressed, isNull, reason: 'consent first');
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pump();
    await tapText(tester, 'Continue');
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('Your portal login'), findsOneWidget);
  }

  Future<void> fillPortal(WidgetTester tester, {String enrollment = fakeEnrollment, String password = fakePassword}) async {
    await tester.enterText(find.byType(TextField).at(0), enrollment);
    await tester.enterText(find.byType(TextField).at(1), password);
    await tester.pump();
  }

  Widget signIn() => MaterialApp(home: ListenableBuilder(listenable: model, builder: (_, _) => SignInScreen(model: model)));

  group('the wizard', () {
    testWidgets('happy path: consent, code, portal login, progress, then the waiting screen', (tester) async {
      phone(tester);
      await tester.pumpWidget(signIn());
      await tester.pumpAndSettle();
      await toPortalPage(tester);
      expect(find.text('Signed in to GitHub as student1. Now the login you use on the Bahria portal. It is encrypted here and sent to your own repository\'s secrets. It is not stored on this phone.'), findsOneWidget);

      await fillPortal(tester);
      await tapText(tester, 'Set up Cloud checks');
      await tester.pumpAndSettle();

      // the sequence ran against GitHub
      expect(gh.secrets, {secretEnrollment: fakeEnrollment, secretPassword: fakePassword});
      expect(gh.files.keys, contains(workflowPath));
      expect(gh.dispatches.single['inputs'], {'mode': 'check'});
      expect(gh.bodies.any((b) => b.contains(fakePassword)), isFalse, reason: 'the password was sent in the clear');

      // the app is signed in and waits for the first summary
      expect(store.tokenV, 'gho_faketoken');
      expect(store.loginV, 'student1');
      expect(model.phase, Phase.waiting);
      expect(model.cloudFirstCheck, isTrue);
      expect(find.text('Signed in as student1'), findsOneWidget);
      expect(find.textContaining('first check is running'), findsOneWidget);
      expect(find.text('Check now'), findsOneWidget);
      expect(find.text('What this does'), findsNothing);

      // the password is nowhere the phone keeps things, and not on screen
      for (final v in [store.tokenV, store.loginV]) {
        expect(v!.contains(fakePassword), isFalse);
      }
      final prefs = await SharedPreferences.getInstance();
      for (final k in prefs.getKeys()) {
        expect('${prefs.get(k)}'.contains(fakePassword), isFalse, reason: 'preference $k');
      }
      expect(find.textContaining(fakePassword), findsNothing);
    });

    testWidgets('a wrong enrollment number or an empty password is explained and nothing is sent', (tester) async {
      phone(tester);
      await tester.pumpWidget(signIn());
      await tester.pumpAndSettle();
      await toPortalPage(tester);
      await fillPortal(tester, enrollment: '1234', password: '');
      await tapText(tester, 'Set up Cloud checks');
      expect(find.text('Enrollment numbers look like 01-123456-001.'), findsOneWidget);
      expect(find.text('Enter your portal password.'), findsOneWidget);
      expect(gh.calls, isEmpty);
    });

    testWidgets('the password can be shown and hidden', (tester) async {
      phone(tester);
      await tester.pumpWidget(signIn());
      await tester.pumpAndSettle();
      await toPortalPage(tester);
      EditableText field() => tester.widget<EditableText>(find.byType(EditableText).at(1));
      expect(field().obscureText, isTrue);
      await tester.tap(find.byTooltip('Show password'));
      await tester.pump();
      expect(field().obscureText, isFalse);
    });

    testWidgets('a failure names the step, keeps what was done, and Retry finishes the job', (tester) async {
      phone(tester);
      gh.failures['PUT /repos/student1/assignment-monitor-cloud/actions/secrets/AM_ENROLLMENT'] = 422;
      await tester.pumpWidget(signIn());
      await tester.pumpAndSettle();
      await toPortalPage(tester);
      await fillPortal(tester);
      await tapText(tester, 'Set up Cloud checks');
      await tester.pumpAndSettle();

      expect(find.text('Setup stopped'), findsOneWidget);
      expect(find.byKey(const ValueKey('cloud-failure')), findsOneWidget);
      expect(find.textContaining('GitHub refused the request'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
      expect(model.phase, isNot(Phase.waiting), reason: 'not signed in until the setup works');
      expect(store.tokenV, isNull);
      expect(gh.files.keys, contains(workflowPath), reason: 'the steps before the failure stay done');

      gh.failures.clear();
      await tapText(tester, 'Retry');
      await tester.pumpAndSettle();
      expect(gh.secrets[secretPassword], fakePassword);
      expect(model.phase, Phase.waiting);
      expect(find.text('Signed in as student1'), findsOneWidget);
    });

    testWidgets('a GitHub sign-in that expired mid-setup offers to sign in again', (tester) async {
      phone(tester);
      gh.failures['GET /user'] = 401;
      await tester.pumpWidget(signIn());
      await tester.pumpAndSettle();
      await toPortalPage(tester);
      await fillPortal(tester);
      await tapText(tester, 'Set up Cloud checks');
      await tester.pumpAndSettle();
      expect(find.textContaining('sign-in expired'), findsOneWidget);
      expect(find.text('Sign in to GitHub again'), findsOneWidget);
    });

    testWidgets('declining on GitHub shows the reason and Try again', (tester) async {
      phone(tester);
      cloudAuthFactory = () => GithubAuth(MockClient((r) async {
            if (r.url.path == '/login/device/code') return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'ABCD-1234', 'verification_uri': 'https://github.com/login/device', 'interval': 0}), 200);
            return http.Response(jsonEncode({'error': 'access_denied'}), 200);
          }), Duration.zero);
      await tester.pumpWidget(signIn());
      await tester.pumpAndSettle();
      await tapText(tester, 'Read-only viewer');
      await tapText(tester, 'Set up from this phone');
      await tester.tap(find.byType(CheckboxListTile));
      await tester.pump();
      await tapText(tester, 'Continue');
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();
      expect(find.text('You declined the request on GitHub.'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('Settings > Cloud checks', () {
    Future<void> openPage(WidgetTester tester) async {
      store.tokenV = 'gho_faketoken';
      model.login = 'student1';
      gh.repoExists = true;
      gh.files[workflowPath] = workflowYaml();
      gh.secrets[secretEnrollment] = fakeEnrollment;
      gh.secrets[secretPassword] = 'old-fake-password';
      gh.run = {'status': 'completed', 'conclusion': 'success', 'run_started_at': DateTime.now().toUtc().subtract(const Duration(hours: 3)).toIso8601String(), 'html_url': ''};
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: CloudSettingsPage(model: model))));
      await tester.pumpAndSettle();
    }

    testWidgets('shows that it is on and how the last run went', (tester) async {
      phone(tester);
      await openPage(tester);
      expect(find.text('Cloud checks are on'), findsOneWidget);
      expect(find.textContaining('Last check worked'), findsOneWidget);
      expect(find.text('student1/assignment-monitor-cloud'), findsOneWidget);
    });

    testWidgets('Run a check now starts a full check', (tester) async {
      phone(tester);
      await openPage(tester);
      await tester.tap(find.text('Run a check now'));
      await tester.pump();
      await tester.pump(const Duration(seconds: 4));
      await tester.pumpAndSettle();
      expect(gh.dispatches.single['inputs'], {'mode': 'check'});
    });

    testWidgets('Change portal login replaces the two secrets and clears the field', (tester) async {
      phone(tester);
      await openPage(tester);
      await tester.tap(find.text('Change portal login'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(0), '02-654321-002');
      await tester.enterText(find.byType(TextField).at(1), 'new-fake-password');
      await tapText(tester, 'Save');
      await tester.pumpAndSettle();
      expect(gh.secrets[secretEnrollment], '02-654321-002');
      expect(gh.secrets[secretPassword], 'new-fake-password');
      expect(gh.bodies.any((b) => b.contains('new-fake-password')), isFalse);
      expect(find.text('Change portal login'), findsOneWidget, reason: 'back on the Cloud checks page, whose row has this name');
      expect(find.textContaining('Portal login updated'), findsOneWidget);
    });

    testWidgets('Change portal login rejects a bad enrollment without calling GitHub', (tester) async {
      phone(tester);
      await openPage(tester);
      final before = gh.calls.length;
      await tester.tap(find.text('Change portal login'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(0), 'nope');
      await tester.enterText(find.byType(TextField).at(1), 'x');
      await tapText(tester, 'Save');
      expect(find.text('Enrollment numbers look like 01-123456-001.'), findsOneWidget);
      expect(gh.calls.length, before);
    });

    testWidgets('Turn off asks first, then removes the secrets and the workflow', (tester) async {
      phone(tester);
      await openPage(tester);
      await tester.tap(find.text('Turn off'));
      await tester.pumpAndSettle();
      expect(find.text('Turn off Cloud checks?'), findsOneWidget);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(gh.secrets, isNotEmpty, reason: 'cancel changes nothing');

      await tester.tap(find.text('Turn off'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Turn off'));
      await tester.pumpAndSettle();
      expect(gh.secrets, isEmpty);
      expect(gh.files.containsKey(workflowPath), isFalse);
      expect(find.text('Not set up from this phone'), findsOneWidget);
    });

    testWidgets('a sign-in that cannot see the workflow is offered the setup, not an error', (tester) async {
      phone(tester);
      store.tokenV = 'gho_faketoken';
      model.login = 'student1';
      gh.repoExists = true;       // no workflow file: a desktop-managed or read-only sign-in
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: CloudSettingsPage(model: model))));
      await tester.pumpAndSettle();
      expect(find.text('Not set up from this phone'), findsOneWidget);
      expect(find.text('Set up Cloud checks'), findsOneWidget);
    });
  });
}

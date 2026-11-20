import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:assignment_monitor_mobile/cloud_setup.dart';
import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/screens/cloud_setup_screens.dart';
import 'package:assignment_monitor_mobile/screens/signin.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:assignment_monitor_mobile/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fake_github.dart';
import 'helpers.dart';

/// Quality checks that go beyond single features:
///  - the contract: summary files that are empty, sparse or damaged still read and draw on every screen;
///  - layout: every screen fits a small phone at large text sizes, in light and dark, with a real font;
///  - contrast: the text and status colours stay readable in all four palettes.
const _sections = ['Today', 'Assignments', 'Attendance', 'Exams', 'Announcements', 'Timetable', 'Results & GPA', 'Settings'];

Directory? _fontDir() {
  final root = Platform.environment['FLUTTER_ROOT'] ?? 'C:/src/flutter';
  final dir = Directory('$root/bin/cache/artifacts/material_fonts');
  return dir.existsSync() ? dir : null;
}

/// The layout checks only mean something with the real font (the test default is a very wide stand-in), so they are
/// skipped, with a note, where the Flutter SDK's Roboto cannot be found.
final _roboto = _fontDir();

Future<void> _loadRoboto() async {
  final dir = _roboto;
  if (dir == null) return;
  final loader = FontLoader('Roboto');
  for (final f in ['Roboto-Regular.ttf', 'Roboto-Medium.ttf', 'Roboto-Bold.ttf']) {
    final file = File('${dir.path}/$f');
    if (file.existsSync()) loader.addFont(Future.value(ByteData.sublistView(file.readAsBytesSync())));
  }
  await loader.load();
}

/// Fails with what overflowed and where, not just that something did.
void _noException(WidgetTester tester, String reason) {
  final e = tester.takeException();
  if (e == null) return;
  final text = e is FlutterError ? (e.diagnostics.map((d) => d.toStringDeep()).join(' | ')) : '$e';
  final where = RegExp(r'[a-z_/]+\.dart:\d+:\d+').allMatches(Uri.decodeFull(text)).map((m) => m.group(0)).toSet().take(3).join(', ');
  fail('$reason: $text ($where)');
}

Summary _fixture(String name) => Summary(jsonDecode(File('test/fixtures/summary_$name.json').readAsStringSync()) as Map<String, dynamic>);

void main() {
  setUpAll(_loadRoboto);

  Future<void> boot(WidgetTester tester, Summary s, {double textScale = 1, Brightness brightness = Brightness.dark, Size size = const Size(360, 740)}) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = Size(size.width * 3, size.height * 3);
    addTearDown(tester.view.reset);
    final prefs = Prefs();
    final model = AppModel(prefs)..summary = s..demo = true;
    await tester.pumpWidget(MaterialApp(
      theme: buildTheme(palettes.first, brightness),
      builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)), child: child!),
      home: Shell(model: model, prefs: prefs),
    ));
    await tester.pump(const Duration(milliseconds: 600));
  }

  Future<void> open(WidgetTester tester, String section) async {
    if (section == 'Today') return;
    await tester.tap(find.byTooltip('Menu'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text(section).first);   // at a large text size the menu scrolls
    await tester.pumpAndSettle();
    await tester.tap(find.text(section).first);
    await tester.pumpAndSettle();
    expect(find.descendant(of: find.byType(AppBar), matching: find.text(section)), findsOneWidget, reason: '$section did not open');
  }

  group('contract: awkward summary files', () {
    for (final name in ['empty', 'sparse']) {
      test('$name: every reader returns instead of throwing', () {
        final s = _fixture(name);
        expect(() {
          s.generatedAt; s.lastCheck; s.studentName; s.firstName; s.semester; s.minimum; s.cgpa;
          for (final w in s.work) { w.id; w.title; w.course; w.due; w.todo; w.overdue; w.marks; w.wasDue; }
          for (final c in s.attendance) { c.percent; c.present; c.absent; c.canMiss; c.need; c.ok; c.recorded; c.classHours; c.classes; c.credit; }
          for (final e in s.exams) { e.day; e.title; e.room; e.row; e.seat; e.time; }
          for (final c in s.timetable) { c.day; c.start; c.end; c.course; }
          for (final n in s.announcements) { n.id; n.title; n.text; n.postedAt; }
          for (final t in s.terms) { t.name; t.gpa; t.cgpa; t.complete; for (final c in t.courses) { c.code; c.title; c.credits; c.grade; } }
        }, returnsNormally);
      });

      for (final section in _sections) {
        testWidgets('$name: $section draws', (tester) async {
          await boot(tester, _fixture(name));
          await open(tester, section);
          _noException(tester, 'drawing');
        });
      }
    }
    test('classes without a weekday or readable times are left off the timetable', () {
      final s = _fixture('sparse');
      expect(s.timetable.map((c) => c.course), ['Fine']);
    });
  });

  group('layout: a small phone, large text, light and dark', skip: _roboto == null ? 'the SDK Roboto font was not found' : null, () {
    for (final scale in [1.0, 1.5, 2.0]) {
      for (final b in [Brightness.light, Brightness.dark]) {
        testWidgets('all sections at ${(scale * 100).round()}% text, ${b.name}', (tester) async {
          final s = (await tester.runAsync(Summary.load))!;
          await boot(tester, s, textScale: scale, brightness: b);
          for (final section in _sections) {
            await open(tester, section);
            _noException(tester, '$section overflowed at ${(scale * 100).round()}% text in ${b.name}');
            if (section == 'Settings') {
              for (final page in ['Reminders', 'Appearance', 'Calendar', 'Security', 'Account and data', 'About and privacy']) {
                await tester.ensureVisible(find.text(page));
                await tester.tap(find.text(page));
                await tester.pumpAndSettle();
                _noException(tester, 'Settings, $page overflowed at ${(scale * 100).round()}% text in ${b.name}');
                await tester.pageBack();
                await tester.pumpAndSettle();
              }
            }
            if (section == 'Results & GPA') {
              await tester.tap(find.text('Calculator'));
              await tester.pumpAndSettle();
              _noException(tester, 'the calculator overflowed at ${(scale * 100).round()}% text in ${b.name}');
            }
          }
        });
      }
    }
  });

  // The phone-only setup (wizard, Cloud checks in Settings, change portal login) at the same sizes: a small phone, large text.
  group('layout: phone-only setup screens', skip: _roboto == null ? 'the SDK Roboto font was not found' : null, () {
    for (final scale in [1.0, 1.5, 2.0]) {
      for (final b in [Brightness.light, Brightness.dark]) {
        final label = '${(scale * 100).round()}% text, ${b.name}';
        testWidgets('wizard, Cloud checks page and change login at $label', (tester) async {
          SharedPreferences.setMockInitialValues({});
          tester.view.devicePixelRatio = 3;
          tester.view.physicalSize = const Size(360 * 3, 740 * 3);
          addTearDown(tester.view.reset);
          final gh = FakeGithub();
          cloudClientFactory = (t) => CloudClient(t, client: gh.client, delay: (_) async {});
          addTearDown(() { cloudClientFactory = (t) => CloudClient(t); cloudAuthFactory = () => GithubAuth(); });
          final store = MemoryStore()..tokenV = 'gho_faketoken'..loginV = 'student1';
          final model = AppModel(Prefs(), store: store, source: SummarySource(MockClient((_) async => http.Response('{}', 404))))..login = 'student1';

          Future<void> show(Widget home) async {
            await tester.pumpWidget(MaterialApp(
              key: UniqueKey(),   // a new app each time: MaterialApp keeps its first home route when only `home` changes
              theme: buildTheme(palettes.first, b),
              builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(scale)), child: child!),
              home: home,
            ));
            await tester.pump(const Duration(milliseconds: 300));
          }
          Future<void> tapText(String text) async {
            await tester.scrollUntilVisible(find.text(text), 150, scrollable: find.byType(Scrollable).first);
            await tester.ensureVisible(find.text(text));   // all of it, not just its edge
            await tester.pump(const Duration(milliseconds: 50));
            await tester.tap(find.text(text));
            await tester.pump(const Duration(milliseconds: 400));
          }

          // sign-in screen with the new entry, the first wizard page, and the GitHub code page (never approved)
          cloudAuthFactory = () => GithubAuth(MockClient((r) async {
                if (r.url.path == '/login/device/code') return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'ABCD-1234', 'verification_uri': 'https://github.com/login/device', 'interval': 1, 'expires_in': 900}), 200);
                return http.Response(jsonEncode({'error': 'authorization_pending'}), 200);
              }));
          await show(ListenableBuilder(listenable: model, builder: (_, _) => SignInScreen(model: model)));
          _noException(tester, 'the sign-in screen overflowed at $label');
          await tapText('Set up from this phone');
          await tester.pumpAndSettle();
          _noException(tester, 'the wizard intro overflowed at $label');
          await tester.scrollUntilVisible(find.byType(CheckboxListTile), 150, scrollable: find.byType(Scrollable).first);
          await tester.ensureVisible(find.byType(CheckboxListTile));
          await tester.pumpAndSettle();
          await tester.tap(find.byType(CheckboxListTile));
          await tester.pump();
          await tapText('Continue');
          await tester.pump(const Duration(milliseconds: 300));
          _noException(tester, 'the GitHub code page overflowed at $label');
          await tapText('Cancel');
          await tester.pump(const Duration(seconds: 6));   // lets the waiting loop see it was cancelled
          await show(const SizedBox());

          // portal login page, then a failed setup (the failure view with Retry)
          cloudAuthFactory = () => GithubAuth(MockClient((r) async {
                if (r.url.path == '/login/device/code') return http.Response(jsonEncode({'device_code': 'dc', 'user_code': 'ABCD-1234', 'verification_uri': 'https://github.com/login/device', 'interval': 0}), 200);
                if (r.url.path == '/login/oauth/access_token') return http.Response(jsonEncode({'access_token': 'gho_faketoken'}), 200);
                return http.Response(jsonEncode({'login': 'student1'}), 200);
              }), Duration.zero);
          gh.failures['PUT /repos/student1/assignment-monitor-cloud/actions/secrets/AM_ENROLLMENT'] = 422;
          await show(CloudSetupWizard(model: model));
          await tester.scrollUntilVisible(find.byType(CheckboxListTile), 150, scrollable: find.byType(Scrollable).first);
          await tester.ensureVisible(find.byType(CheckboxListTile));
          await tester.pumpAndSettle();
          await tester.tap(find.byType(CheckboxListTile));
          await tester.pump();
          await tapText('Continue');
          await tester.pump(const Duration(seconds: 1));
          await tester.pumpAndSettle();
          _noException(tester, 'the portal login page overflowed at $label');
          await tester.enterText(find.byType(TextField).at(0), '01-123456-001');
          await tester.enterText(find.byType(TextField).at(1), 'fake-portal-password-for-tests');
          await tester.pump();
          await tapText('Set up Cloud checks');
          await tester.pumpAndSettle();
          expect(find.text('Retry'), findsOneWidget);
          _noException(tester, 'the setup failure page overflowed at $label');
          await show(const SizedBox());

          // Settings > Cloud checks: on (with a last run), then the change-login page, then off
          gh.failures.clear();
          gh.repoExists = true;
          gh.files[workflowPath] = workflowYaml();
          gh.run = {'status': 'completed', 'conclusion': 'failure', 'run_started_at': DateTime.now().toUtc().subtract(const Duration(hours: 5)).toIso8601String(), 'html_url': ''};
          await show(Scaffold(body: CloudSettingsPage(model: model)));
          await tester.pumpAndSettle();
          expect(find.text('Cloud checks are on'), findsOneWidget);
          _noException(tester, 'Cloud checks (on) overflowed at $label');
          await tapText('Change portal login');
          await tester.pumpAndSettle();
          _noException(tester, 'Change portal login overflowed at $label');
          await show(const SizedBox());
          gh.files.remove(workflowPath);
          await show(Scaffold(body: CloudSettingsPage(model: model)));
          await tester.pumpAndSettle();
          expect(find.text('Not set up from this phone'), findsOneWidget);
          _noException(tester, 'Cloud checks (off) overflowed at $label');
        });
      }
    }
  });

  group('layout: other screen shapes',skip: _roboto == null ? 'the SDK Roboto font was not found' : null, () {
    for (final (name, size) in [('a phone on its side', const Size(800, 360)), ('a small tablet', const Size(800, 1280)), ('a large tablet on its side', const Size(1280, 800)), ('a narrow phone', const Size(320, 640))]) {
      testWidgets('$name: every section fits and the content stays in a column', (tester) async {
        final s = (await tester.runAsync(Summary.load))!;
        await boot(tester, s, size: size);
        for (final section in _sections) {
          await open(tester, section);
          _noException(tester, '$section overflowed on $name');
        }
        // wide screens keep the content a readable column, not edge to edge
        final content = tester.getSize(find.byType(AnimatedSwitcher).last).width;
        expect(content, lessThanOrEqualTo(maxContentWidth + 0.5), reason: 'the content is $content px wide on $name');
      });
    }
  });

  group('contrast: WCAG ratios', () {
    double lum(Color c) {
      double ch(double v) => v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
      return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
    }
    double ratio(Color a, Color b) {
      final x = lum(a), y = lum(b);
      return (math.max(x, y) + 0.05) / (math.min(x, y) + 0.05);
    }

    for (final p in palettes) {
      for (final b in [Brightness.light, Brightness.dark]) {
        test('${p.label} ${b.name}: body text, secondary text, accent and status colours', () {
          final c = buildTheme(p, b).colorScheme;
          final pairs = <String, (Color, Color)>{
            'text on page': (c.onSurface, c.surface),
            'text on card': (c.onSurface, c.surfaceContainer),
            'secondary text on page': (c.onSurfaceVariant, c.surface),
            'secondary text on card': (c.onSurfaceVariant, c.surfaceContainer),
            'secondary text on tile': (c.onSurfaceVariant, c.surfaceContainerHigh),
            'text on the hero': (c.onPrimaryContainer, c.primaryContainer),
            'text on the accent button': (c.onPrimary, c.primary),
            'good on card': (Status.good(b), c.surfaceContainer),
            'warning on card': (Status.warn(b), c.surfaceContainer),
            'bad on card': (Status.bad(b), c.surfaceContainer),
            'good on page': (Status.good(b), c.surface),
            'bad on page': (Status.bad(b), c.surface),
          };
          final failures = [for (final e in pairs.entries) if (ratio(e.value.$1, e.value.$2) < 4.5) '${e.key}: ${ratio(e.value.$1, e.value.$2).toStringAsFixed(2)}'];
          expect(failures, isEmpty, reason: '${p.label} ${b.name} below 4.5:1');
        });
      }
    }
  });
}

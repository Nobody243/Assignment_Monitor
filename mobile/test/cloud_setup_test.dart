import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:assignment_monitor_mobile/cloud_setup.dart';
import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pinenacl/x25519.dart';

import 'fake_github.dart';

const fakePassword = 'fake-portal-password-for-tests';
const fakeEnrollment = '01-123456-001';

CloudSetup setupFor(FakeGithub gh) => CloudSetup(CloudClient('gho_faketoken', client: gh.client, delay: (_) async {}));

void main() {
  group('sealed box', () {
    final fx = jsonDecode(File('test/fixtures/sealed_box.json').readAsStringSync()) as Map<String, dynamic>;
    final sk = PrivateKey(Uint8List.fromList(base64Decode(fx['private_key'] as String)));

    test('opens a box that libsodium sealed (the format GitHub expects)', () {
      final plain = SealedBox(sk).decrypt(Uint8List.fromList(base64Decode(fx['sealed_by_libsodium'] as String)));
      expect(utf8.decode(plain), fx['plaintext']);
    });

    test('a box sealed here has the libsodium layout and opens with the private key', () {
      final sealed = base64Decode(sealSecret(fx['public_key'] as String, fakePassword));
      expect(sealed.length, 32 + 16 + utf8.encode(fakePassword).length);   // ephemeral key + MAC + message
      expect(utf8.decode(SealedBox(sk).decrypt(Uint8List.fromList(sealed))), fakePassword);
    });

    test('is random each time and never contains the value', () {
      final a = sealSecret(fx['public_key'] as String, fakePassword), b = sealSecret(fx['public_key'] as String, fakePassword);
      expect(a, isNot(b));
      expect(a.contains(fakePassword), isFalse);
      expect(utf8.decode(base64Decode(a), allowMalformed: true).contains(fakePassword), isFalse);
    });

    test('a key that is not 32 bytes is refused in words', () {
      expect(() => sealSecret(base64Encode([1, 2, 3]), 'x'), throwsA(isA<CloudError>()));
      expect(() => sealSecret('not base64 !!', 'x'), throwsA(isA<CloudError>()));
    });
  });

  group('the workflow file', () {
    test('is the one the desktop writes, character for character', () {
      final expected = File('test/fixtures/cloud_workflow.yml').readAsStringSync();
      expect(workflowYaml(), expected);
    });

    test('pins the runner release and keeps the schedule', () {
      final y = workflowYaml();
      expect(y, contains('ref: v$cloudRunnerVersion'));
      expect(y, contains('cron: "43 2 * * *"'));
      expect(y, contains('cron: "37 13 * * *"'));
      expect(y, contains(r'AM_PASSWORD: ${{ secrets.AM_PASSWORD }}'));
    });

    test('a campus and other settings land as quoted values, and are read back', () {
      final y = workflowYaml(plain: {'INSTITUTE_ID': '3', 'EMAIL_TO': 'a@b.c', 'EMAIL_ENABLED': 'True'});
      expect(y, contains('AM_INSTITUTE_ID: "3"'));
      final back = parsePlainValues(y);
      expect(back['INSTITUTE_ID'], '3');
      expect(back['EMAIL_TO'], 'a@b.c');
      expect(back['EMAIL_PORT'], '587');
      expect(back.containsKey('PASSWORD'), isFalse);
    });
  });

  group('input checks', () {
    test('enrollment looks like the desktop rule', () {
      expect(enrollmentProblem('01-123456-001'), isNull);
      expect(enrollmentProblem(' 01-123456-001 '), isNull);
      expect(enrollmentProblem(''), isNotNull);
      expect(enrollmentProblem('1234'), isNotNull);
      expect(enrollmentProblem('01-12345-001'), isNotNull);
      expect(passwordProblem(''), isNotNull);
      expect(passwordProblem('x'), isNull);
    });
  });

  group('setup against a fake GitHub', () {
    test('runs the whole sequence with the exact calls, sealed secrets and a verify run', () async {
      final gh = FakeGithub();
      final steps = <String>[];
      final r = await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '3', progress: (s, d) => steps.add('${s.name}${d ? ' done' : ''}'));
      expect(r.repo, 'student1/assignment-monitor-cloud');
      expect(r.runUrl, 'https://github.com/student1/assignment-monitor-cloud/actions');
      expect(steps, ['repo', 'repo done', 'workflow', 'workflow done', 'secrets', 'secrets done', 'check', 'check done']);

      // the order of the calls: release check, account, repository, files, secrets, dispatch
      final c = gh.calls;
      expect(c.first, 'GET /repos/Nobody243/Assignment_Monitor/git/ref/tags/v$cloudRunnerVersion');
      expect(c.indexOf('GET /user'), lessThan(c.indexOf('POST /user/repos')));
      expect(c.where((x) => x == 'POST /user/repos').length, 1);
      expect(c.indexOf('PUT /repos/${gh.repo}/contents/.github/workflows/check.yml'), lessThan(c.indexOf('GET /repos/${gh.repo}/actions/secrets/public-key')));
      expect(c.last, 'POST /repos/${gh.repo}/actions/workflows/check.yml/dispatches');

      expect(gh.files.keys, containsAll(['README.md', '.gitignore', workflowPath]));
      expect(gh.files[workflowPath], workflowYaml(plain: {'INSTITUTE_ID': '3'}));
      expect(gh.files['README.md'], contains("student1's Assignment Monitor setup"));

      expect(gh.secrets, {secretEnrollment: fakeEnrollment, secretPassword: fakePassword});
      expect(gh.dispatches.single, {'ref': 'main', 'inputs': {'mode': 'verify'}});
    });

    test('the password only ever leaves the phone sealed', () async {
      final gh = FakeGithub();
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      for (final b in gh.bodies) {
        expect(b.contains(fakePassword), isFalse, reason: 'a request body held the password in the clear');
      }
      for (final f in gh.files.values) {
        expect(f.contains(fakePassword), isFalse);
      }
      expect(gh.sealedAsSent[secretPassword], isNot(fakePassword));
      expect(gh.sealedAsSent[secretPassword]!.contains(fakePassword), isFalse);
      expect(gh.calls.any((c) => c.contains(fakePassword)), isFalse);
    });

    test('can run again: nothing is made twice and unchanged files are not rewritten', () async {
      final gh = FakeGithub();
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      final before = gh.calls.length;
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      final second = gh.calls.sublist(before);
      expect(second.where((x) => x == 'POST /user/repos'), isEmpty);
      expect(second.where((x) => x.startsWith('PUT /repos/${gh.repo}/contents/') && !x.endsWith('README.md')), isEmpty);
      expect(second.where((x) => x.contains('/actions/secrets/AM_') && x.startsWith('PUT')).length, 2);
      expect(gh.dispatches.length, 2);
    });

    test('an existing repository is reused, and the branch it really has is used for the run', () async {
      final gh = FakeGithub()..repoExists = true..branch = 'trunk';
      gh.files['README.md'] = 'hello';
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      expect(gh.calls.where((x) => x == 'POST /user/repos'), isEmpty);
      expect(gh.dispatches.single['ref'], 'trunk');
    });

    test('an existing desktop workflow keeps its email and tracking choices; only the campus changes', () async {
      final gh = FakeGithub()..repoExists = true;
      gh.files[workflowPath] = workflowYaml(plain: {'EMAIL_ENABLED': 'True', 'EMAIL_TO': 'me@example.com', 'TRACK_RESULTS': 'False', 'INSTITUTE_ID': '1'});
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '2');
      final y = gh.files[workflowPath]!;
      expect(y, contains('AM_EMAIL_TO: "me@example.com"'));
      expect(y, contains('AM_TRACK_RESULTS: "False"'));
      expect(y, contains('AM_INSTITUTE_ID: "2"'));
    });

    test('a public repository of that name is refused, and nothing is written to it', () async {
      final gh = FakeGithub()..repoExists = true..repoPrivate = false;
      await expectLater(setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1'),
          throwsA(isA<CloudError>().having((e) => e.message, 'message', contains('public')).having((e) => e.step, 'step', CloudStep.repo)));
      expect(gh.calls.any((c) => c.startsWith('PUT')), isFalse);
      expect(gh.secrets, isEmpty);
    });

    test('a runner release that is not published stops everything before the repository is touched', () async {
      final gh = FakeGithub()..tagExists = false;
      await expectLater(setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1'),
          throwsA(isA<CloudError>().having((e) => e.message, 'message', contains('v$cloudRunnerVersion'))));
      expect(gh.calls, ['GET /repos/Nobody243/Assignment_Monitor/git/ref/tags/v$cloudRunnerVersion']);
    });

    test('a workflow GitHub does not know yet is retried before the first check is reported failed', () async {
      final gh = FakeGithub()..dispatch404s = 3;
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      expect(gh.dispatches.length, 1);
    });

    test('a first check that never starts is reported at the last step, with the rest already done', () async {
      final gh = FakeGithub()..dispatch404s = 99;
      await expectLater(setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1'),
          throwsA(isA<CloudError>().having((e) => e.step, 'step', CloudStep.check)));
      expect(gh.secrets.keys, containsAll([secretEnrollment, secretPassword]));
    });

    for (final (status, text, step) in [
      (401, 'expired', CloudStep.repo),
      (403, 'did not allow', CloudStep.workflow),
      (422, 'refused', CloudStep.secrets),
    ]) {
      test('a $status from GitHub is explained in words and names the step', () async {
        final gh = FakeGithub();
        gh.failures[switch (step) {
          CloudStep.repo => 'GET /user',
          CloudStep.workflow => 'PUT /repos/student1/assignment-monitor-cloud/contents/.github',
          _ => 'PUT /repos/student1/assignment-monitor-cloud/actions/secrets/AM_ENROLLMENT',
        }] = status;
        await expectLater(setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1'),
            throwsA(isA<CloudError>().having((e) => e.message, 'message', contains(text)).having((e) => e.status, 'status', status).having((e) => e.step, 'step', step)));
      });
    }

    test('a rate limit says to wait', () async {
      final gh = FakeGithub();
      gh.failures['GET /user'] = 403;
      gh.failHeaders = {'x-ratelimit-remaining': '0'};
      await expectLater(setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1'),
          throwsA(isA<CloudError>().having((e) => e.message, 'message', contains('limiting'))));
    });

    test('no connection is explained, and no exception text (which can quote a request) is kept', () async {
      final client = MockClient((r) async => throw http.ClientException('boom $fakePassword', r.url));
      final s = CloudSetup(CloudClient('gho_faketoken', client: client, delay: (_) async {}));
      try {
        await s.run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
        fail('should have thrown');
      } on CloudError catch (e) {
        expect(e.message, contains('No connection'));
        expect(e.toString().contains(fakePassword), isFalse);
      }
    });

    test('nothing the student typed or any token appears in an error, a log line or a stored value', () async {
      final logs = <String>[];
      final gh = FakeGithub()..failures['PUT /repos/student1/assignment-monitor-cloud/actions/secrets/AM_PASSWORD'] = 422;
      gh.failBody = {'message': 'Validation failed, echoing $fakePassword'};
      final before = DebugPrintCapture.start(logs);
      String text = '';
      try {
        await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      } on CloudError catch (e) {
        text = '${e.message} ${e.toString()} ${e.status} ${e.step}';
      }
      before();
      expect(text, isNotEmpty);
      expect(text.contains(fakePassword), isFalse);
      expect(text.contains('gho_faketoken'), isFalse);
      expect(logs.join('\n').contains(fakePassword), isFalse);
      expect(gh.files.values.any((f) => f.contains(fakePassword)), isFalse);
    });
  });

  group('after setup', () {
    test('changing the portal login writes only the two secrets, sealed', () async {
      final gh = FakeGithub();
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      gh.secrets['AM_PUSH_SUB'] = 'desktop-managed';
      final before = gh.calls.length;
      await setupFor(gh).changeLogin(repo: gh.repo, enrollment: '02-654321-002', password: 'another-fake-password');
      expect(gh.secrets[secretEnrollment], '02-654321-002');
      expect(gh.secrets[secretPassword], 'another-fake-password');
      expect(gh.secrets['AM_PUSH_SUB'], 'desktop-managed');
      expect(gh.calls.sublist(before).where((c) => c.startsWith('PUT')).length, 2);
      expect(gh.bodies.any((b) => b.contains('another-fake-password')), isFalse);
    });

    test('run a check now dispatches a full check on the real default branch', () async {
      final gh = FakeGithub()..repoExists = true..branch = 'trunk';
      await setupFor(gh).runNow(gh.repo);
      expect(gh.dispatches.single, {'ref': 'trunk', 'inputs': {'mode': 'check'}});
    });

    test('status says off when there is no workflow, and on with the last run when there is', () async {
      final gh = FakeGithub()..repoExists = true;
      final c = CloudClient('t', client: gh.client, delay: (_) async {});
      expect((await c.status('student1')).enabled, isFalse);
      gh.files[workflowPath] = workflowYaml();
      gh.run = {'status': 'completed', 'conclusion': 'success', 'run_started_at': '2026-11-20T02:43:00Z', 'html_url': 'https://github.com/x/y/actions/runs/1'};
      final st = await c.status('student1');
      expect(st.enabled, isTrue);
      expect(st.run!.ok, isTrue);
      expect(st.run!.running, isFalse);
      gh.run = {'status': 'in_progress', 'conclusion': null, 'created_at': '2026-11-20T02:43:00Z', 'html_url': ''};
      expect((await c.status('student1')).run!.running, isTrue);
    });

    test('turning off removes every secret and the workflow, and keeps the repository', () async {
      final gh = FakeGithub();
      await setupFor(gh).run(enrollment: fakeEnrollment, password: fakePassword, campusId: '1');
      gh.secrets['AM_PUSH_SUB'] = 'x';
      final url = await setupFor(gh).teardown(gh.repo);
      expect(url, 'https://github.com/${gh.repo}/settings');
      expect(gh.secrets, isEmpty);
      expect(gh.files.containsKey(workflowPath), isFalse);
      expect(gh.repoExists, isTrue);
      expect(gh.calls.where((c) => c.startsWith('DELETE /repos/${gh.repo}') && !c.contains('/secrets/') && !c.contains('/contents/')), isEmpty);
    });

    test('device flow asks for the wider scope only when told to', () async {
      final seen = <String>[];
      final client = MockClient((r) async {
        seen.add(r.body);
        return http.Response(jsonEncode({'device_code': 'd', 'user_code': 'ABCD-1234', 'verification_uri': 'https://github.com/login/device'}), 200);
      });
      final auth = GithubAuth(client);
      await auth.start();
      await auth.start(scope: 'repo workflow');
      expect(seen[0], contains('scope=repo'));
      expect(seen[0], isNot(contains('workflow')));
      expect(Uri.splitQueryString(seen[1])['scope'], 'repo workflow');
    });
  });
}

/// Captures debugPrint output for the length of a test.
class DebugPrintCapture {
  static void Function() start(List<String> into) {
    final old = debugPrint;
    debugPrint = (String? m, {int? wrapWidth}) => into.add(m ?? '');
    return () => debugPrint = old;
  }
}

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:pinenacl/x25519.dart';

import 'source.dart' show repoName;

/// The phone-only setup of Cloud checks: everything the desktop app's `cloud.py` does, done from the phone, so a student
/// with only the phone can have the same private repository, the same scheduled workflow and the same `state/summary.json`.
///
/// The portal password is typed once, sealed on the phone with the repository's public key (a libsodium sealed box) and sent
/// over HTTPS to GitHub's secrets store. It is never stored on the phone, never logged and never part of an error message:
/// it is only ever an argument that goes straight into [sealSecret], and nothing in this file keeps it.
///
/// This file has no UI. It takes an [http.Client] so tests run it against a fake GitHub.

/// The desktop release the workflow checks out (`ref: v<version>`). It must be a release whose `cloud_check.py` writes
/// `state/summary.json` (schema 1), which is what this app reads; older runners do not. Raise it together with the desktop.
const cloudRunnerVersion = '1.9.0';

const _projectRepo = 'Nobody243/Assignment_Monitor';
const _siteUrl = 'https://assignment-monitor.saaddev.top';
const _appName = 'Assignment Monitor';
const workflowPath = '.github/workflows/check.yml';
const _workflowFile = 'check.yml';

/// The repository secrets the runner reads. The phone only ever writes the first two; the others belong to the desktop's
/// push and email channels and are left alone unless Cloud checks is turned off.
const secretEnrollment = 'AM_ENROLLMENT';
const secretPassword = 'AM_PASSWORD';
const allSecretNames = [secretEnrollment, secretPassword, 'AM_PUSH_SUB', 'AM_PUSH_VAPID', 'AM_EMAIL_PASS'];

/// (display name, CMS institute id), the same list and order as the desktop's setup.
const cloudCampuses = <(String, String)>[
  ('Islamabad E-8 Campus', '1'),
  ('Islamabad H-11 Campus', '9'),
  ('Karachi Campus', '2'),
  ('Lahore Campus', '3'),
  ('Health Sciences Campus (Islamabad)', '12'),
  ('Health Sciences Campus (Karachi)', '6'),
  ('Bahria University College of Nursing', '13'),
  ('IPP (Karachi)', '5'),
  ('NCMPR', '4'),
  ('ODL', '14'),
];

/// The non-secret settings written into the workflow file, with the desktop's defaults (in the desktop's order).
const _plainDefaults = <(String, String)>[
  ('INSTITUTE_ID', '1'),
  ('NOTIFY_DAYS_AHEAD', '3'),
  ('ATTENDANCE_MIN', '75'),
  ('EXAM_REMIND_DAYS', '1'),
  ('TRACK_ATTENDANCE', 'True'),
  ('TRACK_EXAMS', 'True'),
  ('TRACK_ANNOUNCEMENTS', 'True'),
  ('TRACK_LECTURES', 'True'),
  ('TRACK_TIMETABLE', 'True'),
  ('TRACK_RESULTS', 'True'),
  ('PUSH_ENABLED', 'False'),
  ('EMAIL_ENABLED', 'False'),
  ('EMAIL_TO', ''),
  ('EMAIL_USER', ''),
  ('EMAIL_HOST', ''),
  ('EMAIL_PORT', '587'),
];

/// Enrollment numbers look like 01-123456-001 (the desktop's rule). Null when fine, else what is wrong.
String? enrollmentProblem(String raw) {
  final v = raw.trim();
  if (v.isEmpty) return 'Enter your enrollment number.';
  if (!RegExp(r'^\d{2}-\d{6}-\d{3}$').hasMatch(v)) return 'Enrollment numbers look like 01-123456-001.';
  return null;
}

String? passwordProblem(String raw) => raw.isEmpty ? 'Enter your portal password.' : null;

/// The step of the setup that was running; also what the progress screen lists.
enum CloudStep { repo, workflow, secrets, check }

typedef CloudProgress = void Function(CloudStep step, bool done);

/// Something GitHub refused or could not do, in words for the student. The message never holds a request body, a secret,
/// a token or the text GitHub sent back; only the step and the status code are kept.
class CloudError implements Exception {
  CloudError(this.message, {this.status, this.step});
  final String message;
  final int? status;
  CloudStep? step;
  @override
  String toString() => message;
}

/// Encrypts [value] for GitHub with the repository's public key (base64): a libsodium `crypto_box_seal`, returned base64.
String sealSecret(String publicKeyBase64, String value) {
  final Uint8List raw;
  try {
    raw = base64Decode(publicKeyBase64);
  } catch (_) {
    throw CloudError('GitHub sent a key the phone cannot read.');
  }
  if (raw.length != 32) throw CloudError('GitHub sent a key the phone cannot read.');
  final sealed = SealedBox(PublicKey(raw)).encrypt(Uint8List.fromList(utf8.encode(value)));
  return base64Encode(sealed);
}

/// The workflow the desktop writes (`workflow_yaml` in cloud.py), character for character. [plain] holds the non-secret
/// settings by their short name (INSTITUTE_ID ...); anything missing falls back to the desktop's default.
String workflowYaml({String version = cloudRunnerVersion, Map<String, String> plain = const {}}) {
  final plainEnv = [for (final (k, d) in _plainDefaults) '          AM_$k: ${jsonEncode(plain[k] ?? d)}'].join('\n');
  final secretsEnv = [for (final k in allSecretNames) '          $k: \${{ secrets.$k }}'].join('\n');
  return _workflowTemplate
      .replaceAll('@@APP@@', _appName)
      .replaceAll('@@PROJECT@@', _projectRepo)
      .replaceAll('@@VERSION@@', version)
      .replaceAll('@@PLAIN@@', plainEnv)
      .replaceAll('@@SECRETS@@', secretsEnv);
}

/// The non-secret settings already written in an existing workflow file, so a repository the desktop manages keeps its
/// email and tracking choices when the phone rewrites the file.
Map<String, String> parsePlainValues(String yaml) {
  final out = <String, String>{};
  final known = {for (final (k, _) in _plainDefaults) k};
  for (final m in RegExp(r'^ {10}AM_([A-Z_]+): ("(?:[^"\\]|\\.)*")\s*$', multiLine: true).allMatches(yaml)) {
    final key = m.group(1)!;
    if (!known.contains(key)) continue;
    try {
      out[key] = jsonDecode(m.group(2)!) as String;
    } catch (_) {/* keep the default */}
  }
  return out;
}

String readmeText(String login) => '''# $_appName cloud checks

This private repository belongs to $login's $_appName setup. A scheduled workflow signs in to the Bahria portal
twice a day from GitHub's machines and sends the usual alerts to the paired phone and mailbox, so they arrive when the
PC is off. The `state` folder is the cache of what was last seen (the same files the PC keeps). The portal login and
channel keys are repository secrets, encrypted by GitHub.

Managed by the app: turn it off from Settings > Cloud checks. Project: https://github.com/$_projectRepo
Website: $_siteUrl
''';

const _gitignore = 'state/settings.env\nstate/chrome_profile/\nstate/browsers/\nstate/data/app.log*\nstate/data/sync.lock\n';

/// The latest run of the workflow.
class CloudRun {
  CloudRun({required this.when, required this.status, required this.conclusion, required this.url});
  final DateTime when;
  final String status;       // queued, in_progress, completed
  final String? conclusion;  // success, failure, cancelled ... once completed
  final String url;
  bool get running => status != 'completed';
  bool get ok => conclusion == 'success';
}

/// What Settings shows: is Cloud checks on in the student's repository, and how did the last run go.
class CloudStatus {
  CloudStatus({required this.repo, required this.enabled, this.run});
  final String repo;
  final bool enabled;
  final CloudRun? run;
}

class CloudSetupResult {
  CloudSetupResult(this.repo, this.login, this.runUrl);
  final String repo, login, runUrl;
}

/// The GitHub calls, with errors in plain words. One instance per token.
class CloudClient {
  CloudClient(this._token, {http.Client? client, Future<void> Function(Duration)? delay})
      : _http = client ?? http.Client(),
        _delay = delay ?? ((d) => Future<void>.delayed(d));
  final String _token;
  final http.Client _http;
  final Future<void> Function(Duration) _delay;

  Map<String, String> get _headers => {
        'Authorization': 'Bearer $_token',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
      };

  /// One request. Returns the status and the decoded JSON (or null). Network trouble becomes a [CloudError] that says so
  /// and nothing else (the exception text is dropped on purpose: it can quote the request).
  Future<(int, Object?)> _call(String method, String path, {Object? body}) async {
    final req = http.Request(method, Uri.parse(path.startsWith('http') ? path : 'https://api.github.com$path'));
    req.headers.addAll(_headers);
    if (body != null) req.body = jsonEncode(body);
    final http.Response res;
    try {
      res = await http.Response.fromStream(await _http.send(req).timeout(const Duration(seconds: 40)));
    } on TimeoutException {
      throw CloudError('GitHub did not answer in time. Check the connection and retry.');
    } catch (_) {
      throw CloudError('No connection to GitHub. Check the internet and retry.');
    }
    Object? data;
    if (res.body.isNotEmpty) {
      try {
        data = jsonDecode(utf8.decode(res.bodyBytes));
      } catch (_) {/* not JSON */}
    }
    return (res.statusCode, _RateLimited.mark(res, data));
  }

  /// A request that must succeed with one of [ok]; anything else is explained.
  Future<Object?> _must(String what, String method, String path, {Object? body, List<int> ok = const [200, 201, 204]}) async {
    final (status, data) = await _call(method, path, body: body);
    if (ok.contains(status)) return data;
    throw _explain(what, status, data);
  }

  CloudError _explain(String what, int status, Object? data) {
    if (data is _RateLimited || status == 429) {
      return CloudError('GitHub is limiting requests from this account for a few minutes. Wait a little and retry.', status: status);
    }
    switch (status) {
      case 401:
        return CloudError('Your GitHub sign-in expired or was removed. Sign in again.', status: status);
      case 403:
        return CloudError('GitHub did not allow that ($what). The sign-in may lack permission; sign in again and approve "repo" and "workflow".', status: status);
      case 404:
        return CloudError('GitHub could not find what it needed ($what). The sign-in may lack permission, or it was removed.', status: status);
      case 409:
        return CloudError('GitHub was busy with another change ($what). Retry in a moment.', status: status);
      case 422:
        return CloudError('GitHub refused the request ($what). If the repository was just created, wait a moment and retry.', status: status);
    }
    if (status >= 500) return CloudError('GitHub had a problem ($status) while $what. Retry in a moment.', status: status);
    return CloudError('GitHub answered $status while $what.', status: status);
  }

  Future<String> login() async {
    final d = await _must('reading your account', 'GET', '/user', ok: const [200]);
    final l = d is Map ? d['login'] : null;
    if (l is! String) throw CloudError('GitHub did not say who you are.');
    return l;
  }

  /// The runner tag must exist, or every run of the workflow would fail at checkout.
  Future<void> _runnerExists() async {
    final (status, _) = await _call('GET', '/repos/$_projectRepo/git/ref/tags/v$cloudRunnerVersion');
    if (status == 200) return;
    if (status == 404) {
      throw CloudError('Cloud checks from the phone need the desktop release v$cloudRunnerVersion, which is not published yet. Update the app, or try again later.', status: 404);
    }
    throw _explain('checking the release', status, null);
  }

  /// The private repository, created on first use. Returns (owner/name, default branch).
  Future<(String, String)> ensureRepo(String login) async {
    final full = '$login/$repoName';
    final (status, data) = await _call('GET', '/repos/$full');
    if (status == 200 && data is Map) {
      if (data['private'] != true) {
        throw CloudError('The repository $full exists but is public. Make it private or delete it on GitHub, then retry.');
      }
      return (full, (data['default_branch'] as String?) ?? 'main');
    }
    if (status != 404) throw _explain('opening $full', status, data);
    final made = await _must('creating the repository', 'POST', '/user/repos', ok: const [201], body: {
      'name': repoName,
      'private': true,
      'auto_init': true,
      'has_issues': false,
      'has_projects': false,
      'has_wiki': false,
      'description': '$_appName: scheduled portal checks for this account. Managed by the app; nothing to edit here.',
    });
    for (var i = 0; i < 20; i++) {   // auto_init creates the default branch a moment later
      final (s, _) = await _call('GET', '/repos/$full/contents/README.md');
      if (s == 200) break;
      await _delay(const Duration(milliseconds: 500));
    }
    return (full, (made is Map ? made['default_branch'] as String? : null) ?? 'main');
  }

  /// The decoded text of a file, or null when it is not there.
  Future<String?> readFile(String repo, String path) async {
    final (status, data) = await _call('GET', '/repos/$repo/contents/$path');
    if (status == 404) return null;
    if (status != 200 || data is! Map) throw _explain('reading $path', status, data);
    final c = data['content'];
    if (c is! String) return null;
    try {
      return utf8.decode(base64Decode(c.replaceAll(RegExp(r'\s'), '')));
    } catch (_) {
      return null;
    }
  }

  /// Creates or updates one file (one commit); nothing is sent when it is already the same.
  Future<void> putFile(String repo, String path, String text, String message) async {
    final (status, data) = await _call('GET', '/repos/$repo/contents/$path');
    final body = <String, Object?>{'message': message, 'content': base64Encode(utf8.encode(text))};
    if (status == 200 && data is Map && data['sha'] is String) {
      final old = data['content'];
      if (old is String) {
        try {
          if (utf8.decode(base64Decode(old.replaceAll(RegExp(r'\s'), ''))) == text) return;
        } catch (_) {/* rewrite it */}
      }
      body['sha'] = data['sha'];
    } else if (status != 404 && status != 200) {
      throw _explain('reading $path', status, data);
    }
    await _must('writing $path', 'PUT', '/repos/$repo/contents/$path', body: body, ok: const [200, 201]);
  }

  Future<void> deleteFile(String repo, String path, String message) async {
    final (status, data) = await _call('GET', '/repos/$repo/contents/$path');
    if (status == 404) return;
    if (status != 200 || data is! Map || data['sha'] is! String) throw _explain('reading $path', status, data);
    await _must('removing $path', 'DELETE', '/repos/$repo/contents/$path', body: {'message': message, 'sha': data['sha']});
  }

  /// Seals each value with the repository's public key and stores it. A null or empty value deletes that secret.
  Future<void> setSecrets(String repo, Map<String, String?> values) async {
    final pk = await _must('fetching the repository key', 'GET', '/repos/$repo/actions/secrets/public-key', ok: const [200]);
    if (pk is! Map || pk['key'] is! String || pk['key_id'] is! String) throw CloudError('GitHub did not send the repository key.');
    for (final e in values.entries) {
      final v = e.value;
      if (v == null || v.isEmpty) {
        final (s, d) = await _call('DELETE', '/repos/$repo/actions/secrets/${e.key}');
        if (s != 204 && s != 404) throw _explain('removing a secret', s, d);
        continue;
      }
      await _must('storing a secret', 'PUT', '/repos/$repo/actions/secrets/${e.key}',
          body: {'encrypted_value': sealSecret(pk['key'] as String, v), 'key_id': pk['key_id']}, ok: const [201, 204]);
    }
  }

  /// Starts the workflow by hand. A workflow written a moment ago can take a few seconds to be known, so "not found" is
  /// retried before it is reported.
  Future<void> dispatch(String repo, String branch, {String mode = 'check', int attempts = 6}) async {
    for (var i = 1;; i++) {
      final (status, data) = await _call('POST', '/repos/$repo/actions/workflows/$_workflowFile/dispatches',
          body: {'ref': branch, 'inputs': {'mode': mode}});
      if (status == 204 || status == 200) return;
      if ((status == 404 || status == 422) && i < attempts) {
        await _delay(const Duration(seconds: 2));
        continue;
      }
      throw _explain('starting the check', status, data);
    }
  }

  Future<CloudRun?> lastRun(String repo) async {
    final d = await _must('reading the last check', 'GET', '/repos/$repo/actions/runs?per_page=1', ok: const [200]);
    final runs = d is Map ? d['workflow_runs'] : null;
    if (runs is! List || runs.isEmpty || runs.first is! Map) return null;
    final r = runs.first as Map;
    final when = DateTime.tryParse((r['run_started_at'] ?? r['created_at'] ?? '') as String);
    if (when == null) return null;
    return CloudRun(when: when.toLocal(), status: (r['status'] ?? 'completed') as String, conclusion: r['conclusion'] as String?, url: (r['html_url'] ?? '') as String);
  }

  /// Is Cloud checks on in this account's repository (is the workflow file there) and how did the last run go.
  Future<CloudStatus> status(String login) async {
    final repo = '$login/$repoName';
    final (s, _) = await _call('GET', '/repos/$repo/contents/$workflowPath');
    if (s == 404) return CloudStatus(repo: repo, enabled: false);
    if (s != 200) throw _explain('reading the workflow', s, null);
    CloudRun? run;
    try {
      run = await lastRun(repo);
    } on CloudError {/* the status still shows */}
    return CloudStatus(repo: repo, enabled: true, run: run);
  }

  Future<String> defaultBranch(String repo) async {
    final d = await _must('opening the repository', 'GET', '/repos/$repo', ok: const [200]);
    return (d is Map ? d['default_branch'] as String? : null) ?? 'main';
  }
}

/// Marks a response as GitHub's rate-limit answer (403 with no requests left, or a message saying so), without keeping the
/// body around.
class _RateLimited {
  const _RateLimited();
  static Object? mark(http.Response r, Object? data) {
    if (r.statusCode != 403 && r.statusCode != 429) return data;
    final msg = data is Map ? '${data['message']}'.toLowerCase() : '';
    if (r.headers['x-ratelimit-remaining'] == '0' || msg.contains('rate limit') || msg.contains('abuse') || r.headers.containsKey('retry-after')) {
      return const _RateLimited();
    }
    return data;
  }
}

/// The whole setup, and the later changes, in order. The password is an argument and nothing more: it is sealed and sent.
class CloudSetup {
  CloudSetup(this.client);
  final CloudClient client;

  /// Creates or refreshes the repository, the workflow and the two secrets, then starts a first check ("verify": sign in,
  /// count, send a test alert). Every step can run again: what already exists is kept or rewritten the same.
  Future<CloudSetupResult> run({required String enrollment, required String password, required String campusId, CloudProgress? progress}) async {
    void say(CloudStep s, bool done) => progress?.call(s, done);
    var step = CloudStep.repo;
    try {
      say(step, false);
      await client._runnerExists();
      final login = await client.login();
      final (repo, branch) = await client.ensureRepo(login);
      say(step, true);

      step = CloudStep.workflow;
      say(step, false);
      final plain = parsePlainValues(await client.readFile(repo, workflowPath) ?? '')..['INSTITUTE_ID'] = campusId;
      await client.putFile(repo, 'README.md', readmeText(login), 'README');
      await client.putFile(repo, '.gitignore', _gitignore, 'ignore local files');
      await client.putFile(repo, workflowPath, workflowYaml(plain: plain), 'workflow for $_appName $cloudRunnerVersion');
      say(step, true);

      step = CloudStep.secrets;
      say(step, false);
      await client.setSecrets(repo, {secretEnrollment: enrollment.trim(), secretPassword: password});
      say(step, true);

      step = CloudStep.check;
      say(step, false);
      await client.dispatch(repo, branch, mode: 'verify');
      say(step, true);
      return CloudSetupResult(repo, login, 'https://github.com/$repo/actions');
    } on CloudError catch (e) {
      e.step ??= step;
      rethrow;
    }
  }

  /// Settings > Change portal login: only the two secrets are written again.
  Future<void> changeLogin({required String repo, required String enrollment, required String password}) =>
      client.setSecrets(repo, {secretEnrollment: enrollment.trim(), secretPassword: password});

  /// Settings > Run a check now.
  Future<void> runNow(String repo, {String mode = 'check'}) async => client.dispatch(repo, await client.defaultBranch(repo), mode: mode, attempts: 1);

  /// Turn off: every secret and the workflow file are removed. The repository stays (deleting one needs a permission the
  /// app does not ask for); its settings address is returned so it can be deleted in one tap.
  Future<String> teardown(String repo) async {
    await client.setSecrets(repo, {for (final k in allSecretNames) k: ''});
    await client.deleteFile(repo, workflowPath, 'cloud checks turned off');
    return 'https://github.com/$repo/settings';
  }
}

const _workflowTemplate = r'''# @@APP@@ cloud checks. Written by the app; it is replaced on every app update, so edits here are lost.
# Runs the same check the PC runs, on GitHub's machines, so alerts reach the phone and the mailbox when the PC is off.
name: @@APP@@ check

on:
  schedule:
    - cron: "43 2 * * *"    # 07:43 Pakistan time (an odd minute: GitHub starts top-of-the-hour jobs hours late)
    - cron: "37 13 * * *"   # 18:37 Pakistan time
  workflow_dispatch:
    inputs:
      mode:
        description: "check (full sync and alerts) or verify (sign in, count, send a test alert)"
        default: check
        type: choice
        options: [check, verify]

permissions:
  contents: write

env:
  PLAYWRIGHT_BROWSERS_PATH: ${{ github.workspace }}/browsers

concurrency:
  group: check
  cancel-in-progress: false

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    steps:
      - name: This repository (state)
        uses: actions/checkout@v4
      - name: @@APP@@ @@VERSION@@
        uses: actions/checkout@v4
        with:
          repository: @@PROJECT@@
          ref: v@@VERSION@@
          path: app
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: |
          python -m pip install --quiet --upgrade pip
          pip install --quiet playwright==1.64.0 lxml==6.1.3 pywebpush==2.5.0
          python -m playwright install --with-deps chromium
      - name: Check
        env:
          ASSIGNMENT_MONITOR_HOME: ${{ github.workspace }}/state
          ASSIGNMENT_MONITOR_RUNNER: cloud
          AM_ENABLE_WINDOWS_TOAST: "False"
          AM_ENABLE_VOICE: "False"
          AM_HEADLESS: "True"
@@PLAIN@@
@@SECRETS@@
        run: python app/cloud_check.py ${{ inputs.mode || 'check' }}
      - name: Save state
        # every run commits (at least the timestamp): GitHub switches off the schedule of a repository that has
        # had no commits for 60 days, which a quiet semester break would otherwise trigger
        if: always()
        run: |
          git config user.name "@@APP@@"
          git config user.email "noreply@users.noreply.github.com"
          date -u +%Y-%m-%dT%H:%MZ > state/last_run.txt
          git add state
          git diff --cached --quiet || (git commit -q -m "state $(date -u +%Y-%m-%dT%H:%MZ)" && git push -q)
''';

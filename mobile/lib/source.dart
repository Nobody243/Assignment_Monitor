import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' hide Summary;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'data.dart';

/// Where the phone gets its numbers: the student's own private repository (`assignment-monitor-cloud`), file
/// `state/summary.json`, written after every check by the cloud runner. No server of ours is involved.
const githubClientId = 'Ov23ctd8HzseTPqZhf8Q';   // the same public OAuth app id the desktop uses (it is not a secret)
const repoName = 'assignment-monitor-cloud';
const summaryPath = 'state/summary.json';

class DeviceCode {
  DeviceCode(this.deviceCode, this.userCode, this.uri, this.interval, this.expiresIn);
  final String deviceCode, userCode, uri;
  final int interval, expiresIn;
}

/// GitHub device flow: show a short code, the student approves it in a browser (or on their other phone), we get a token.
class GithubAuth {
  GithubAuth([http.Client? client, this.unit = const Duration(seconds: 1)]) : _http = client ?? http.Client();
  final http.Client _http;

  /// One second of GitHub's polling interval; tests shrink it.
  final Duration unit;
  static const _json = {'Accept': 'application/json'};

  /// [scope] is what the token may do: `repo` reads the summary (the default); the phone-only setup asks for `repo workflow`.
  Future<DeviceCode> start({String scope = 'repo'}) async {
    final r = await _http.post(Uri.https('github.com', '/login/device/code'), headers: _json,
        body: {'client_id': githubClientId, 'scope': scope});
    final d = jsonDecode(r.body) as Map<String, dynamic>;
    if (r.statusCode != 200 || d['device_code'] == null) throw SourceError('GitHub did not give a code (${d['error'] ?? r.statusCode}).');
    return DeviceCode(d['device_code'] as String, d['user_code'] as String, d['verification_uri'] as String,
        (d['interval'] ?? 5) as int, (d['expires_in'] ?? 900) as int);
  }

  /// Polls until approved. Returns the token; throws if refused or expired.
  Future<String> approved(DeviceCode c, {bool Function()? cancelled}) async {
    var wait = c.interval;
    final until = DateTime.now().add(Duration(seconds: c.expiresIn));
    while (DateTime.now().isBefore(until)) {
      await Future.delayed(unit * wait);
      if (cancelled?.call() ?? false) throw SourceError('Cancelled.');
      final r = await _http.post(Uri.https('github.com', '/login/oauth/access_token'), headers: _json, body: {
        'client_id': githubClientId, 'device_code': c.deviceCode, 'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'});
      final d = jsonDecode(r.body) as Map<String, dynamic>;
      if (d['access_token'] != null) return d['access_token'] as String;
      switch (d['error']) {
        case 'authorization_pending': break;
        case 'slow_down': wait += 5; break;
        case 'access_denied': throw SourceError('You declined the request on GitHub.');
        case 'expired_token': throw SourceError('The code expired. Start again.');
        default: throw SourceError('GitHub said: ${d['error']}.');
      }
    }
    throw SourceError('The code expired. Start again.');
  }

  Future<String> login(String token) async {
    final r = await _http.get(Uri.https('api.github.com', '/user'), headers: _api(token));
    if (r.statusCode != 200) throw SourceError('The saved sign-in no longer works (${r.statusCode}). Sign in again.');
    return (jsonDecode(r.body) as Map)['login'] as String;
  }
}

Map<String, String> _api(String token) => {'Authorization': 'Bearer $token', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'};

class SourceError implements Exception {
  SourceError(this.message);
  final String message;
  @override
  String toString() => message;
}

class Fetched {
  Fetched(this.summary, this.etag, {this.unchanged = false, this.missing = false});
  final Summary? summary;
  final String? etag;
  final bool unchanged, missing;
}

/// Reads summary.json with a conditional GET, so an unchanged file costs one tiny request.
class SummarySource {
  SummarySource([http.Client? client]) : _http = client ?? http.Client();
  final http.Client _http;

  Future<Fetched> fetch(String token, String login, {String? etag}) async {
    final uri = Uri.https('api.github.com', '/repos/${Uri.encodeComponent(login)}/$repoName/contents/$summaryPath');
    final h = {..._api(token), 'Accept': 'application/vnd.github.raw+json', 'If-None-Match': ?etag};
    final http.Response r;
    try {
      r = await _http.get(uri, headers: h).timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw SourceError('GitHub did not answer in time.');
    } catch (_) {
      throw SourceError('No connection.');
    }
    if (r.statusCode == 304) return Fetched(null, etag, unchanged: true);
    if (r.statusCode == 404) return Fetched(null, null, missing: true);
    if (r.statusCode == 401) throw SourceError('Your GitHub sign-in expired. Sign in again.');
    if (r.statusCode != 200) throw SourceError('GitHub answered ${r.statusCode}.');
    final Object? body;
    try {
      body = jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {
      throw SourceError('summary.json is not readable.');
    }
    if (body is! Map<String, dynamic> || body['schema'] != 1) throw SourceError('This app is older than the data in your repository. Update the app.');
    return Fetched(Summary(body), r.headers['etag']);
  }
}

/// Where secrets live: the platform's keystore on a phone, memory in tests.
abstract class Vault {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
}

class KeystoreVault implements Vault {
  static const _s = FlutterSecureStorage();
  @override Future<String?> read(String key) => _s.read(key: key);
  @override Future<void> write(String key, String value) => _s.write(key: key, value: value);
  @override Future<void> delete(String key) => _s.delete(key: key);
}

/// The sign-in token and the last summary are kept in the keystore (encrypted with a key that never leaves the secure
/// hardware where there is one); the ETag, the login name and the time of the last read are not secret and stay in plain
/// preferences. The saved summary is the most sensitive thing on the phone (grades, name, seat numbers), so it is not
/// written to ordinary storage. A copy an earlier build left in preferences is moved into the keystore on first read.
class Store {
  Store({Vault? vault}) : _vault = vault ?? KeystoreVault();
  final Vault _vault;

  /// The same keystore, for the other secrets the app keeps (the portal sign-in).
  Vault get vault => _vault;
  static const _kToken = 'token', _kLogin = 'login', _kSummary = 'summary', _kEtag = 'etag', _kFetched = 'fetched';

  Future<String?> token() => _vault.read(_kToken);
  Future<void> saveSession(String token, String login) async {
    await _vault.write(_kToken, token);
    final p = await SharedPreferences.getInstance();
    await p.setString(_kLogin, login);
  }

  Future<String?> login() async => (await SharedPreferences.getInstance()).getString(_kLogin);

  Future<({Summary? summary, String? etag, DateTime? fetchedAt})> cached() async {
    final p = await SharedPreferences.getInstance();
    var raw = await _vault.read(_kSummary);
    final legacy = p.getString(_kSummary);
    if (legacy != null) {   // an earlier build kept it in plain preferences: move it, then forget the plain copy
      if (raw == null) { await _vault.write(_kSummary, legacy); raw = legacy; }
      await p.remove(_kSummary);
    }
    Summary? s;
    if (raw != null) {
      try { s = Summary(jsonDecode(raw) as Map<String, dynamic>); } catch (e) { debugPrint('cache unreadable'); }
    }
    final at = p.getString(_kFetched);
    return (summary: s, etag: p.getString(_kEtag), fetchedAt: at == null ? null : DateTime.tryParse(at));
  }

  Future<void> saveSummary(Summary s, String? etag) async {
    final p = await SharedPreferences.getInstance();
    await _vault.write(_kSummary, jsonEncode(s.raw));
    await p.remove(_kSummary);
    if (etag != null) await p.setString(_kEtag, etag);
    await p.setString(_kFetched, DateTime.now().toIso8601String());
  }

  Future<void> touchFetched() async => (await SharedPreferences.getInstance()).setString(_kFetched, DateTime.now().toIso8601String());

  /// Sign out: the token and everything cached go.
  Future<void> clear() async {
    await _vault.delete(_kToken);
    await _vault.delete(_kSummary);
    final p = await SharedPreferences.getInstance();
    for (final k in [_kLogin, _kSummary, _kEtag, _kFetched]) { await p.remove(k); }
  }
}

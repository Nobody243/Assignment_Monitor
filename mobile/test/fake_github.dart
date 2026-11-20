import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pinenacl/x25519.dart';

/// An in-memory GitHub, just enough of the REST API for the phone-only Cloud checks setup: the account, the runner tag, a
/// private repository with files and repository secrets, workflow dispatches and runs. It records every request.
class FakeGithub {
  FakeGithub({this.login = 'student1'}) : _sk = PrivateKey.generate();

  final String login;
  final PrivateKey _sk;
  bool tagExists = true, repoExists = false, repoPrivate = true;
  String branch = 'main';
  final files = <String, String>{};                 // path -> text
  final secrets = <String, String>{};               // name -> decrypted value (only the fake can open them)
  final sealedAsSent = <String, String>{};          // name -> the base64 the phone sent
  final calls = <String>[];                         // "METHOD /path"
  final bodies = <String>[];                        // every request body, as text
  final dispatches = <Map<String, Object?>>[];
  Map<String, Object?>? run;
  int dispatch404s = 0;                             // answer this many dispatches with 404 first (a workflow GitHub does not know yet)
  final failures = <String, int>{};                 // "METHOD /path-prefix" -> status to answer with
  Map<String, String> failHeaders = {};
  Object? failBody;

  String get publicKey => base64Encode(_sk.publicKey.asTypedList);
  String get repo => '$login/assignment-monitor-cloud';

  late final http.Client client = MockClient((req) async {
    final path = req.url.path + (req.url.hasQuery ? '?${req.url.query}' : '');
    calls.add('${req.method} ${req.url.path}');
    if (req.body.isNotEmpty) bodies.add(req.body);
    for (final f in failures.entries) {
      final sp = f.key.indexOf(' ');
      if (req.method == f.key.substring(0, sp) && req.url.path.startsWith(f.key.substring(sp + 1))) {
        return http.Response(jsonEncode(failBody ?? {'message': 'refused'}), f.value, headers: failHeaders);
      }
    }
    return _route(req, path);
  });

  http.Response _json(Object? body, [int status = 200]) => http.Response(jsonEncode(body), status);

  http.Response _route(http.Request req, String path) {
    final p = req.url.path;
    final m = req.method;
    if (p == '/user' && m == 'GET') return _json({'login': login});
    if (p == '/repos/Nobody243/Assignment_Monitor/git/ref/tags/v1.9.0') return tagExists ? _json({'ref': 'refs/tags/v1.9.0'}) : _json({'message': 'Not Found'}, 404);
    if (p == '/user/repos' && m == 'POST') {
      repoExists = true;
      files['README.md'] = 'initial';
      return _json({'private': true, 'default_branch': branch, 'full_name': repo}, 201);
    }
    if (p == '/repos/$repo' && m == 'GET') return repoExists ? _json({'private': repoPrivate, 'default_branch': branch}) : _json({'message': 'Not Found'}, 404);
    final contents = '/repos/$repo/contents/';
    if (p.startsWith(contents)) {
      final file = p.substring(contents.length);
      if (m == 'GET') {
        final t = files[file];
        if (t == null) return _json({'message': 'Not Found'}, 404);
        return _json({'sha': 'sha-${t.hashCode}', 'content': base64Encode(utf8.encode(t))});
      }
      final b = jsonDecode(req.body) as Map;
      if (m == 'PUT') {
        final exists = files.containsKey(file);
        if (exists && b['sha'] == null) return _json({'message': 'sha missing'}, 422);
        files[file] = utf8.decode(base64Decode(b['content'] as String));
        return _json({'content': {}}, exists ? 200 : 201);
      }
      if (m == 'DELETE') {
        files.remove(file);
        return _json({});
      }
    }
    if (p == '/repos/$repo/actions/secrets/public-key') return _json({'key': publicKey, 'key_id': 'key-1'});
    final sec = '/repos/$repo/actions/secrets/';
    if (p.startsWith(sec)) {
      final name = p.substring(sec.length);
      if (m == 'PUT') {
        final b = jsonDecode(req.body) as Map;
        final sealed = b['encrypted_value'] as String;
        sealedAsSent[name] = sealed;
        secrets[name] = utf8.decode(SealedBox(_sk).decrypt(Uint8List.fromList(base64Decode(sealed))));
        return http.Response('', 201);
      }
      if (m == 'DELETE') return http.Response('', secrets.remove(name) == null ? 404 : 204);
    }
    if (p == '/repos/$repo/actions/workflows/check.yml/dispatches' && m == 'POST') {
      if (dispatch404s > 0) {
        dispatch404s--;
        return _json({'message': 'Not Found'}, 404);
      }
      dispatches.add(jsonDecode(req.body) as Map<String, Object?>);
      return http.Response('', 204);
    }
    if (p == '/repos/$repo/actions/runs' && m == 'GET') {
      return _json({'workflow_runs': run == null ? [] : [run]});
    }
    return _json({'message': 'unexpected ${req.method} $path'}, 500);
  }
}

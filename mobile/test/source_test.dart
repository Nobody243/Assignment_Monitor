import 'dart:convert';

import 'package:assignment_monitor_mobile/source.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

http.Response _json(Object o, [int code = 200, Map<String, String> h = const {}]) => http.Response(jsonEncode(o), code, headers: h);

void main() {
  test('a good summary is read and its ETag kept', () async {
    final src = SummarySource(MockClient((r) async {
      expect(r.url.path, '/repos/alex/assignment-monitor-cloud/contents/state/summary.json');
      expect(r.headers['Authorization'], 'Bearer tok');
      return _json({'schema': 1, 'assignments': []}, 200, {'etag': 'W/"abc"'});
    }));
    final f = await src.fetch('tok', 'alex');
    expect(f.summary, isNotNull);
    expect(f.etag, 'W/"abc"');
  });

  test('an unchanged file costs a conditional request and no parse', () async {
    final src = SummarySource(MockClient((r) async {
      expect(r.headers['If-None-Match'], 'W/"abc"');
      return http.Response('', 304);
    }));
    final f = await src.fetch('tok', 'alex', etag: 'W/"abc"');
    expect(f.unchanged, isTrue);
  });

  test('no summary yet is reported as missing, not as an error', () async {
    final src = SummarySource(MockClient((r) async => http.Response('{}', 404)));
    expect((await src.fetch('tok', 'alex')).missing, isTrue);
  });

  test('a rejected token asks for a new sign-in', () async {
    final src = SummarySource(MockClient((r) async => http.Response('{}', 401)));
    expect(() => src.fetch('tok', 'alex'), throwsA(isA<SourceError>().having((e) => e.message, 'message', contains('Sign in again'))));
  });

  test('data from a newer schema asks for an app update', () async {
    final src = SummarySource(MockClient((r) async => _json({'schema': 2})));
    expect(() => src.fetch('tok', 'alex'), throwsA(isA<SourceError>().having((e) => e.message, 'message', contains('Update the app'))));
  });

  test('a lost connection is said in plain words', () async {
    final src = SummarySource(MockClient((r) async => throw http.ClientException('down')));
    expect(() => src.fetch('tok', 'alex'), throwsA(isA<SourceError>().having((e) => e.message, 'message', 'No connection.')));
  });
}

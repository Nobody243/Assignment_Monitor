import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'source.dart' show Vault;

/// Talking to the university portal straight from the phone (the standalone mode). A browser view that the student never
/// sees signs in to the CMS, goes through single sign-on to the LMS, and reads pages, exactly as the desktop app's browser
/// does. This file holds the sign-in and the course list; `PortalBrowser` is the only piece that needs a real WebView, so
/// everything else is tested with a fake one.
const cmsHost = 'cms.bahria.edu.pk', lmsHost = 'lms.bahria.edu.pk';
const loginUrl = 'https://$cmsHost/Logins/Student/Login.aspx';
const ssoUrl = 'https://$cmsHost/Sys/Common/GoToLMS.aspx';
const assignmentsUrl = 'https://$lmsHost/Student/Assignments.php';

/// The direct-from-the-phone mode (mobile/STANDALONE.md): its sign-in entry on the first screen.
const standaloneReady = bool.fromEnvironment('STANDALONE', defaultValue: true);   // --dart-define=STANDALONE=false hides it

/// Only these hosts are ever opened; the password is typed into nothing else.
bool isPortalHost(String? host) => host == cmsHost || host == lmsHost;

/// (name, CMS institute id), the same list as the desktop app's setup.
const campuses = <(String, String)>[
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

class PortalCredentials {
  const PortalCredentials(this.enrollment, this.password, this.instituteId);
  final String enrollment, password, instituteId;
  bool get complete => enrollment.trim().isNotEmpty && password.isNotEmpty && instituteId.isNotEmpty;
}

/// The enrollment number and password live only in the keystore. Nothing here is logged or put in preferences.
class PortalStore {
  PortalStore(this._vault);
  final Vault _vault;
  static const _kEnrollment = 'portal_enrollment', _kPassword = 'portal_password', _kInstitute = 'portal_institute';

  Future<PortalCredentials?> read() async {
    final e = await _vault.read(_kEnrollment), p = await _vault.read(_kPassword), i = await _vault.read(_kInstitute);
    if (e == null || p == null || i == null) return null;
    return PortalCredentials(e, p, i);
  }

  Future<void> save(PortalCredentials c) async {
    await _vault.write(_kEnrollment, c.enrollment.trim());
    await _vault.write(_kPassword, c.password);
    await _vault.write(_kInstitute, c.instituteId);
  }

  Future<void> clear() async {
    for (final k in [_kEnrollment, _kPassword, _kInstitute]) { await _vault.delete(k); }
  }
}

/// A page the phone can drive. The real one is a WebView; tests use a scripted fake.
abstract class PortalBrowser {
  /// Opens [url] and returns when the page has loaded (or throws after [timeout]).
  Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)});
  Future<String> url();
  Future<String> html();

  /// Runs JavaScript in the page and returns its result.
  Future<dynamic> js(String source);

  /// Runs JavaScript that makes the page reload or post (a course change, a button) and waits for the page to settle again.
  /// A page that updates without reloading is fine: the wait simply ends after [timeout].
  Future<void> jsThenSettle(String source, {Duration timeout = const Duration(seconds: 20)});

  /// Downloads a file with the page's own session (cookies). The page must be on the same host as [url].
  Future<FetchedFile> fetchFile(String url, {int maxBytes = maxDownloadBytes});

  /// Puts a file into a file input of the current page, as if the student had picked it.
  Future<void> attachFile(String selector, String name, String mime, Uint8List bytes);

  /// Forgets the session (cookies) and frees the view.
  Future<void> close();
}

/// The largest file the phone downloads in one go (it is held in memory while it is carried over from the page).
const maxDownloadBytes = 60 * 1024 * 1024;

class FetchedFile {
  FetchedFile(this.status, this.contentType, this.disposition, this.bytes);
  final int status;
  final String contentType, disposition;
  final Uint8List bytes;
}

enum SignInProblem { wrongDetails, blocked, offline, unexpected }

class SignInResult {
  const SignInResult.ok() : problem = null, message = '';
  const SignInResult.failed(SignInProblem this.problem, this.message);
  final SignInProblem? problem;
  final String message;
  bool get ok => problem == null;
}

class PortalCourse {
  const PortalCourse(this.value, this.name);
  final String value, name;
}

class Portal {
  Portal(this.browser, {this.pause = const Duration(milliseconds: 500), this.signInSeconds = 30, this.credentials});
  final PortalBrowser browser;

  /// Kept so a dropped session can sign in again without asking (the portal expires sessions quietly).
  final PortalCredentials? credentials;

  /// How long a sign-in may take before the portal is judged to have said no.
  final int signInSeconds;

  /// How long to wait between looks at the page; tests make it zero.
  final Duration pause;
  bool _inLms = false;

  static String _q(String s) => jsonEncode(s);   // a safe JavaScript string literal

  Future<bool> _waitFor(Future<bool> Function() ready, {int seconds = 30}) async {
    final end = DateTime.now().add(Duration(seconds: seconds));
    while (true) {
      if (await ready()) return true;
      if (!DateTime.now().isBefore(end)) return false;
      await Future<void>.delayed(pause);
    }
  }

  Future<bool> _onLogin() async => (await browser.url()).toLowerCase().contains('login.aspx');

  /// Signs in to the CMS. The reasons a sign-in can fail are told apart so the screen can say what to do about each.
  Future<SignInResult> signIn(PortalCredentials c) async {
    try {
      await browser.open(loginUrl);
    } catch (e) {
      return const SignInResult.failed(SignInProblem.offline, 'The university portal did not answer. Check the connection and try again.');
    }
    final hasForm = await browser.js("!!document.querySelector('#BodyPH_tbEnrollment')") == true;
    if (!hasForm) {
      if (!await _onLogin()) { _inLms = false; return const SignInResult.ok(); }   // the portal remembered a session
      final page = (await browser.html()).toLowerCase();
      if (page.contains('captcha') || page.contains('recaptcha')) {
        return const SignInResult.failed(SignInProblem.blocked, 'The portal is asking for a captcha, which the phone cannot solve on its own.');
      }
      return const SignInResult.failed(SignInProblem.unexpected, 'The portal sign-in page looks different from what the app expects.');
    }
    final page = (await browser.html()).toLowerCase();
    if (page.contains('g-recaptcha') || page.contains('captcha_image')) {
      return const SignInResult.failed(SignInProblem.blocked, 'The portal is asking for a captcha, which the phone cannot solve on its own.');
    }
    await browser.js('''
(() => {
  const set = (id, v) => { const el = document.querySelector(id); if (el) { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); } };
  set('#BodyPH_tbEnrollment', ${_q(c.enrollment.trim())});
  set('#BodyPH_tbPassword', ${_q(c.password)});
  set('#BodyPH_ddlInstituteID', ${_q(c.instituteId)});
  set('#BodyPH_ddlSubUserType', 'None');
  document.querySelector('#BodyPH_btnLogin').click();
})()''');
    final left = await _waitFor(() async => !await _onLogin(), seconds: signInSeconds);
    if (left) { _inLms = false; return const SignInResult.ok(); }
    final said = await browser.js('''
(() => {
  const out = [];
  for (const sel of ['.text-danger', '.alert', "[id*='lblMessage']", "[id*='lblError']"]) {
    for (const el of document.querySelectorAll(sel)) {
      if (el.offsetParent !== null) { const t = (el.innerText || '').trim(); if (t && !out.includes(t)) out.push(t); }
    }
  }
  return out.join(', ');
})()''');
    final text = (said is String ? said : '').trim();
    final after = (await browser.html()).toLowerCase();
    if (after.contains('captcha')) {
      return const SignInResult.failed(SignInProblem.blocked, 'The portal is asking for a captcha, which the phone cannot solve on its own.');
    }
    return SignInResult.failed(SignInProblem.wrongDetails,
        text.isNotEmpty ? text : 'The portal did not accept the enrollment number, password or campus.');
  }

  /// Goes from the CMS to the LMS through single sign-on. Returns false when the session is gone.
  Future<bool> enterLms() async {
    if (_inLms) return true;
    try {
      await browser.open(ssoUrl);
    } catch (e) {
      return false;
    }
    final ok = await _waitFor(() async => Uri.tryParse(await browser.url())?.host == lmsHost, seconds: 30);
    if (!ok) return false;
    _inLms = true;
    return true;
  }

  /// The courses in the LMS course selector. The option values are one-time tokens that the portal re-issues, so they are
  /// only good for the page they were read from; use the names.
  Future<List<PortalCourse>> courses() async {
    if (!await enterLms()) throw StateError('The LMS could not be opened.');
    await browser.open(assignmentsUrl);
    final there = await _waitFor(() async => await browser.js("document.querySelectorAll('#courseId option[value]:not([value=\"\"])').length > 0") == true, seconds: 20);
    if (!there) return const [];
    final raw = await browser.js('''
JSON.stringify(Array.from(document.querySelectorAll('#courseId option')).map(o => [o.value, (o.innerText || '').trim()]).filter(x => x[0] && x[1] && x[1] !== 'Select Course'))''');
    final list = jsonDecode(raw as String) as List;
    return [for (final e in list) PortalCourse((e as List)[0] as String, e[1] as String)];
  }

  /// Opens a CMS page and returns its HTML, signing in again once if the portal sent the session back to the login page.
  Future<String> cmsPage(String url) async {
    await browser.open(url);
    if (await _onLogin()) {
      final c = credentials;
      if (c == null || !(await signIn(c)).ok) throw StateError('The portal session ended.');
      await browser.open(url);
      if (await _onLogin()) throw StateError('The page could not be opened.');
    }
    return browser.html();
  }

  /// Opens an LMS page (through single sign-on first) and returns its HTML; one retry if the session was lost.
  Future<String> lmsPage(String url) async {
    for (var attempt = 0; attempt < 2; attempt++) {
      if (!await enterLms()) { _inLms = false; if (attempt == 0) continue; throw StateError('The LMS could not be opened.'); }
      await browser.open(url);
      if (Uri.tryParse(await browser.url())?.host == lmsHost) return browser.html();
      _inLms = false;
    }
    throw StateError('The LMS session was lost.');
  }

  /// Chooses a course by its name in the LMS course selector and returns the page after the change. The option values are
  /// re-issued each time the list reloads, so the value is read from the page as it is now.
  Future<String> selectCourse(String name) async {
    for (var attempt = 0; attempt < 3; attempt++) {
      final raw = await browser.js("""
(() => {
  const s = document.querySelector('#courseId'); if (!s) return '';
  const o = Array.from(s.options).find(o => (o.innerText || '').trim() === ${_q(name)});
  if (!o) return '';
  s.value = o.value; s.dispatchEvent(new Event('change', {bubbles: true})); return 'ok';
})()""");
      if (raw == 'ok') { await browser.jsThenSettle('0', timeout: const Duration(seconds: 15)); await Future<void>.delayed(pause * 2); return browser.html(); }
      await Future<void>.delayed(pause);
    }
    throw StateError('Course not found in the course list: $name');
  }

  /// Chooses an option of a select by its value (the exam type, for one) and returns the page after the change.
  Future<String> selectOption(String selector, String value) async {
    await browser.js("""
(() => { const s = document.querySelector(${_q(selector)}); if (s) { s.value = ${_q(value)}; s.dispatchEvent(new Event('change', {bubbles: true})); } })()""");
    await browser.jsThenSettle('0', timeout: const Duration(seconds: 15));
    await Future<void>.delayed(pause * 2);
    return browser.html();
  }

  Future<void> close() => browser.close();
}

/// The real browser: a WebView the student never sees, with its cookies and cache cleared before and after, limited to the
/// two university hosts.
class WebViewBrowser implements PortalBrowser {
  WebViewController? _c;
  Completer<void>? _loaded;

  Future<WebViewController> _ready() async {
    final have = _c;
    if (have != null) return have;
    final c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onNavigationRequest: (r) {
          final u = Uri.tryParse(r.url);
          return (u != null && u.scheme == 'https' && isPortalHost(u.host)) ? NavigationDecision.navigate : NavigationDecision.prevent;
        },
        onPageFinished: (_) { final l = _loaded; if (l != null && !l.isCompleted) l.complete(); },
        onWebResourceError: (e) { final l = _loaded; if (l != null && !l.isCompleted && (e.isForMainFrame ?? true)) l.completeError(StateError(e.description)); },
      ));
    await WebViewCookieManager().clearCookies();
    await c.clearCache();
    await c.clearLocalStorage();
    _c = c;
    return c;
  }

  @override
  Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)}) async {
    final uri = Uri.parse(url);
    if (uri.scheme != 'https' || !isPortalHost(uri.host)) throw ArgumentError('Not a portal address.');
    final c = await _ready();
    _loaded = Completer<void>();
    await c.loadRequest(uri);
    await _loaded!.future.timeout(timeout);
  }

  @override
  Future<String> url() async => (await (await _ready()).currentUrl()) ?? '';

  @override
  Future<String> html() async => (await js('document.documentElement.outerHTML'))?.toString() ?? '';

  /// On Android the result of a script comes back JSON-encoded (a string arrives with quotes); this undoes that once.
  @override
  Future<dynamic> js(String source) async {
    final r = await (await _ready()).runJavaScriptReturningResult(source);
    if (r is String) {
      if (r == 'null' || r == 'undefined') return null;
      try { return jsonDecode(r); } catch (_) { return r; }
    }
    return r;
  }

  /// Messages from the page's download script (a file arrives in pieces, base64 text, because a script result is small).
  BytesBuilder? _incoming;
  Completer<FetchedFile>? _fetch;
  int _status = 0, _limit = 0;
  String _type = '', _disp = '';

  void _onMessage(String raw) {
    final m = jsonDecode(raw) as Map<String, dynamic>;
    final done = _fetch;
    if (done == null || done.isCompleted) return;
    switch (m['k']) {
      case 'head':
        _status = (m['status'] as num).toInt(); _type = '${m['type']}'; _disp = '${m['cd']}';
        if ((m['size'] as num) > _limit) { done.completeError(StateError('The file is too big for the phone to carry (over ${_limit ~/ (1024 * 1024)} MB).')); }
      case 'chunk':
        _incoming?.add(base64Decode(m['d'] as String));
      case 'end':
        done.complete(FetchedFile(_status, _type, _disp, _incoming?.takeBytes() ?? Uint8List(0)));
      case 'err':
        done.completeError(StateError('${m['m']}'));
    }
  }

  @override
  Future<FetchedFile> fetchFile(String url, {int maxBytes = maxDownloadBytes}) async {
    final uri = Uri.parse(url);
    if (uri.scheme != 'https' || !isPortalHost(uri.host)) throw ArgumentError('Not a portal address.');
    final c = await _ready();
    if (!_channel) { await c.addJavaScriptChannel('AM', onMessageReceived: (m) => _onMessage(m.message)); _channel = true; }
    _incoming = BytesBuilder(copy: false); _limit = maxBytes;
    final done = _fetch = Completer<FetchedFile>();
    await c.runJavaScript('''
(async () => {
  try {
    const r = await fetch(${jsonEncode(url)}, {credentials: 'include'});
    const buf = await r.arrayBuffer();
    AM.postMessage(JSON.stringify({k: 'head', status: r.status, type: r.headers.get('content-type') || '', cd: r.headers.get('content-disposition') || '', size: buf.byteLength}));
    const bytes = new Uint8Array(buf), STEP = 240000;
    for (let i = 0; i < bytes.length; i += STEP) {
      const part = bytes.subarray(i, i + STEP); let s = '';
      for (let j = 0; j < part.length; j += 8192) s += String.fromCharCode.apply(null, part.subarray(j, j + 8192));
      AM.postMessage(JSON.stringify({k: 'chunk', d: btoa(s)}));
    }
    AM.postMessage(JSON.stringify({k: 'end'}));
  } catch (e) { AM.postMessage(JSON.stringify({k: 'err', m: String(e)})); }
})()''');
    return done.future.timeout(const Duration(minutes: 4));
  }

  bool _channel = false;

  @override
  Future<void> attachFile(String selector, String name, String mime, Uint8List bytes) async {
    final c = await _ready();
    await c.runJavaScript('window.__am = "";');
    final text = base64Encode(bytes);
    for (var i = 0; i < text.length; i += 200000) {
      await c.runJavaScript('window.__am += ${jsonEncode(text.substring(i, i + 200000 > text.length ? text.length : i + 200000))};');
    }
    await c.runJavaScript('''
(() => {
  const bin = atob(window.__am), arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  const dt = new DataTransfer(); dt.items.add(new File([arr], ${jsonEncode(name)}, {type: ${jsonEncode(mime)}}));
  const input = document.querySelector(${jsonEncode(selector)}); input.files = dt.files;
  input.dispatchEvent(new Event('change', {bubbles: true})); window.__am = '';
})()''');
  }

  @override
  Future<void> jsThenSettle(String source, {Duration timeout = const Duration(seconds: 20)}) async {
    final c = await _ready();
    _loaded = Completer<void>();
    await c.runJavaScript(source);
    try { await _loaded!.future.timeout(timeout); } catch (_) {/* no reload happened */}
  }

  @override
  Future<void> close() async {
    final c = _c;
    _c = null;
    try {
      await WebViewCookieManager().clearCookies();
      await c?.clearCache();
      await c?.clearLocalStorage();
    } catch (e) { debugPrint('portal cleanup: $e'); }
  }
}

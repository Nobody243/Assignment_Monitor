import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';

import 'source.dart' show Vault;

/// Talking to the university portal straight from the phone (the standalone mode). A browser view that the student never
/// sees signs in to the CMS, goes through single sign-on to the LMS, and reads pages, exactly as the desktop app's browser
/// does. This file holds the sign-in and the course list; `PortalBrowser` is the only piece that needs a real WebView, so
/// everything else is tested with a fake one.
const cmsHost = 'cms.bahria.edu.pk', lmsHost = 'lms.bahria.edu.pk';
const loginUrl = 'https://$cmsHost/Logins/Student/Login.aspx';
const ssoUrl = 'https://$cmsHost/Sys/Common/GoToLMS.aspx';
const assignmentsUrl = 'https://$lmsHost/Student/Assignments.php';

/// The direct-from-the-phone mode is built phase by phase (mobile/STANDALONE.md); its sign-in entry stays hidden until the data
/// screens behind it work, so nobody signs in to a path that leads nowhere.
const standaloneReady = false;

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

  /// Forgets the session (cookies) and frees the view.
  Future<void> close();
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
  Portal(this.browser, {this.pause = const Duration(milliseconds: 500), this.signInSeconds = 30});
  final PortalBrowser browser;

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

  Future<void> close() => browser.close();
}

/// The real browser: a headless WebView with its own empty cookie jar that is thrown away at the end, limited to the two
/// university hosts.
class WebViewBrowser implements PortalBrowser {
  HeadlessInAppWebView? _view;
  InAppWebViewController? _c;
  Completer<void>? _loaded;

  Future<InAppWebViewController> _ready() async {
    final have = _c;
    if (have != null) return have;
    final ready = Completer<InAppWebViewController>();
    final view = HeadlessInAppWebView(
      initialSettings: InAppWebViewSettings(
        javaScriptEnabled: true, incognito: true, clearCache: true, cacheEnabled: false,
        thirdPartyCookiesEnabled: false, mediaPlaybackRequiresUserGesture: true, allowFileAccess: false,
        allowContentAccess: false, javaScriptCanOpenWindowsAutomatically: false,
      ),
      onWebViewCreated: (c) { if (!ready.isCompleted) ready.complete(c); },
      onLoadStop: (c, u) { final l = _loaded; if (l != null && !l.isCompleted) l.complete(); },
      onReceivedError: (c, r, e) { final l = _loaded; if (l != null && !l.isCompleted && (r.isForMainFrame ?? true)) l.completeError(StateError(e.description)); },
      shouldOverrideUrlLoading: (c, a) async {
        final u = a.request.url;
        return (u != null && u.scheme == 'https' && isPortalHost(u.host)) ? NavigationActionPolicy.ALLOW : NavigationActionPolicy.CANCEL;
      },
    );
    _view = view;
    await view.run();
    _c = await ready.future.timeout(const Duration(seconds: 20));
    return _c!;
  }

  @override
  Future<void> open(String url, {Duration timeout = const Duration(seconds: 40)}) async {
    final uri = Uri.parse(url);
    if (uri.scheme != 'https' || !isPortalHost(uri.host)) throw ArgumentError('Not a portal address.');
    final c = await _ready();
    _loaded = Completer<void>();
    await c.loadUrl(urlRequest: URLRequest(url: WebUri(url)));
    await _loaded!.future.timeout(timeout);
  }

  @override
  Future<String> url() async => (await (await _ready()).getUrl())?.toString() ?? '';

  @override
  Future<String> html() async => (await (await _ready()).getHtml()) ?? '';

  @override
  Future<dynamic> js(String source) async => (await _ready()).evaluateJavascript(source: source);

  @override
  Future<void> close() async {
    try { await CookieManager.instance().deleteAllCookies(); } catch (e) { debugPrint('cookies: $e'); }
    await _view?.dispose();
    _view = null; _c = null;
  }
}

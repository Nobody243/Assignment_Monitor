// ignore_for_file: prefer_initializing_formals
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'data.dart';
import 'lock.dart';
import 'secure_screen.dart';
import 'reminders.dart';
import 'portal.dart';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'portal_files.dart';
import 'portal_sync.dart';
import 'source.dart';
import 'widget.dart';
import 'theme.dart';

enum Phase { loading, signedOut, signingIn, waiting, ready }

/// App-wide choices the Settings screen changes, saved on the phone.
class Prefs extends ChangeNotifier {
  Palette palette = palettes.first;
  ThemeMode mode = ThemeMode.system;
  List<int> leads = [24, 3, 1];
  DateTime? annSeen;   // announcements posted after this are new
  bool secureScreen = true;   // block screenshots and the recent-apps preview (Android)
  bool setupDone = false;     // the first-run reminder setup and lock offer have been shown
  bool appLock = false;   // ask the phone's own lock before showing anything
  bool weekly = true, digest = false, alerts = true;   // Sunday summary, morning digest, background alerts
  final Set<String> done = {};
  final Map<String, DateTime> snoozed = {};
  void Function()? onChanged;   // the model re-plans reminders when a choice that affects them changes

  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    palette = palettes.firstWhere((x) => x.key == p.getString('palette'), orElse: () => palettes.first);
    mode = ThemeMode.values.firstWhere((x) => x.name == p.getString('mode'), orElse: () => ThemeMode.system);
    leads = (p.getStringList('leads') ?? ['24', '3', '1']).map(int.parse).toList();
    annSeen = DateTime.tryParse(p.getString('annSeen') ?? '');
    appLock = p.getBool('appLock') ?? false;
    secureScreen = p.getBool('secureScreen') ?? true;
    setupDone = p.getBool('setupDone') ?? false;
    weekly = p.getBool('weekly') ?? true;
    digest = p.getBool('digest') ?? false;
    alerts = p.getBool('alerts') ?? true;
    done..clear()..addAll(p.getStringList('done') ?? []);
    snoozed.clear();
    try {
      (jsonDecode(p.getString('snoozed') ?? '{}') as Map).forEach((k, v) => snoozed['$k'] = DateTime.parse('$v'));
    } catch (_) {/* a damaged value is forgotten */}
    notifyListeners();
  }

  Future<void> _save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString('palette', palette.key);
    await p.setString('mode', mode.name);
    await p.setStringList('leads', leads.map((e) => '$e').toList());
    if (annSeen != null) await p.setString('annSeen', annSeen!.toIso8601String());
    await p.setBool('appLock', appLock);
    await p.setBool('secureScreen', secureScreen);
    await p.setBool('setupDone', setupDone);
    await p.setBool('weekly', weekly);
    await p.setBool('digest', digest);
    await p.setBool('alerts', alerts);
    await p.setStringList('done', done.toList());
    await p.setString('snoozed', jsonEncode(snoozed.map((k, v) => MapEntry(k, v.toIso8601String()))));
  }

  void update(void Function() f) {
    f();
    notifyListeners();
    _save();
    onChanged?.call();
  }
}

/// Signed in or not, what was last read, and how fresh it is. The screens only read from here.
class AppModel extends ChangeNotifier {
  AppModel(this.prefs, {Store? store, GithubAuth? auth, SummarySource? source, Duration splashMin = const Duration(milliseconds: 900), Duration splashMax = const Duration(milliseconds: 3500), Future<bool> Function()? askPermission, Locker? locker, LockPolicy lockPolicy = const LockPolicy(), PortalStore? portalStore, Portal Function({PortalCredentials? credentials})? portalFactory, Future<Directory> Function()? filesDir})
      : _filesDir = filesDir ?? _defaultFilesDir, _portalStore = portalStore ?? PortalStore((store ?? Store()).vault), _portalFactory = portalFactory ?? (({PortalCredentials? credentials}) => Portal(WebViewBrowser(), credentials: credentials)), _store = store ?? Store(), _auth = auth ?? GithubAuth(), _source = source ?? SummarySource(), _splashMin = splashMin, _splashMax = splashMax, _askPermission = askPermission ?? Reminders.allowed, locker = locker ?? DeviceLocker(), _lockPolicy = lockPolicy {
    prefs.onChanged = replan;
  }
  final Prefs prefs;
  final Store _store;
  final PortalStore _portalStore;
  final Portal Function({PortalCredentials? credentials}) _portalFactory;
  final Future<Directory> Function() _filesDir;
  static Future<Directory> _defaultFilesDir() async => Directory('${(await getApplicationDocumentsDirectory()).path}/downloads');
  final GithubAuth _auth;
  final SummarySource _source;

  Phase phase = Phase.loading;
  bool demo = false;
  Summary? summary;
  DateTime? fetchedAt;
  String? login, error, etag;
  DeviceCode? code;
  bool refreshing = false, _cancelSignIn = false;
  int scheduled = 0;
  /// The one-time offer to turn on GitHub background checks after the first sign-in to the portal; hidden for good by "Not now".
  bool cloudOfferHidden = true;
  bool introSeen = true;   // the first-run intro is shown once, only to someone who is signed out

  /// Announcements posted since the Announcements screen was last looked at. The first summary ever read sets the
  /// starting point, so a new install does not start with a pile of "new".
  int get newAnnouncements {
    final s = summary;
    if (s == null) return 0;
    if (prefs.annSeen == null) {
      final latest = s.announcements.map((n) => n.postedAt).whereType<DateTime>().fold<DateTime?>(null, (a, b) => a == null || b.isAfter(a) ? b : a);
      if (latest != null) prefs.annSeen = latest;
      return 0;
    }
    return s.announcements.where((n) => n.postedAt != null && n.postedAt!.isAfter(prefs.annSeen!)).length;
  }

  Clock get clock => demo ? Clock(summary!.generatedAt) : Clock.real();

  /// Hours since the phone last heard from the repository.
  Duration? get age => fetchedAt == null ? null : DateTime.now().difference(fetchedAt!);

  /// The launch screen stays at least this long, and at most [_splashMax]: long enough to read the saved data, look for
  /// anything new on GitHub and plan the reminders before the first screen shows, so the app opens already filled in.
  final Duration _splashMin, _splashMax;
  final Future<bool> Function() _askPermission;
  final Locker locker;
  final LockPolicy _lockPolicy;

  /// True while the lock screen must be shown. Starts true when the lock is on, so a cold start asks first.
  bool locked = false;
  bool _lockChecked = false;
  DateTime? _leftAt;

  /// Called once the settings are read: the app opens locked if the lock is on and the phone can still verify.
  Future<void> _applyLockAtStart() async {
    if (_lockChecked) return;
    _lockChecked = true;
    locked = prefs.appLock && await locker.available();
  }

  /// The app went to the background.
  void noteLeft(DateTime now) => _leftAt = now;

  /// The app came back: lock again if it was away long enough.
  void noteBack(DateTime now) {
    if (_lockPolicy.shouldLock(enabled: prefs.appLock, leftAt: _leftAt, now: now)) { locked = true; notifyListeners(); }
    _leftAt = null;
  }

  /// Asks the phone to verify; unlocks only on a yes.
  Future<bool> unlock() async {
    final ok = await locker.verify('Unlock Assignment Monitor');
    if (ok) { locked = false; notifyListeners(); }
    return ok;
  }

  /// Turns the lock on or off. Turning it on needs the phone to have a lock, and one successful check, so you cannot lock
  /// yourself out with a lock that cannot be answered.
  Future<String?> setAppLock(bool on) async {
    if (on) {
      if (!await locker.available()) return 'Set up a screen lock, fingerprint or face on this phone first.';
      if (!await locker.verify('Turn on the app lock')) return 'The lock was not confirmed, so it stays off.';
    }
    prefs.update(() => prefs.appLock = on);
    if (!on) { locked = false; notifyListeners(); }
    return null;
  }

  /// Android 13 and later show no notification until the user allows it, so the app asks once, as soon as there is
  /// something to remind about. The Allow button in Settings stays for anyone who said no.
  Future<void> askForNotificationsOnce() async {
    if (!Reminders.supported || demo) return;
    final p = await SharedPreferences.getInstance();
    if (p.getBool('askedNotifications') ?? false) return;
    await p.setBool('askedNotifications', true);
    await _askPermission();
    await replan();
  }
  String loadingStep = 'Starting';

  void _step(String s) { loadingStep = s; notifyListeners(); }

  Future<void> start() async {
    final began = DateTime.now();
    Duration spent() => DateTime.now().difference(began);
    _step('Reading your saved data');
    await prefs.load();
    introSeen = (await SharedPreferences.getInstance()).getBool('introSeen') ?? false;
    cloudOfferHidden = (await SharedPreferences.getInstance()).getBool('cloudOfferHidden') ?? false;
    await _applyLockAtStart();
    unawaited(SecureScreen.set(prefs.secureScreen));
    final token = await _store.token();
    hasLogin = await hasPortal();
    portalMode = hasLogin && token == null;   // the data comes from the portal only when there is no GitHub sign-in
    final signedIn = token != null || hasLogin;
    if (signedIn) {
      login = await _store.login();
      final c = await _store.cached();
      summary = c.summary; etag = c.etag; fetchedAt = c.fetchedAt;
      if (summary != null && _splashMax > spent()) {
        _step('Looking for new data');
        // a slow network must not hold the app up: after the limit it opens on what it already has
        await refresh().timeout(_splashMax - spent(), onTimeout: () {});
      }
      if (summary != null) { _step('Planning your reminders'); await replan(); }
    }
    _step(!signedIn ? 'Almost there' : 'Opening your deadlines');
    final left = _splashMin - spent();
    if (!left.isNegative) await Future.delayed(left);
    if (!signedIn) { phase = Phase.signedOut; notifyListeners(); return; }
    phase = summary == null ? Phase.waiting : Phase.ready;
    notifyListeners();
    if (summary == null) unawaited(refresh());
  }

  Future<void> finishIntro() async {
    introSeen = true;
    notifyListeners();
    await (await SharedPreferences.getInstance()).setBool('introSeen', true);
  }

  Future<void> useDemo() async {
    demo = true;
    summary = await Summary.load();
    phase = Phase.ready;
    notifyListeners();
  }

  Future<void> signIn() async {
    error = null; _cancelSignIn = false;
    phase = Phase.signingIn;
    notifyListeners();
    try {
      code = await _auth.start();
      notifyListeners();
      final token = await _auth.approved(code!, cancelled: () => _cancelSignIn);
      login = await _auth.login(token);
      await _store.saveSession(token, login!);
      code = null;
      phase = Phase.waiting;
      notifyListeners();
      await refresh();
    } on SourceError catch (e) {
      error = e.message; code = null; phase = Phase.signedOut;
      notifyListeners();
    } catch (e) {
      error = 'Sign-in failed. Check the connection and try again.'; code = null; phase = Phase.signedOut;
      notifyListeners();
    }
  }

  /// Sign-in with a fine-grained personal access token that can read one repository (Contents: read-only), instead of
  /// the device flow, whose token can touch every repository. The token is checked against GitHub, then kept exactly
  /// like the device-flow one.
  Future<void> signInWithToken(String raw) async {
    final token = raw.trim();
    error = null;
    if (!looksLikeToken(token)) {
      error = 'That does not look like a GitHub token. A fine-grained one starts with github_pat_.';
      notifyListeners();
      return;
    }
    phase = Phase.signingIn;
    notifyListeners();
    try {
      login = await _auth.login(token);
      await _store.saveSession(token, login!);
      phase = Phase.waiting;
      notifyListeners();
      await refresh();
    } on SourceError catch (e) {
      error = e.message; phase = Phase.signedOut;
      notifyListeners();
    } catch (e) {
      error = 'Sign-in failed. Check the connection and try again.'; phase = Phase.signedOut;
      notifyListeners();
    }
  }

  /// A fine-grained token (`github_pat_...`) or a classic one (`ghp_...`); anything with spaces or too short is refused
  /// before it is sent anywhere.
  static bool looksLikeToken(String t) => RegExp(r'^(github_pat_|ghp_)[A-Za-z0-9_]{20,}$').hasMatch(t);

  /// Turns the screenshot and recent-apps protection on or off.
  void setSecureScreen(bool on) {
    prefs.update(() => prefs.secureScreen = on);
    unawaited(SecureScreen.set(on));
  }

  /// The first-run setup (reminders, then the lock offer) is due: signed in with real data and not yet shown.
  bool get firstRunDue => !demo && phase == Phase.ready && !prefs.setupDone;

  void finishFirstRun() => prefs.update(() => prefs.setupDone = true);

  void cancelSignIn() { _cancelSignIn = true; code = null; phase = Phase.signedOut; notifyListeners(); }

  /// Reads only one section's data (the screen's own pull-to-refresh), not the whole portal again. Without a portal login the
  /// summary comes whole from GitHub, so this is the same as [refresh].
  Future<void> refreshSection(String section) async {
    // The lecture list is not in the summary file: with a university login it is read from the portal, apart from the data's source.
    if (section == 'lectures' && hasLogin && !portalMode) {
      if (demo || refreshing) return;
      refreshing = true; notifyListeners();
      try { await _refreshFromPortal(only: {'lectures'}); } finally { refreshing = false; notifyListeners(); }
      return;
    }
    return refresh(only: {section});
  }

  Future<void> refresh({Set<String>? only}) async {
    if (demo || refreshing) return;
    refreshing = true;   // claimed before the first await, so a pull-to-refresh and a resume together cannot both run
    final token = await _store.token();
    hasLogin = await hasPortal();
    portalMode = hasLogin && (token == null || login == null);
    if (portalMode) {
      // no GitHub sign-in: the data comes straight from the portal
      await _refreshFromPortal(only: only);
      refreshing = false; notifyListeners();
      return;
    }
    if (token == null || login == null) { refreshing = false; return; }
    error = null;
    notifyListeners();
    try {
      final f = await _source.fetch(token, login!, etag: etag);
      if (f.unchanged) {
        await _store.touchFetched();
        fetchedAt = DateTime.now();
      } else if (f.missing) {
        if (summary == null && phase != Phase.loading) phase = Phase.waiting;
      } else {
        final lectures = summary?.raw['lectures'];   // the lecture list is read from the portal, not carried by the summary file
        summary = f.summary; etag = f.etag; fetchedAt = DateTime.now();
        if (lectures != null && summary!.raw['lectures'] == null) summary!.raw['lectures'] = lectures;
        await _store.saveSummary(summary!, etag);
        if (phase != Phase.loading) phase = Phase.ready;
        unawaited(replan());
      }
    } on SourceError catch (e) {
      error = e.message;
    } finally {
      refreshing = false;
      notifyListeners();
    }
  }

  Future<void> replan() async {
    final s = summary;
    if (s == null || demo) return;
    unawaited(HomeScreenWidget.update(s, prefs.done));
    scheduled = await Reminders.schedule(s, leads: prefs.leads, done: prefs.done, snoozed: prefs.snoozed, weekly: prefs.weekly, digest: prefs.digest, hide: prefs.appLock);
    notifyListeners();
  }

  Future<void> signOut() async {
    await _store.clear();
    await _portalStore.clear();
    await clearDownloads();   // what was downloaded with this login goes with it
    if (Reminders.supported) { await Reminders.schedule(Summary({'assignments': [], 'schema': 1}), leads: [], done: {}, snoozed: {}); }
    summary = null; login = null; etag = null; fetchedAt = null; demo = false; error = null; cloudFirstCheck = false;
    phase = Phase.signedOut;
    notifyListeners();
  }

  // ---------------------------------------------------------------------------------------------- standalone (portal) mode
  // The phone signs in to the university portal itself (lib/portal.dart). Built in phases: see mobile/STANDALONE.md.

  /// True when the phone holds a portal sign-in: the data then comes straight from the portal.
  bool portalMode = false;

  /// A university login is saved (used for the lecture list and downloads; the data may still come from GitHub).
  bool hasLogin = false;

  /// What the portal read is doing right now ("Reading attendance"), and the parts it had to skip.
  String syncStep = '';
  List<String> syncSkipped = const [];

  /// Per part, what the last read of the portal brought back and how long it took (for finding out why something is missing).
  List<String> syncReport = const [];

  /// How far the read has got: parts finished and parts to read (0 of 0 when nothing is being read).
  int syncDone = 0, syncTotal = 0;

  /// Reads the whole portal with the saved sign-in and replaces the summary. Returns false (with [error] worded for the
  /// student) when it could not.
  Future<bool> _refreshFromPortal({Set<String>? only}) => _serial(() => _readPortal(only: only));

  Future<bool> _readPortal({Set<String>? only}) async {
    final c = await _portalStore.read();
    if (c == null) return false;
    error = null; syncStep = 'Signing in'; notifyListeners();
    final portal = _portalFactory(credentials: c);
    try {
      final r = await portal.signIn(c);
      if (!r.ok) { error = r.message; syncReport = ['sign-in: ${r.problem?.name ?? 'failed'}: ${r.message}']; return false; }
      final campus = campuses.where((x) => x.$2 == c.instituteId).map((x) => x.$1).firstOrNull ?? '';
      final out = await PortalSync(portal).run(
        say: (s) { syncStep = s; notifyListeners(); }, campus: campus, previous: summary?.raw, only: only,
        onProgress: (d, n) { syncDone = d; syncTotal = n; notifyListeners(); },
        // each part fills its screens as soon as it is read; the rest keeps showing the last full read meanwhile
        onPartial: (s) async {
          summary = s; fetchedAt = DateTime.now(); etag = null;
          if (phase != Phase.loading) phase = Phase.ready;
          await _store.saveSummary(s, null);
          notifyListeners();
        },
      );
      summary = out.summary; fetchedAt = DateTime.now(); etag = null;
      // a section refresh only knows about its own part: what failed before in other parts stays listed
      syncSkipped = only == null ? out.skipped : [...syncSkipped.where((k) => !only.contains(k)), ...out.skipped];
      syncReport = out.report;
      await _store.saveSummary(summary!, null);
      if (phase != Phase.loading) phase = Phase.ready;
      unawaited(replan());
      return true;
    } catch (e) {
      final at = syncStep.isEmpty ? '' : ' while: ${syncStep.toLowerCase()}';
      error = 'The portal could not be read just now (${why(e)}$at). Pull down to try again.';
      syncReport = ['failed${at.isEmpty ? '' : at}: ${why(e)}'];
      return false;
    } finally {
      syncStep = ''; syncDone = 0; syncTotal = 0;
      await portal.close();
    }
  }

  /// True when the phone holds a portal sign-in (enrollment number and password, in the keystore).
  Future<bool> hasPortal() async => (await _portalStore.read()) != null;

  /// Tries the sign-in and, only if the portal accepts it, keeps the details in the keystore. Returns what happened and, on
  /// success, the number of courses the LMS lists (a first proof that the whole path works, not just the CMS).
  Future<({SignInResult result, int courses})> connectPortal(PortalCredentials c) => _serial(() => _connectPortal(c));

  Future<({SignInResult result, int courses})> _connectPortal(PortalCredentials c) async {
    if (!c.complete) return (result: const SignInResult.failed(SignInProblem.wrongDetails, 'Enter the enrollment number and the password.'), courses: 0);
    final portal = _portalFactory(credentials: c);
    try {
      final r = await portal.signIn(c);
      if (!r.ok) return (result: r, courses: 0);
      var n = 0;
      try { n = (await portal.courses()).length; } catch (e) { debugPrint('portal courses unavailable'); }
      await _portalStore.save(c);
      return (result: r, courses: n);
    } finally {
      await portal.close();
    }
  }

  /// After a successful sign-in: the first read of the portal starts, and the waiting screen shows what it is doing.
  void beginPortalMode() {
    hasLogin = true; error = null;
    if (!cloudOn) {
      // no GitHub: the portal is the data source (kept for those who use the phone this way)
      portalMode = true;
      if (summary == null) phase = Phase.waiting;   // someone who already has data keeps seeing it while the portal is read
      notifyListeners();
      unawaited(refresh());
      return;
    }
    notifyListeners();
    unawaited(refreshSection('lectures'));   // data stays from GitHub; the login adds the lecture list and downloads
  }

  /// Forgets the saved university login (the lecture list and downloads stop working); the rest of the data is untouched.
  Future<void> removePortalLogin() async {
    await _portalStore.clear();
    hasLogin = false;
    if (portalMode) { portalMode = false; }
    notifyListeners();
  }

  /// Portal jobs (a read, a lecture list, a download) run one after another: two hidden-browser sessions at once would sign in
  /// over each other and fail in ways that look like "the portal is down".
  Future<void> _portalQueue = Future<void>.value();
  Future<T> _serial<T>(Future<T> Function() job) {
    final done = Completer<T>();
    _portalQueue = _portalQueue.whenComplete(() async {
      try {
        // a job that never ends would hold every later one behind it: after six minutes it is stopped and the hidden browser let go of
        done.complete(await job().timeout(const Duration(minutes: 6), onTimeout: () {
          WebViewBrowser.reset();
          throw StateError('The portal took too long and was stopped${syncStep.isEmpty ? '' : ' (at: $syncStep)'}.');
        }));
      } catch (e, s) { done.completeError(e, s); }
    });
    return done.future;
  }

  Future<T> serialForTest<T>(Future<T> Function() job) => _serial(job);

  /// A few words on why something failed (no page text, no links), for the banner and the read report.
  static String why(Object e) {
    final text = e is StateError ? e.message : e is ArgumentError ? '${e.message}' : '${e.runtimeType}: ${'$e'.replaceAll(RegExp(r'\s+'), ' ')}';
    return text.length > 90 ? text.substring(0, 90) : text;
  }

  /// Runs [job] with a signed-in portal and a folder for downloads, then throws the session away. Each file action signs in
  /// on its own (about 15 seconds), so nothing stays open between taps and a dropped session is never reused.
  Future<T> withPortalFiles<T>(Future<T> Function(PortalFiles files) job) => _serial(() => _withPortalFiles(job));

  Future<T> _withPortalFiles<T>(Future<T> Function(PortalFiles files) job) async {
    final c = await _portalStore.read();
    if (c == null) throw FileProblem('Sign in with your university login (Settings) to use files.');
    final portal = _portalFactory(credentials: c);
    try {
      final r = await portal.signIn(c);
      if (!r.ok) throw FileProblem(r.message);
      return await job(PortalFiles(portal, await _filesDir()));
    } finally {
      await portal.close();
    }
  }


  /// True when GitHub background checks are connected (a GitHub sign-in exists).
  bool get cloudOn => login != null;

  /// Whether to show the offer: only in portal mode, only until GitHub checks are on or the student said "Not now".
  bool get offerCloud => portalMode && !cloudOn && !cloudOfferHidden && phase == Phase.ready && !demo;

  Future<void> hideCloudOffer() async {
    cloudOfferHidden = true;
    notifyListeners();
    await (await SharedPreferences.getInstance()).setBool('cloudOfferHidden', true);
  }

  /// The saved portal login, for the GitHub setup to use so it is not typed twice.
  Future<PortalCredentials?> savedPortalLogin() => _portalStore.read();

  /// Deletes every lecture file and brief saved on the phone. Returns how many files were removed.
  Future<int> clearDownloads() async {
    try {
      final dir = await _filesDir();
      if (!await dir.exists()) return 0;
      var n = 0;
      await for (final e in dir.list(recursive: true, followLinks: false)) { if (e is File) n++; }
      await dir.delete(recursive: true);
      return n;
    } catch (e) {
      debugPrint('clearing downloads failed');
      return 0;
    }
  }

  Future<void> forgetPortal() => _portalStore.clear();

  // ---------------------------------------------------------------------------------------------- phone-only Cloud checks
  // (added for the phone-only setup, lib/screens/cloud_setup_screens.dart; kept together at the end of the class)

  /// True from the end of the phone-only setup until the first summary arrives or the user signs out: the waiting screen
  /// says the first check is running instead of telling the student to start one by hand.
  bool cloudFirstCheck = false;

  /// The saved GitHub token, for the Cloud checks screens (they talk to GitHub themselves). Never shown or logged.
  Future<String?> cloudToken() => _store.token();

  /// The setup finished: keep the sign-in it ended with (the wider "repo workflow" one) exactly like a normal sign-in, and
  /// land on the waiting screen, which fills in when the first check has written the summary.
  Future<void> adoptSession(String token, String githubLogin) async {
    await _store.saveSession(token, githubLogin);
    login = githubLogin; error = null; demo = false; code = null;
    cloudFirstCheck = true;
    phase = summary == null ? Phase.waiting : phase;
    notifyListeners();
    unawaited(refresh());
  }
}

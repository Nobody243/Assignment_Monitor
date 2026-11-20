// ignore_for_file: prefer_initializing_formals
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'data.dart';
import 'lock.dart';
import 'secure_screen.dart';
import 'reminders.dart';
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
  AppModel(this.prefs, {Store? store, GithubAuth? auth, SummarySource? source, Duration splashMin = const Duration(milliseconds: 1800), Duration splashMax = const Duration(milliseconds: 3500), Future<bool> Function()? askPermission, Locker? locker, LockPolicy lockPolicy = const LockPolicy()})
      : _store = store ?? Store(), _auth = auth ?? GithubAuth(), _source = source ?? SummarySource(), _splashMin = splashMin, _splashMax = splashMax, _askPermission = askPermission ?? Reminders.allowed, locker = locker ?? DeviceLocker(), _lockPolicy = lockPolicy {
    prefs.onChanged = replan;
  }
  final Prefs prefs;
  final Store _store;
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
    await _applyLockAtStart();
    unawaited(SecureScreen.set(prefs.secureScreen));
    final token = await _store.token();
    if (token != null) {
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
    _step(token == null ? 'Almost there' : 'Opening your deadlines');
    final left = _splashMin - spent();
    if (!left.isNegative) await Future.delayed(left);
    if (token == null) { phase = Phase.signedOut; notifyListeners(); return; }
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

  Future<void> refresh() async {
    if (demo || refreshing) return;
    refreshing = true;   // claimed before the first await, so a pull-to-refresh and a resume together cannot both run
    final token = await _store.token();
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
        summary = f.summary; etag = f.etag; fetchedAt = DateTime.now();
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
    if (Reminders.supported) { await Reminders.schedule(Summary({'assignments': [], 'schema': 1}), leads: [], done: {}, snoozed: {}); }
    summary = null; login = null; etag = null; fetchedAt = null; demo = false; error = null;
    phase = Phase.signedOut;
    notifyListeners();
  }
}

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'data.dart';
import 'reminders.dart';
import 'source.dart';
import 'theme.dart';

enum Phase { loading, signedOut, signingIn, waiting, ready }

/// App-wide choices the Settings screen changes, saved on the phone.
class Prefs extends ChangeNotifier {
  Palette palette = palettes.first;
  ThemeMode mode = ThemeMode.system;
  List<int> leads = [24, 3, 1];
  final Set<String> done = {};
  final Map<String, DateTime> snoozed = {};
  void Function()? onChanged;   // the model re-plans reminders when a choice that affects them changes

  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    palette = palettes.firstWhere((x) => x.key == p.getString('palette'), orElse: () => palettes.first);
    mode = ThemeMode.values.firstWhere((x) => x.name == p.getString('mode'), orElse: () => ThemeMode.system);
    leads = (p.getStringList('leads') ?? ['24', '3', '1']).map(int.parse).toList();
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
  AppModel(this.prefs) { prefs.onChanged = replan; }
  final Prefs prefs;
  final _store = Store();
  final _auth = GithubAuth();
  final _source = SummarySource();

  Phase phase = Phase.loading;
  bool demo = false;
  Summary? summary;
  DateTime? fetchedAt;
  String? login, error, etag;
  DeviceCode? code;
  bool refreshing = false, _cancelSignIn = false;
  int scheduled = 0;

  Clock get clock => demo ? Clock(summary!.generatedAt) : Clock.real();

  /// Hours since the phone last heard from the repository.
  Duration? get age => fetchedAt == null ? null : DateTime.now().difference(fetchedAt!);

  Future<void> start() async {
    await prefs.load();
    final token = await _store.token();
    if (token == null) { phase = Phase.signedOut; notifyListeners(); return; }
    login = await _store.login();
    final c = await _store.cached();
    summary = c.summary; etag = c.etag; fetchedAt = c.fetchedAt;
    phase = summary == null ? Phase.waiting : Phase.ready;
    notifyListeners();
    unawaited(refresh());
    unawaited(replan());
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

  void cancelSignIn() { _cancelSignIn = true; code = null; phase = Phase.signedOut; notifyListeners(); }

  Future<void> refresh() async {
    if (demo || refreshing) return;
    final token = await _store.token();
    if (token == null || login == null) return;
    refreshing = true; error = null;
    notifyListeners();
    try {
      final f = await _source.fetch(token, login!, etag: etag);
      if (f.unchanged) {
        await _store.touchFetched();
        fetchedAt = DateTime.now();
      } else if (f.missing) {
        if (summary == null) phase = Phase.waiting;
      } else {
        summary = f.summary; etag = f.etag; fetchedAt = DateTime.now();
        await _store.saveSummary(summary!, etag);
        phase = Phase.ready;
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
    scheduled = await Reminders.schedule(s, leads: prefs.leads, done: prefs.done, snoozed: prefs.snoozed);
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

import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:workmanager/workmanager.dart';

import 'alerts.dart';
import 'model.dart';
import 'reminders.dart';
import 'source.dart';
import 'widget.dart';

/// Checking for news while the app is closed. Android runs [backgroundDispatcher] about every two hours (its own minimum
/// is 15 minutes, and it may delay the run to save battery); the check reads the same summary file with the same sign-in,
/// compares it with the saved copy, and shows a notification for each new announcement, assignment, extension, mark,
/// exam seat or result. No server is involved: the phone asks GitHub, exactly as it does when it is open.
const _taskName = 'am.check';

@pragma('vm:entry-point')
void backgroundDispatcher() {
  Workmanager().executeTask((task, input) async {
    WidgetsFlutterBinding.ensureInitialized();
    try {
      await BackgroundCheck.run();
      return true;
    } catch (e) {
      debugPrint('background check: $e');
      return false;   // Android retries later with backoff
    }
  });
}

class BackgroundCheck {
  /// One pass: fetch, compare, notify, save, re-plan reminders. Returns how many notifications were shown.
  static Future<int> run({Store? store, SummarySource? source, DateTime? now, Future<void> Function(AlertText, int)? notify}) async {
    final st = store ?? Store();
    final token = await st.token();
    final login = await st.login();
    if (token == null || login == null) return 0;
    final prefs = Prefs();
    await prefs.load();
    final cached = await st.cached();
    final fetched = await (source ?? SummarySource()).fetch(token, login, etag: cached.etag);
    if (fetched.unchanged || fetched.missing || fetched.summary == null) {
      await st.touchFetched();
      return 0;
    }
    final fresh = fetched.summary!;
    var shown = 0;
    final before = cached.summary;
    if (prefs.alerts && before != null) {
      final changes = changesBetween(before, fresh);
      final send = notify ?? Reminders.showNow;
      var i = 0;
      for (final m in messagesFor(changes)) {
        await send(Reminders.maskNews(m, hide: prefs.appLock), 7000 + i++);
        shown++;
      }
    }
    await st.saveSummary(fresh, fetched.etag);
    await HomeScreenWidget.update(fresh, prefs.done);
    // the saved copy changed, so what is planned changes too (a new deadline needs its reminders)
    await Reminders.schedule(fresh, leads: prefs.leads, done: prefs.done, snoozed: prefs.snoozed, weekly: prefs.weekly, digest: prefs.digest, hide: prefs.appLock);
    return shown;
  }

  /// Starts or stops the periodic check to match the setting. Does nothing off Android.
  static Future<void> apply({required bool on}) async {
    if (!Reminders.supported || !Reminders.isAndroid) return;   // the background check is Android only for now
    final wm = Workmanager();
    await wm.initialize(backgroundDispatcher);
    if (on) {
      await wm.registerPeriodicTask(
        _taskName, _taskName,
        frequency: const Duration(hours: 2),
        constraints: Constraints(networkType: NetworkType.connected),
        existingWorkPolicy: ExistingPeriodicWorkPolicy.update,
      );
    } else {
      await wm.cancelByUniqueName(_taskName);
    }
  }

  /// Reads the saved setting (the app may be starting for the first time) and applies it.
  static Future<void> applySaved() async {
    final on = (await SharedPreferences.getInstance()).getBool('alerts') ?? true;
    await apply(on: on);
  }
}

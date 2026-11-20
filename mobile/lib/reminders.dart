import 'dart:convert';

import 'package:flutter/foundation.dart' hide Summary;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'alerts.dart';
import 'data.dart';

/// Deadline reminders scheduled on the phone itself, so they fire with no network and no server.
/// Quiet hours (23:00 to 07:00) are delivered silently. Snooze and Done are notification buttons.
class Reminders {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _ready = false;
  /// Tests set this to false so scheduling never reaches the notification plugin.
  @visibleForTesting
  static bool? forceSupported;
  static bool get supported => forceSupported ?? (!kIsWeb && defaultTargetPlatform == TargetPlatform.android);

  static const _loud = AndroidNotificationDetails('deadlines', 'Deadlines',
      channelDescription: 'Reminders before an assignment is due', importance: Importance.high, priority: Priority.high,
      actions: [AndroidNotificationAction('snooze', 'Snooze 1 h'), AndroidNotificationAction('done', 'Done')]);
  static const _quiet = AndroidNotificationDetails('quiet', 'Quiet hours',
      channelDescription: 'Reminders that fall between 23:00 and 07:00 arrive silently', importance: Importance.low, priority: Priority.low,
      playSound: false, enableVibration: false,
      actions: [AndroidNotificationAction('snooze', 'Snooze 1 h'), AndroidNotificationAction('done', 'Done')]);

  static const _news = AndroidNotificationDetails('news', 'Updates',
      channelDescription: 'New announcements, assignments, extensions, marks, exam seats and results', importance: Importance.high, priority: Priority.high);
  static const _digest = AndroidNotificationDetails('digest', 'Summaries',
      channelDescription: 'Your morning digest and the Sunday summary', importance: Importance.defaultImportance, priority: Priority.defaultPriority);

  static Future<void> init() async {
    if (!supported || _ready) return;
    tzdata.initializeTimeZones();
    try {
      tz.setLocalLocation(tz.getLocation((await FlutterTimezone.getLocalTimezone()).identifier));
    } catch (e) {
      debugPrint('timezone: $e');
    }
    await _plugin.initialize(
      settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/launcher_icon')),
      onDidReceiveNotificationResponse: _answer,
      onDidReceiveBackgroundNotificationResponse: answerInBackground,
    );
    _ready = true;
  }

  /// Asks for the notification permission (Android 13+). Returns whether reminders can show.
  static Future<bool> allowed() async {
    if (!supported) return false;
    await init();
    final a = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    return await a?.requestNotificationsPermission() ?? false;
  }

  /// The reminders the summary and settings call for, soonest first, at most 60 (Android keeps a limited number).
  /// Pure: no notification plugin involved, so it is tested without a phone.
  static List<PlannedReminder> plan(Summary s, {required List<int> leads, required Set<String> done, required Map<String, DateTime> snoozed, required DateTime now}) {
    final out = <PlannedReminder>[];
    for (final w in s.work) {
      if (!w.todo || !w.open || w.due == null || done.contains(w.id)) continue;
      for (final h in leads) {
        final at = w.due!.subtract(Duration(hours: h));
        if (at.isAfter(now)) out.add(PlannedReminder(w, at, h));
      }
      final wake = snoozed[w.id];
      if (wake != null && wake.isAfter(now) && wake.isBefore(w.due!)) out.add(PlannedReminder(w, wake, null));
    }
    out.sort((a, b) => a.at.compareTo(b.at));
    return out.take(60).toList();
  }

  /// The Sunday summary (Sunday 18:00) and the morning digest (07:30), each only when switched on and only when there is
  /// something to say at that time. Pure, like [plan].
  static List<PlannedMessage> planMessages(Summary s, {required bool weekly, required bool digest, required DateTime now}) {
    final out = <PlannedMessage>[];
    if (weekly) {
      var at = DateTime(now.year, now.month, now.day, 18);
      at = at.add(Duration(days: (DateTime.sunday - at.weekday) % 7));
      if (!at.isAfter(now)) at = at.add(const Duration(days: 7));
      final m = weeklySummary(s, at);
      if (m != null) out.add(PlannedMessage(9001, at, m, false));
    }
    if (digest) {
      var at = DateTime(now.year, now.month, now.day, 7, 30);
      if (!at.isAfter(now)) at = at.add(const Duration(days: 1));
      final m = dailyDigest(s, at);
      if (m != null) out.add(PlannedMessage(9002, at, m, true));
    }
    return out;
  }

  /// Replaces every scheduled reminder with the ones the current summary and settings call for.
  static Future<int> schedule(Summary s, {required List<int> leads, required Set<String> done, required Map<String, DateTime> snoozed, bool weekly = false, bool digest = false}) async {
    if (!supported) return 0;
    await init();
    await _plugin.cancelAll();
    final now = DateTime.now();
    final planned = plan(s, leads: leads, done: done, snoozed: snoozed, now: now);
    for (final p in planned) {
      await _show(p.work, p.at, p.hours, _idFor(p.work.id, p.hours ?? 99));
    }
    final messages = planMessages(s, weekly: weekly, digest: digest, now: now);
    for (final m in messages) {
      await _plugin.zonedSchedule(
        id: m.id, title: m.message.title, body: m.message.body, scheduledDate: tz.TZDateTime.from(m.at, tz.local),
        notificationDetails: const NotificationDetails(android: _digest), androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    }
    return planned.length + messages.length;
  }

  /// Shows a notification now (used by the background check for new announcements, marks, seats and results).
  static Future<void> showNow(AlertText m, int id) async {
    if (!supported) return;
    await init();
    await _plugin.show(id: id, title: m.title, body: m.body, notificationDetails: const NotificationDetails(android: _news));
  }

  static Future<void> _show(Work w, DateTime at, int? hours, int id) {
    final quiet = at.hour >= 23 || at.hour < 7;
    final left = hours == null ? 'is still open' : hours == 1 ? 'is due in 1 hour' : 'is due in $hours hours';
    return _plugin.zonedSchedule(
      id: id,
      title: '${w.course}: ${w.title}',
      body: 'Assignment ${w.number} $left.'.replaceAll('  ', ' '),
      scheduledDate: tz.TZDateTime.from(at, tz.local),
      notificationDetails: NotificationDetails(android: quiet ? _quiet : _loud),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      payload: w.id,
    );
  }

  static int _idFor(String assignmentId, int slot) => (assignmentId.hashCode.abs() % 20000000) * 100 + slot;

  static Future<void> _answer(NotificationResponse r) => answerInBackground(r);
}

/// Snooze or Done tapped on a notification, possibly while the app is closed: write the choice where the app reads it.
@pragma('vm:entry-point')
Future<void> answerInBackground(NotificationResponse r) async {
  final id = r.payload;
  if (id == null) return;
  final p = await SharedPreferences.getInstance();
  if (r.actionId == 'done') {
    p.setStringList('done', <String>{...(p.getStringList('done') ?? <String>[]), id}.toList());
  } else if (r.actionId == 'snooze') {
    final m = Map<String, dynamic>.from(jsonDecode(p.getString('snoozed') ?? '{}') as Map);
    m[id] = DateTime.now().add(const Duration(hours: 1)).toIso8601String();
    p.setString('snoozed', jsonEncode(m));
  }
}

class PlannedReminder {
  const PlannedReminder(this.work, this.at, this.hours);
  final Work work;
  final DateTime at;

  /// Hours before the deadline, or null for a snooze that wakes the reminder up again.
  final int? hours;
}

class PlannedMessage {
  const PlannedMessage(this.id, this.at, this.message, this.daily);
  final int id;
  final DateTime at;
  final AlertText message;
  final bool daily;
}

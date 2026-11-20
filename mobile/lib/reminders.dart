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
  static bool get isAndroid => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
  static bool get isIOS => !kIsWeb && defaultTargetPlatform == TargetPlatform.iOS;

  /// Reminders work on Android and on iOS. (The Snooze and Done buttons on a notification, and the background check for
  /// news, are Android only for now.)
  static bool get supported => forceSupported ?? (isAndroid || isIOS);

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

  static DarwinNotificationDetails _ios(bool quiet) => DarwinNotificationDetails(presentSound: !quiet);

  static Future<void> init() async {
    if (!supported || _ready) return;
    tzdata.initializeTimeZones();
    try {
      tz.setLocalLocation(tz.getLocation((await FlutterTimezone.getLocalTimezone()).identifier));
    } catch (e) {
      debugPrint('timezone: $e');
    }
    await _plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/launcher_icon'),
        // the permission is asked for by allowed(), once there is something to remind about, not at start-up
        iOS: DarwinInitializationSettings(requestAlertPermission: false, requestBadgePermission: false, requestSoundPermission: false),
      ),
      onDidReceiveNotificationResponse: _answer,
      onDidReceiveBackgroundNotificationResponse: answerInBackground,
    );
    _ready = true;
  }

  /// Asks for the notification permission (Android 13+). Returns whether reminders can show.
  static Future<bool> allowed() async {
    if (!supported) return false;
    await init();
    if (isIOS) {
      final i = _plugin.resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>();
      return await i?.requestPermissions(alert: true, badge: false, sound: true) ?? false;
    }
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
  static Future<int> schedule(Summary s, {required List<int> leads, required Set<String> done, required Map<String, DateTime> snoozed, bool weekly = false, bool digest = false, bool hide = false}) async {
    if (!supported) return 0;
    await init();
    await _plugin.cancelAll();
    final now = DateTime.now();
    final planned = plan(s, leads: leads, done: done, snoozed: snoozed, now: now);
    for (final p in planned) {
      await _show(p.work, p.at, p.hours, _idFor(p.work.id, p.hours ?? 99), hide: hide);
    }
    final messages = planMessages(s, weekly: weekly, digest: digest, now: now);
    for (final m in messages) {
      await _plugin.zonedSchedule(
        id: m.id, title: maskSummary(m.message, hide: hide, daily: m.daily).title, body: maskSummary(m.message, hide: hide, daily: m.daily).body, scheduledDate: tz.TZDateTime.from(m.at, tz.local),
        notificationDetails: const NotificationDetails(android: _digest, iOS: DarwinNotificationDetails()), androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    }
    return planned.length + messages.length;
  }

  /// Shows a notification now (used by the background check for new announcements, marks, seats and results).
  static Future<void> showNow(AlertText m, int id) async {
    if (!supported) return;
    await init();
    await _plugin.show(id: id, title: m.title, body: m.body, notificationDetails: const NotificationDetails(android: _news, iOS: DarwinNotificationDetails()));
  }

  // ---- what a notification says. With the app lock on, the lock screen must not say what is due or what changed, so the
  // ---- text is generic and the details are one tap away inside the (locked) app.
  static AlertText reminderText({required String course, required String title, required String number, int? hours, required bool hide}) {
    if (hide) return (title: 'Assignment due soon', body: 'Open the app to see which one.');
    final left = hours == null ? 'is still open' : hours == 1 ? 'is due in 1 hour' : 'is due in $hours hours';
    return (title: '${course.isEmpty ? '' : '$course: '}$title', body: 'Assignment $number $left.'.replaceAll('  ', ' '));
  }

  static AlertText maskNews(AlertText m, {required bool hide}) => hide ? (title: 'Assignment Monitor', body: 'There is something new. Open the app to see it.') : m;

  static AlertText maskSummary(AlertText m, {required bool hide, required bool daily}) =>
      hide ? (title: daily ? 'Your day' : 'Your week ahead', body: 'Open the app for the details.') : m;

  static Future<void> _show(Work w, DateTime at, int? hours, int id, {required bool hide}) {
    final quiet = at.hour >= 23 || at.hour < 7;
    final text = reminderText(course: w.course, title: w.title, number: w.number, hours: hours, hide: hide);
    return _plugin.zonedSchedule(
      id: id,
      title: text.title,
      body: text.body,
      scheduledDate: tz.TZDateTime.from(at, tz.local),
      notificationDetails: NotificationDetails(android: quiet ? _quiet : _loud, iOS: _ios(quiet)),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      payload: payloadFor(w),
    );
  }

  static int _idFor(String assignmentId, int slot) => (assignmentId.hashCode.abs() % 20000000) * 100 + slot;
  static const _slots = [48, 24, 12, 6, 3, 1, 99];   // every lead time that can exist, and 99 for a snooze wake-up

  /// What a reminder carries, so a button tapped with the app closed knows which assignment it is about.
  static String payloadFor(Work w) => jsonEncode({'id': w.id, 'title': w.title, 'course': w.course, 'number': w.number});

  /// Reads a payload (an older build wrote just the id), or null when there is none.
  static ({String id, String title, String course, String number})? parsePayload(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    try {
      final d = jsonDecode(raw);
      if (d is Map && d['id'] is String) return (id: d['id'] as String, title: '${d['title'] ?? 'Assignment'}', course: '${d['course'] ?? ''}', number: '${d['number'] ?? ''}');
    } catch (_) {/* not JSON: the old format */}
    return (id: raw, title: 'Assignment', course: '', number: '');
  }

  /// Done: every reminder still waiting for this assignment is cancelled, not just the one on screen.
  static Future<void> cancelFor(String assignmentId) async {
    if (!supported) return;
    await init();
    for (final slot in _slots) { await _plugin.cancel(id: _idFor(assignmentId, slot)); }
  }

  /// Snooze: the notification on screen goes away and a new one comes back at [at].
  static Future<void> snoozeUntil(({String id, String title, String course, String number}) a, DateTime at, {int? shownId, bool hide = false}) async {
    if (!supported) return;
    await init();
    if (shownId != null) await _plugin.cancel(id: shownId);
    final quiet = at.hour >= 23 || at.hour < 7;
    await _plugin.zonedSchedule(
      id: _idFor(a.id, 99), title: reminderText(course: a.course, title: a.title, number: a.number, hide: hide).title, body: reminderText(course: a.course, title: a.title, number: a.number, hide: hide).body,
      scheduledDate: tz.TZDateTime.from(at, tz.local), notificationDetails: NotificationDetails(android: quiet ? _quiet : _loud, iOS: _ios(quiet)),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      payload: jsonEncode({'id': a.id, 'title': a.title, 'course': a.course, 'number': a.number}),
    );
  }

  static Future<void> _answer(NotificationResponse r) => answerInBackground(r);
}

/// Snooze or Done tapped on a notification, possibly while the app is closed. The choice is saved where the app reads it,
/// and acted on at once: Done cancels every reminder still waiting for that assignment, Snooze brings this one back in
/// an hour.
@pragma('vm:entry-point')
Future<void> answerInBackground(NotificationResponse r) async {
  final a = Reminders.parsePayload(r.payload);
  if (a == null) return;
  final p = await SharedPreferences.getInstance();
  if (r.actionId == 'done') {
    await p.setStringList('done', <String>{...(p.getStringList('done') ?? <String>[]), a.id}.toList());
    await Reminders.cancelFor(a.id);
  } else if (r.actionId == 'snooze') {
    final wake = DateTime.now().add(const Duration(hours: 1));
    final m = Map<String, dynamic>.from(jsonDecode(p.getString('snoozed') ?? '{}') as Map);
    m[a.id] = wake.toIso8601String();
    await p.setString('snoozed', jsonEncode(m));
    await Reminders.snoozeUntil(a, wake, shownId: r.id, hide: p.getBool('appLock') ?? false);
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

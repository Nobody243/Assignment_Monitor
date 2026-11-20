import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/painting.dart';
import 'package:image/image.dart' as img;
import 'package:pdf/pdf.dart' as pdf;
import 'package:pdf/widgets.dart' as pw;

import 'data.dart';

/// Draws the week timetable as a picture (PNG, JPG) or a one-page PDF, the same way the desktop app does:
/// a clean week grid, a block per class, a legend underneath. No widgets and no screenshots, so the file looks
/// the same on every phone.
class TimetableExport {
  static const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  static const _full = {'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday', 'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'};

  // course fills: muted, one per course, light and dark variants
  static const _lightFill = [Color(0xFFF1DDD5), Color(0xFFDDE6D6), Color(0xFFD9E2EE), Color(0xFFEFE5CC), Color(0xFFE6DCE5), Color(0xFFD5E6E5), Color(0xFFE5E2DB), Color(0xFFEBD9D6)];
  static const _darkFill = [Color(0xFF4A3029), Color(0xFF2F3D2B), Color(0xFF2B3A4D), Color(0xFF473D22), Color(0xFF3D2F3C), Color(0xFF254240), Color(0xFF3A3731), Color(0xFF47312E)];

  static int _mins(String s) { final p = s.split(':'); return int.parse(p[0]) * 60 + int.parse(p[1]); }

  static bool hasClasses(Summary s) => s.timetable.isNotEmpty;

  /// The picture, as PNG bytes. [scale] 2 gives a sharp image on a phone and in print.
  static Future<Uint8List> png(Summary s, {bool dark = false, double scale = 2}) async {
    final slots = s.timetable;
    final used = {for (final c in slots) c.day};
    final days = [for (var i = 0; i < _days.length; i++) if (i < 5 || used.contains(_days[i])) _days[i]];
    final courses = ({for (final c in slots) c.course}.toList()..sort());
    final startH = slots.map((c) => _mins(c.start)).reduce((a, b) => a < b ? a : b) ~/ 60;
    final endH = (slots.map((c) => _mins(c.end)).reduce((a, b) => a > b ? a : b) + 59) ~/ 60;

    const w = 1200.0, margin = 36.0, timeCol = 64.0, headH = 110.0, dayH = 44.0, hourH = 78.0;
    final grid = (endH - startH) * hourH;
    final legendRows = (courses.length / 3).ceil();
    final h = headH + dayH + grid + 36 + legendRows * 34 + 36;

    final bg = dark ? const Color(0xFF16120F) : const Color(0xFFFFFAF6);
    final surface = dark ? const Color(0xFF241E1A) : const Color(0xFFFFFFFF);
    final ink = dark ? const Color(0xFFF4EBE5) : const Color(0xFF241A15);
    final muted = dark ? const Color(0xFFCDBFB6) : const Color(0xFF5A4A41);
    final line = dark ? const Color(0xFF3A3029) : const Color(0xFFE6D6CA);
    final accent = const Color(0xFFE8552B);

    final rec = ui.PictureRecorder();
    final c = Canvas(rec, Rect.fromLTWH(0, 0, w * scale, h * scale))..scale(scale);
    c.drawRect(Rect.fromLTWH(0, 0, w, h), Paint()..color = bg);

    void text(String t, Offset at, {double size = 16, FontWeight weight = FontWeight.w500, Color? color, double? maxWidth, TextAlign align = TextAlign.left, int maxLines = 1}) {
      final tp = TextPainter(
        text: TextSpan(text: t, style: TextStyle(fontSize: size, fontWeight: weight, color: color ?? ink, height: 1.2)),
        textDirection: TextDirection.ltr, textAlign: align, maxLines: maxLines, ellipsis: '…',
      )..layout(maxWidth: maxWidth ?? w);
      tp.paint(c, align == TextAlign.center && maxWidth != null ? at : at);
    }

    // header
    text('Timetable', const Offset(margin, 30), size: 34, weight: FontWeight.w800);
    text([if (s.semester.isNotEmpty) s.semester, s.studentName].where((e) => e.isNotEmpty).join('  ·  '), const Offset(margin, 78), size: 17, color: muted);

    // day columns
    final colW = (w - margin * 2 - timeCol) / days.length;
    final top = headH;
    c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(margin, top, w - margin * 2, dayH + grid), const Radius.circular(20)), Paint()..color = surface);
    for (var i = 0; i < days.length; i++) {
      final x = margin + timeCol + i * colW;
      text(_full[days[i]]!, Offset(x, top + 13), size: 16, weight: FontWeight.w700, maxWidth: colW, align: TextAlign.center);
      if (i > 0) c.drawLine(Offset(x, top + dayH), Offset(x, top + dayH + grid), Paint()..color = line);
    }
    for (var i = 0; i <= endH - startH; i++) {
      final y = top + dayH + i * hourH;
      c.drawLine(Offset(margin + timeCol - 8, y), Offset(w - margin, y), Paint()..color = line);
      if (i < endH - startH) text('${(startH + i).toString().padLeft(2, '0')}:00', Offset(margin + 10, y + 6), size: 13, color: muted);
    }

    // classes
    for (final s in slots) {
      final di = days.indexOf(s.day);
      if (di < 0) continue;
      final x = margin + timeCol + di * colW + 5;
      final y = top + dayH + (_mins(s.start) - startH * 60) / 60 * hourH + 2;
      final bh = (_mins(s.end) - _mins(s.start)) / 60 * hourH - 4;
      final k = courses.indexOf(s.course) % _lightFill.length;
      final r = RRect.fromRectAndRadius(Rect.fromLTWH(x, y, colW - 10, bh), const Radius.circular(12));
      c.drawRRect(r, Paint()..color = (dark ? _darkFill : _lightFill)[k]);
      c.save();
      c.clipRRect(r);
      text(s.course, Offset(x + 10, y + 8), size: 14.5, weight: FontWeight.w700, maxWidth: colW - 30, maxLines: bh > 70 ? 3 : 2);
      if (bh > 58) text('${s.start} – ${s.end}', Offset(x + 10, y + bh - 24), size: 12.5, color: muted, maxWidth: colW - 30);
      c.restore();
    }

    // legend
    final ly = top + dayH + grid + 30;
    for (var i = 0; i < courses.length; i++) {
      final lx = margin + (i % 3) * ((w - margin * 2) / 3);
      final y = ly + (i ~/ 3) * 34;
      c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(lx, y + 3, 18, 18), const Radius.circular(6)), Paint()..color = (dark ? _darkFill : _lightFill)[i % _lightFill.length]);
      text(courses[i], Offset(lx + 28, y + 2), size: 15, maxWidth: (w - margin * 2) / 3 - 40);
    }
    text('Assignment Monitor', Offset(margin, h - 34), size: 13, color: muted);
    c.drawCircle(Offset(w - margin - 4, h - 25), 4, Paint()..color = accent);

    final image = await rec.endRecording().toImage((w * scale).round(), (h * scale).round());
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    return data!.buffer.asUint8List();
  }

  static Future<Uint8List> jpg(Summary s, {bool dark = false}) async {
    final decoded = img.decodePng(await png(s, dark: dark))!;
    return Uint8List.fromList(img.encodeJpg(decoded, quality: 92));
  }

  static Future<Uint8List> pdfFile(Summary s, {bool dark = false}) async {
    final bytes = await png(s, dark: dark);
    final decoded = img.decodePng(bytes)!;
    final doc = pw.Document(title: 'Timetable', author: 'Assignment Monitor');
    final ratio = decoded.width / decoded.height;
    doc.addPage(pw.Page(
      pageFormat: pdf.PdfPageFormat(842, 842 / ratio, marginAll: 0),
      build: (_) => pw.Image(pw.MemoryImage(bytes), fit: pw.BoxFit.fill),
    ));
    return doc.save();
  }
}

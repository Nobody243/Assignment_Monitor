import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/source.dart';

/// Keeps the sign-in and the last summary in memory, so the model runs without a phone's keystore.
class MemoryStore extends Store {
  MemoryStore() : super(vault: MemoryVault());
  String? tokenV, loginV, etagV;
  Summary? summaryV;
  DateTime? fetchedV;
  bool cleared = false;
  @override Future<String?> token() async => tokenV;
  @override Future<String?> login() async => loginV;
  @override Future<void> saveSession(String token, String login) async { tokenV = token; loginV = login; }
  @override Future<({Summary? summary, String? etag, DateTime? fetchedAt})> cached() async => (summary: summaryV, etag: etagV, fetchedAt: fetchedV);
  @override Future<void> saveSummary(Summary s, String? etag) async { summaryV = s; etagV = etag; fetchedV = DateTime.now(); }
  @override Future<void> touchFetched() async => fetchedV = DateTime.now();
  @override Future<void> clear() async { tokenV = loginV = etagV = null; summaryV = null; cleared = true; }
}

/// A vault that lives in memory, so the real Store (its keystore and plain-preference split) is tested without a phone.
class MemoryVault implements Vault {
  final data = <String, String>{};
  @override Future<String?> read(String key) async => data[key];
  @override Future<void> write(String key, String value) async => data[key] = value;
  @override Future<void> delete(String key) async => data.remove(key);
}

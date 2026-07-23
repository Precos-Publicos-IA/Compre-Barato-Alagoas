import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:permission_handler/permission_handler.dart';

/// Local notifications when a long SEFAZ/web search finishes.
///
/// Web: no system notification (browser APIs vary); UI still shows the promise.
/// Android/iOS: `flutter_local_notifications` + runtime permission when needed.
class SearchNotifications {
  SearchNotifications._();
  static final SearchNotifications instance = SearchNotifications._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;
  bool _initFailed = false;

  static const _channelId = 'search_done';
  static const _channelName = 'Busca de preços';
  static const _channelDesc =
      'Aviso quando a comparação de preços da sua lista termina.';
  static const _notificationId = 7101;

  /// True when this platform can show a system notification after init.
  bool get isSupported => !kIsWeb && !_initFailed;

  Future<void> ensureInitialized() async {
    if (kIsWeb || _initialized || _initFailed) return;
    try {
      const android = AndroidInitializationSettings('@mipmap/ic_launcher');
      const ios = DarwinInitializationSettings(
        requestAlertPermission: false,
        requestBadgePermission: false,
        requestSoundPermission: false,
      );
      await _plugin.initialize(
        const InitializationSettings(android: android, iOS: ios),
      );
      final androidPlugin = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      await androidPlugin?.createNotificationChannel(
        const AndroidNotificationChannel(
          _channelId,
          _channelName,
          description: _channelDesc,
          importance: Importance.high,
        ),
      );
      _initialized = true;
    } catch (_) {
      _initFailed = true;
    }
  }

  /// Request permission if needed. Returns whether we may post a notification.
  Future<bool> ensurePermission() async {
    if (kIsWeb) return false;
    await ensureInitialized();
    if (_initFailed) return false;
    try {
      if (defaultTargetPlatform == TargetPlatform.android) {
        // Android 13+ needs POST_NOTIFICATIONS; older versions are granted at install.
        final status = await Permission.notification.status;
        if (status.isGranted) return true;
        if (status.isPermanentlyDenied) return false;
        final req = await Permission.notification.request();
        return req.isGranted;
      }
      if (defaultTargetPlatform == TargetPlatform.iOS) {
        final ios = _plugin.resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>();
        final ok = await ios?.requestPermissions(
              alert: true,
              badge: true,
              sound: true,
            ) ??
            false;
        return ok;
      }
    } catch (_) {
      return false;
    }
    return _initialized;
  }

  /// Best-effort “can we notify?” without prompting (for loading UI copy).
  Future<bool> hasPermission() async {
    if (kIsWeb) return false;
    await ensureInitialized();
    if (_initFailed) return false;
    try {
      if (defaultTargetPlatform == TargetPlatform.android) {
        return (await Permission.notification.status).isGranted;
      }
      // iOS: after a prior grant; if never asked, treat as “will ask on search”.
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> notifySearchDone({
    required int storeCount,
    required int itemsRequested,
  }) async {
    if (kIsWeb) return;
    await ensureInitialized();
    if (!_initialized) return;
    final allowed = await ensurePermission();
    if (!allowed) return;

    final title = storeCount > 0 ? 'Busca concluída' : 'Busca finalizada';
    final body = storeCount > 0
        ? (storeCount == 1
            ? 'Encontramos 1 loja com preços da sua lista.'
            : 'Encontramos $storeCount lojas com preços da sua lista.')
        : 'Não encontramos lojas por perto para esses itens. Toque para ver detalhes.';

    const androidDetails = AndroidNotificationDetails(
      _channelId,
      _channelName,
      channelDescription: _channelDesc,
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    try {
      await _plugin.show(_notificationId, title, body, details);
    } catch (_) {
      // Ignore — UI already shows results when foreground.
    }
  }
}

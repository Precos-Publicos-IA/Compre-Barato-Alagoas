/// App-wide configuration.
class AppConfig {
  /// Backend base URL. Override at build/run time, e.g.:
  ///   flutter run --dart-define=API_BASE_URL=http://192.168.0.10:8000
  /// Defaults to the production domain.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://alagoas.precospublicos.ia.br',
  );

  /// Public download URL for the Android APK (shown to web users).
  static const String androidApkUrl =
      '$apiBaseUrl/app/compre-barato-alagoas.apk';

  /// Base URL of the public web app (same origin as the API).
  static const String webBaseUrl = apiBaseUrl;

  /// Domain used for Android App Links verification (no scheme).
  static const String appLinkHost = 'alagoas.precospublicos.ia.br';

  /// Path prefix for shareable search links: `/abrir/<uuid>`. Scoped so it
  /// doesn't hijack the whole domain for the installed app (App Links).
  static const String shareLinkPath = '/abrir';
}

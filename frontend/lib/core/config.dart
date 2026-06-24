import 'web_user_agent_stub.dart'
    if (dart.library.html) 'web_user_agent_web.dart' as web_ua;

/// App-wide configuration.
class AppConfig {
  /// Backend base URL. Override at build/run time, e.g.:
  ///   flutter run --dart-define=API_BASE_URL=http://192.168.0.10:8000
  /// Defaults to the production domain.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://alagoas.precospublicos.ia.br',
  );

  /// Public download URL for the Android APK (shown to non-iOS web users).
  static const String androidApkUrl =
      '$apiBaseUrl/app/compre-barato-alagoas.apk';

  /// Base URL of the public web app (same origin as the API).
  static const String webBaseUrl = apiBaseUrl;

  /// Domain used for Android App Links verification (no scheme).
  /// iOS Universal Links (AASA) should use the same host when the ios/ target lands.
  static const String appLinkHost = 'alagoas.precospublicos.ia.br';

  /// Path prefix for shareable search links: `/abrir/<uuid>`. Scoped so it
  /// doesn't hijack the whole domain for the installed app (App Links).
  static const String shareLinkPath = '/abrir';

  /// Privacy policy / terms version recorded with each LGPD consent. Bump in
  /// lockstep with the backend `POLICY_VERSION` when the policy text changes.
  static const String policyVersion = '2026-06-06';

  /// App semver / build for support screenshots (#404 / #411); set at CI build.
  static const String appVersion = String.fromEnvironment(
    'APP_VERSION',
    defaultValue: '0.1.0',
  );
  static const String appBuild = String.fromEnvironment(
    'APP_BUILD',
    defaultValue: '1',
  );

  static String get supportVersionLine {
    final host = Uri.tryParse(apiBaseUrl)?.host ?? apiBaseUrl;
    return 'App $appVersion ($appBuild) · API $host · política $policyVersion';
  }

  /// Browser user-agent on web builds (`null` on VM/native). Used to tailor the
  /// install banner (APK vs iOS "Add to Home Screen"). Overridable in tests via
  /// [setWebUserAgentForTest].
  static String? _webUserAgentOverride;

  static String? get webUserAgent =>
      _webUserAgentOverride ?? web_ua.readBrowserUserAgent();

  /// Test-only: force the UA string seen by install/PWA helpers.
  static void setWebUserAgentForTest(String? value) {
    _webUserAgentOverride = value;
  }
}

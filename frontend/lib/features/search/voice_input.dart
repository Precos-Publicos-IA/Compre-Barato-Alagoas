import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';

/// Picks the best speech locale for this app (Brazilian Portuguese first).
///
/// On iPhone, `pt_BR` speech assets are not always installed; falling back to
/// `pt_PT` or the device default avoids a hard failure with only a mic error
/// (issue #18). Pure function so unit tests don't need the speech plugin.
String? resolveSpeechLocaleId(
  List<LocaleName> locales, {
  String preferred = 'pt_BR',
  List<String> fallbacks = const ['pt_PT', 'pt'],
}) {
  if (locales.isEmpty) return preferred;
  String norm(String id) => id.replaceAll('-', '_').toLowerCase();
  final byNorm = {for (final l in locales) norm(l.localeId): l.localeId};

  String? matchExactOrPrefix(String want) {
    final w = norm(want);
    if (byNorm.containsKey(w)) return byNorm[w];
    for (final e in byNorm.entries) {
      if (e.key.startsWith('${w}_') || e.key.startsWith(w)) return e.value;
    }
    // Prefix on preferred lang only (e.g. want "pt" matches "pt_br").
    if (w.length == 2) {
      for (final e in byNorm.entries) {
        if (e.key.startsWith('${w}_')) return e.value;
      }
    }
    return null;
  }

  final hit = matchExactOrPrefix(preferred);
  if (hit != null) return hit;
  for (final fb in fallbacks) {
    final h = matchExactOrPrefix(fb);
    if (h != null) return h;
  }
  return locales.first.localeId;
}

/// Wraps speech_to_text + microphone permission with a tiny, testable surface.
///
/// On **web / iPhone Safari**, `permission_handler` is unreliable or a no-op;
/// the browser grants mic access when the Web Speech / getUserMedia path runs
/// inside `speech_to_text.initialize()` / `listen()`. We skip the pre-check
/// there and let the speech engine surface the real prompt (or failure).
///
/// On **native** Android/iOS builds we still request via `permission_handler`
/// before initializing, so the OS permission dialog appears first.
class VoiceInput {
  VoiceInput({
    SpeechToText? speech,
    /// Injected for tests; defaults to real `Permission.microphone.request`.
    Future<PermissionStatus> Function()? requestMicrophone,
    /// Injected for tests; defaults to real `Permission.microphone.status`.
    Future<PermissionStatus> Function()? checkMicrophone,
    /// Override web detection in tests (defaults to [kIsWeb]).
    bool? isWeb,
  })  : _speech = speech ?? SpeechToText(),
        _requestMicrophone =
            requestMicrophone ?? (() => Permission.microphone.request()),
        _checkMicrophone = checkMicrophone,
        _isWeb = isWeb ?? kIsWeb;

  final SpeechToText _speech;
  final Future<PermissionStatus> Function() _requestMicrophone;
  final Future<PermissionStatus> Function()? _checkMicrophone;
  final bool _isWeb;
  bool _available = false;
  String? _localeId;

  /// Last mic permission outcome on native (after [ensureReady]); null on web
  /// or before the first pre-check. Used for denied-forever / Settings UX (#356).
  PermissionStatus? lastMicStatus;

  bool get isListening => _speech.isListening;

  /// Last resolved locale (after [ensureReady]); useful for diagnostics/tests.
  String? get localeId => _localeId;

  /// Whether the microphone permission pre-check runs (false on web).
  bool get usesPermissionHandlerPrecheck => !_isWeb;

  /// True when the OS will not show the permission dialog again until the user
  /// changes it in system Settings (#356).
  bool get micNeedsSystemSettings {
    final s = lastMicStatus;
    if (s == null) return false;
    return s.isPermanentlyDenied || s.isRestricted;
  }

  Future<bool> ensureReady() async {
    if (!_isWeb) {
      // Prefer an explicit check first so permanentlyDenied is accurate even
      // when request() no-ops after "Don't ask again".
      final check = _checkMicrophone ?? (() => Permission.microphone.status);
      PermissionStatus status = await check();
      if (!status.isGranted &&
          !status.isPermanentlyDenied &&
          !status.isRestricted) {
        status = await _requestMicrophone();
      }
      lastMicStatus = status;
      if (!status.isGranted) return false;
    }
    if (!_available) {
      _available = await _speech.initialize();
      if (_available) {
        try {
          final locales = await _speech.locales();
          _localeId = resolveSpeechLocaleId(locales);
        } catch (_) {
          _localeId = 'pt_BR';
        }
      }
    }
    return _available;
  }

  /// Starts listening; [onResult] receives the (possibly partial) transcript.
  Future<bool> start({
    required void Function(String text, bool isFinal) onResult,
  }) async {
    if (!await ensureReady()) return false;
    await _speech.listen(
      onResult: (r) => onResult(r.recognizedWords, r.finalResult),
      listenOptions: SpeechListenOptions(
        partialResults: true,
        localeId: _localeId ?? 'pt_BR',
      ),
    );
    return true;
  }

  Future<void> stop() => _speech.stop();
}

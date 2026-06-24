import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';

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
    /// Override web detection in tests (defaults to [kIsWeb]).
    bool? isWeb,
  })  : _speech = speech ?? SpeechToText(),
        _requestMicrophone =
            requestMicrophone ?? (() => Permission.microphone.request()),
        _isWeb = isWeb ?? kIsWeb;

  final SpeechToText _speech;
  final Future<PermissionStatus> Function() _requestMicrophone;
  final bool _isWeb;
  bool _available = false;

  bool get isListening => _speech.isListening;

  /// Whether the microphone permission pre-check runs (false on web).
  bool get usesPermissionHandlerPrecheck => !_isWeb;

  Future<bool> ensureReady() async {
    if (!_isWeb) {
      final status = await _requestMicrophone();
      if (!status.isGranted) return false;
    }
    if (!_available) {
      _available = await _speech.initialize();
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
      listenOptions:
          SpeechListenOptions(partialResults: true, localeId: 'pt_BR'),
    );
    return true;
  }

  Future<void> stop() => _speech.stop();
}

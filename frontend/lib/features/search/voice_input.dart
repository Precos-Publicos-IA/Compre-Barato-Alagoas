import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';

/// Wraps speech_to_text + microphone permission with a tiny, testable surface.
class VoiceInput {
  VoiceInput({SpeechToText? speech}) : _speech = speech ?? SpeechToText();

  final SpeechToText _speech;
  bool _available = false;

  bool get isListening => _speech.isListening;

  Future<bool> ensureReady() async {
    final status = await Permission.microphone.request();
    if (!status.isGranted) return false;
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

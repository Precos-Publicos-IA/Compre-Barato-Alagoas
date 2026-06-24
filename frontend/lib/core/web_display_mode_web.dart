// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

/// True when already running as installed PWA / iOS A2HS (#391).
///
/// Checks `display-mode: standalone|fullscreen|minimal-ui` and iOS
/// `navigator.standalone`.
bool isStandaloneDisplayMode() {
  try {
    final nav = html.window.navigator;
    // iOS Safari A2HS sets standalone on the Navigator (non-standard).
    final standalone = nav.standalone;
    if (standalone == true) return true;
    final m = html.window.matchMedia;
    for (final mode in ['standalone', 'fullscreen', 'minimal-ui']) {
      if (m('(display-mode: $mode)').matches) return true;
    }
  } catch (_) {
    // Older browsers without matchMedia — treat as normal tab.
  }
  return false;
}

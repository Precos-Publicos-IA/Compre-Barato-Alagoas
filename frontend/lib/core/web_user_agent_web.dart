// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

/// Web: real navigator.userAgent for install-banner branching.
String? readBrowserUserAgent() => html.window.navigator.userAgent;

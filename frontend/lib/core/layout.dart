import 'package:flutter/material.dart';

/// Shared viewport helpers for phone-landscape density and large-desktop chrome.
///
/// PhoneLandscape matrix cells use CSS height ~360–440. Without compaction the
/// staple chips and store cards fall under the fold (V-CLIP-TEXT).
/// Desktop4k (QHD/4K) needs a capped content column so the home/admin chrome
/// is not a postage-stamp on an empty canvas (V-FORM-FACTOR).
class AppLayout {
  AppLayout._();

  /// Short CSS height — PhoneLandscape class (and thin chrome browsers).
  static bool isShortHeight(BuildContext context) =>
      MediaQuery.sizeOf(context).height < 480;

  /// Slightly less aggressive than [isShortHeight]; used for padding tweaks.
  static bool isCompactHeight(BuildContext context) =>
      MediaQuery.sizeOf(context).height < 560;

  /// Landscape orientation (width > height).
  static bool isLandscape(BuildContext context) {
    final s = MediaQuery.sizeOf(context);
    return s.width > s.height;
  }

  /// Phone-class width (portrait phones + narrow landscape).
  static bool isPhoneWidth(BuildContext context) =>
      MediaQuery.sizeOf(context).width < 600;

  /// Dense phone landscape: short height AND landscape.
  static bool isPhoneLandscape(BuildContext context) =>
      isLandscape(context) && isCompactHeight(context);

  /// Desktop4k class: QHD / 4K CSS widths.
  static bool isDesktop4k(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= 2400;

  /// Comfortable max width for the product column.
  ///
  /// On QHD/4K we take a generous fraction of the viewport so chrome is not a
  /// postage stamp in an empty field (V-FORM-FACTOR), while still capping so
  /// lines stay readable.
  static double contentMaxWidth(BuildContext context) {
    final w = MediaQuery.sizeOf(context).width;
    // Generous column: ~half the viewport on ultrawide, hard-capped so line
    // lengths stay readable and chrome does not become a postage stamp.
    if (w >= 3200) return (w * 0.48).clamp(1400.0, 1920.0); // 4K
    if (w >= 2400) return (w * 0.52).clamp(1180.0, 1560.0); // QHD
    if (w >= 1600) return 920;
    if (w >= 1100) return 760;
    return double.infinity;
  }

  /// Horizontal page padding: tighter on short height, roomier on desktop.
  static double pagePadding(BuildContext context) {
    if (isShortHeight(context)) return 10;
    if (isDesktop4k(context)) return 28;
    return 16;
  }

  /// Primary CTA min height — theme default is too tall on PhoneLandscape.
  static double ctaMinHeight(BuildContext context) {
    if (isShortHeight(context)) return 48;
    if (isCompactHeight(context)) return 52;
    return 56;
  }

  /// App bar height.
  static double toolbarHeight(BuildContext context) {
    if (isShortHeight(context)) return 48;
    return 56;
  }

  /// Staple tile min height for portrait grid.
  static double stapleTileHeight(BuildContext context) {
    if (isShortHeight(context)) return 40;
    return 72;
  }

  /// Center a child inside [contentMaxWidth] for wide desktops.
  ///
  /// [expand] (default true): fill the parent's max height — correct for
  /// Scaffold **body** so scroll views get a bounded viewport.
  ///
  /// Set [expand] false for **bottomNavigationBar** / intrinsic-height bars.
  /// An expanding [Align] there grows to the full scaffold height, paints a
  /// full-screen white Material over the body, and pins the CTA near the top
  /// (y≈30) — blank QHD/4K stills and broken Desktop4k chrome.
  static Widget constrainContent({
    required BuildContext context,
    required Widget child,
    bool expand = true,
  }) {
    final maxW = contentMaxWidth(context);
    if (maxW == double.infinity) return child;
    return Align(
      alignment: Alignment.topCenter,
      // heightFactor: 1.0 → shrink-wrap to child height (bottom bars).
      // null → expand to parent max height (body / scroll viewport).
      heightFactor: expand ? null : 1.0,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxW),
        child: child,
      ),
    );
  }
}

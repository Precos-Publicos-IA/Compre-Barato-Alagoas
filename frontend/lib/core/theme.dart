import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Brand tokens — custom palette for a local grocery-savings product.
/// Not a bare ColorScheme.fromSeed Material starter.
class AppColors {
  AppColors._();

  /// Deep forest green — trustworthy, "economia".
  static const primary = Color(0xFF0B6B3A);
  static const primaryDark = Color(0xFF074D2A);
  static const primaryMid = Color(0xFF158F4E);
  static const primarySoft = Color(0xFFD8F0E2);
  static const primaryContainer = Color(0xFFE6F6EC);

  /// Soft sage canvas (warmer than pure grey).
  static const canvas = Color(0xFFF2F5F1);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceMuted = Color(0xFFEAEFE8);

  /// Ink hierarchy.
  static const ink = Color(0xFF132019);
  static const inkSecondary = Color(0xFF3D4F44);
  static const inkMuted = Color(0xFF6B7C72);
  static const outline = Color(0xFFC9D4CC);

  /// Gold accent for "winner / savings".
  static const accent = Color(0xFFE0A21A);
  static const accentSoft = Color(0xFFFFF4D6);

  static const danger = Color(0xFFC0392B);
  static const dangerSoft = Color(0xFFFDECEA);

  static const shadow = Color(0x1A132019);
}

class AppRadii {
  AppRadii._();
  static const xs = 8.0;
  static const sm = 12.0;
  static const md = 16.0;
  static const lg = 20.0;
  static const xl = 28.0;
  static const pill = 999.0;
}

class AppSpacing {
  AppSpacing._();
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 20.0;
  static const xxl = 28.0;
}

/// Soft product elevation (not default M3 card).
List<BoxShadow> appCardShadow({double elevation = 1}) {
  if (elevation <= 0) return const [];
  return [
    BoxShadow(
      color: AppColors.shadow,
      blurRadius: 10 * elevation,
      offset: Offset(0, 3 * elevation),
    ),
  ];
}

/// High-contrast, large-touch-target theme with a real brand palette.
ThemeData buildAppTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: AppColors.primary,
    onPrimary: Colors.white,
    primaryContainer: AppColors.primaryContainer,
    onPrimaryContainer: AppColors.primaryDark,
    secondary: AppColors.primaryMid,
    onSecondary: Colors.white,
    secondaryContainer: AppColors.primarySoft,
    onSecondaryContainer: AppColors.primaryDark,
    tertiary: AppColors.accent,
    onTertiary: AppColors.ink,
    tertiaryContainer: AppColors.accentSoft,
    onTertiaryContainer: Color(0xFF5C4200),
    error: AppColors.danger,
    onError: Colors.white,
    errorContainer: AppColors.dangerSoft,
    onErrorContainer: AppColors.danger,
    surface: AppColors.surface,
    onSurface: AppColors.ink,
    onSurfaceVariant: AppColors.inkSecondary,
    outline: AppColors.outline,
    outlineVariant: Color(0xFFDCE5DE),
    shadow: AppColors.ink,
    scrim: Colors.black54,
    inverseSurface: AppColors.ink,
    onInverseSurface: AppColors.canvas,
    inversePrimary: AppColors.primarySoft,
    surfaceTint: AppColors.primary,
  );

  const textTheme = TextTheme(
    displaySmall: TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.w800,
      letterSpacing: -0.6,
      height: 1.15,
      color: AppColors.ink,
    ),
    headlineMedium: TextStyle(
      fontSize: 26,
      fontWeight: FontWeight.w800,
      letterSpacing: -0.4,
      height: 1.2,
      color: AppColors.ink,
    ),
    headlineSmall: TextStyle(
      fontSize: 22,
      fontWeight: FontWeight.w800,
      letterSpacing: -0.3,
      height: 1.25,
      color: AppColors.ink,
    ),
    titleLarge: TextStyle(
      fontSize: 18,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.2,
      height: 1.3,
      color: AppColors.ink,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w700,
      height: 1.3,
      color: AppColors.ink,
    ),
    titleSmall: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w700,
      height: 1.3,
      color: AppColors.inkSecondary,
    ),
    bodyLarge: TextStyle(
      fontSize: 17,
      fontWeight: FontWeight.w400,
      height: 1.4,
      color: AppColors.ink,
    ),
    bodyMedium: TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w400,
      height: 1.4,
      color: AppColors.inkSecondary,
    ),
    bodySmall: TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w400,
      height: 1.35,
      color: AppColors.inkMuted,
    ),
    labelLarge: TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.2,
      color: AppColors.ink,
    ),
    labelMedium: TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: AppColors.inkSecondary,
    ),
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.canvas,
    textTheme: textTheme,
    primaryTextTheme: textTheme,
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0.5,
      centerTitle: true,
      backgroundColor: AppColors.canvas,
      foregroundColor: AppColors.ink,
      surfaceTintColor: Colors.transparent,
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
      ),
      titleTextStyle: TextStyle(
        fontSize: 17,
        fontWeight: FontWeight.w700,
        color: AppColors.ink,
        letterSpacing: -0.2,
      ),
      iconTheme: IconThemeData(color: AppColors.inkSecondary, size: 24),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        disabledBackgroundColor: AppColors.outline,
        disabledForegroundColor: AppColors.inkMuted,
        minimumSize: const Size.fromHeight(56),
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        textStyle: const TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        minimumSize: const Size(48, 48),
        side: const BorderSide(color: AppColors.outline, width: 1.4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      hintStyle: const TextStyle(
        color: AppColors.inkMuted,
        fontSize: 16,
        fontWeight: FontWeight.w400,
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadii.md),
        borderSide: const BorderSide(color: AppColors.outline, width: 1.2),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadii.md),
        borderSide: const BorderSide(color: AppColors.outline, width: 1.2),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadii.md),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadii.md),
        side: const BorderSide(color: AppColors.outline, width: 1),
      ),
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: AppColors.surface,
      selectedColor: AppColors.primarySoft,
      disabledColor: AppColors.surfaceMuted,
      labelStyle: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.ink,
      ),
      secondaryLabelStyle: const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.inkSecondary,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadii.sm),
        side: const BorderSide(color: AppColors.outline),
      ),
      side: const BorderSide(color: AppColors.outline),
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.outline,
      thickness: 1,
      space: 1,
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadii.lg)),
      ),
      showDragHandle: true,
      dragHandleColor: AppColors.outline,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: AppColors.ink,
      contentTextStyle: const TextStyle(color: Colors.white, fontSize: 15),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadii.sm),
      ),
      insetPadding: const EdgeInsets.fromLTRB(12, 0, 12, 16),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: AppColors.primary,
      circularTrackColor: AppColors.primarySoft,
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.primary,
      foregroundColor: Colors.white,
      elevation: 2,
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(
        minimumSize: const Size(48, 48),
        foregroundColor: AppColors.inkSecondary,
      ),
    ),
    listTileTheme: const ListTileThemeData(
      iconColor: AppColors.inkSecondary,
      textColor: AppColors.ink,
      contentPadding: EdgeInsets.symmetric(horizontal: 12),
    ),
  );
}

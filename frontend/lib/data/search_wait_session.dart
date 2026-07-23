import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/results/search_wait_copy.dart';

/// Metadata for the in-flight (or last) search wait experience.
class SearchWaitSession {
  const SearchWaitSession({
    required this.startedAt,
    required this.itemCount,
    required this.etaMinutes,
    this.notifyPromise = true,
  });

  final DateTime startedAt;
  final int itemCount;
  final int etaMinutes;

  /// Whether the UI should promise a system notification (permission willing).
  final bool notifyPromise;

  factory SearchWaitSession.start(int itemCount, {bool notifyPromise = true}) {
    return SearchWaitSession(
      startedAt: DateTime.now(),
      itemCount: itemCount,
      etaMinutes: estimateSearchEtaMinutes(itemCount),
      notifyPromise: notifyPromise,
    );
  }
}

class SearchWaitSessionNotifier extends Notifier<SearchWaitSession?> {
  @override
  SearchWaitSession? build() => null;

  void begin(int itemCount, {bool notifyPromise = true}) {
    state = SearchWaitSession.start(itemCount, notifyPromise: notifyPromise);
  }

  void clear() => state = null;
}

final searchWaitSessionProvider =
    NotifierProvider<SearchWaitSessionNotifier, SearchWaitSession?>(
  SearchWaitSessionNotifier.new,
);

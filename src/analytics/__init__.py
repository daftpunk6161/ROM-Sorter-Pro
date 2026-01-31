"""Collection Analytics Module - F91-F93 + F66 Implementation.

Provides:
- F91: Sammlungs-Dashboard (Collection statistics)
- F92: Wunschlisten-Manager (Wishlist tracking)
- F93: Timeline-View (ROMs by release year)
- F66: Collection-Completeness-Tracker
"""

from .collection_dashboard import CollectionDashboard, CollectionStats, SystemStats
from .wishlist_manager import WishlistManager, WishlistItem, WishlistExport
from .timeline_view import TimelineView, TimelineEntry, TimelinePeriod
from .completeness_tracker import CompletenessTracker, SystemCompleteness, CompletenessReport

__all__ = [
    # F91
    "CollectionDashboard",
    "CollectionStats",
    "SystemStats",
    # F92
    "WishlistManager",
    "WishlistItem",
    "WishlistExport",
    # F93
    "TimelineView",
    "TimelineEntry",
    "TimelinePeriod",
    # F66
    "CompletenessTracker",
    "SystemCompleteness",
    "CompletenessReport",
]

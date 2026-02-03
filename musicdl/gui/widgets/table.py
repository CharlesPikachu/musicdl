# Custom Table Widgets
"""
Custom table widget items with enhanced sorting.
"""

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


class SortableTableWidgetItem(QTableWidgetItem):
    """
    Table widget item with proper sorting support.
    
    Uses UserRole data for numerical sorting when available.
    """
    
    def __lt__(self, other: 'QTableWidgetItem') -> bool:
        """Compare items for sorting."""
        my_value = self.data(Qt.ItemDataRole.UserRole)
        other_value = other.data(Qt.ItemDataRole.UserRole)
        
        if my_value is not None and other_value is not None:
            try:
                return my_value < other_value
            except TypeError:
                pass  # Fallback to default
        
        return super().__lt__(other)

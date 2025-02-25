"""
Layout Helper Utilities

This module provides utilities to handle layout issues that may arise
from language differences, particularly when text might be longer or
shorter in different languages.
"""

from typing import Dict, List, Tuple, Optional, Union
from PyQt6.QtCore import QLocale, QSize, Qt
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLayout, QFormLayout,
    QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy
)

from scout.translations.config import (
    LANGUAGE_EXPANSION_FACTORS,
    MIN_WIDTHS,
    DEFAULT_PADDING,
    DEFAULT_FONT,
    DEFAULT_SPACING,
)


def get_current_language_code() -> str:
    """
    Get the current language code based on the application locale.
    
    Returns:
        A two-letter language code (e.g., 'en', 'de')
    """
    locale = QLocale()
    language_code = locale.name().split('_')[0]
    return language_code


def get_expansion_factor(language_code: Optional[str] = None) -> float:
    """
    Get the expansion factor for a given language compared to English.
    
    Args:
        language_code: Two-letter language code (e.g., 'en', 'de'). 
                       If None, uses the current application language.
    
    Returns:
        Expansion factor as a float. 1.0 for English, higher for languages with
        longer text (e.g., German), lower for languages with shorter text (e.g., Chinese).
    """
    if language_code is None:
        language_code = get_current_language_code()
    
    return LANGUAGE_EXPANSION_FACTORS.get(language_code, 1.0)


def calculate_min_width_for_text(
    text: str, 
    font: Optional[QFont] = None, 
    language_code: Optional[str] = None,
    padding: int = DEFAULT_PADDING
) -> int:
    """
    Calculate the minimum width needed to display text based on language.
    
    This function takes into account the expansion factor of the language
    to ensure the width is appropriate for the current language.
    
    Args:
        text: The text to measure
        font: The font to use for measurement. If None, uses DEFAULT_FONT.
        language_code: Two-letter language code. If None, uses current language.
        padding: Additional padding to add to the calculated width.
    
    Returns:
        Minimum width in pixels
    """
    if font is None:
        font = QFont(DEFAULT_FONT[0], DEFAULT_FONT[1])
    
    # Measure the text
    font_metrics = QFontMetrics(font)
    text_width = font_metrics.horizontalAdvance(text)
    
    # Apply language expansion factor
    expansion_factor = get_expansion_factor(language_code)
    adjusted_width = int(text_width * expansion_factor) + padding
    
    return adjusted_width


def set_min_width_for_text(
    widget: QWidget, 
    text: str, 
    font: Optional[QFont] = None,
    language_code: Optional[str] = None,
    padding: int = DEFAULT_PADDING
) -> None:
    """
    Set the minimum width of a widget based on the text it contains.
    
    Args:
        widget: The widget to set the minimum width for
        text: The text to base the width on
        font: The font to use for measurement. If None, uses widget's font or DEFAULT_FONT.
        language_code: Two-letter language code. If None, uses current language.
        padding: Additional padding to add to the calculated width.
    """
    if font is None:
        font = widget.font() if hasattr(widget, 'font') else QFont(DEFAULT_FONT[0], DEFAULT_FONT[1])
    
    min_width = calculate_min_width_for_text(text, font, language_code, padding)
    widget.setMinimumWidth(min_width)


def set_fixed_width_for_text(
    widget: QWidget, 
    text: str, 
    font: Optional[QFont] = None,
    language_code: Optional[str] = None,
    padding: int = DEFAULT_PADDING
) -> None:
    """
    Set the fixed width of a widget based on the text it contains.
    
    Args:
        widget: The widget to set the fixed width for
        text: The text to base the width on
        font: The font to use for measurement. If None, uses widget's font or DEFAULT_FONT.
        language_code: Two-letter language code. If None, uses current language.
        padding: Additional padding to add to the calculated width.
    """
    if font is None:
        font = widget.font() if hasattr(widget, 'font') else QFont(DEFAULT_FONT[0], DEFAULT_FONT[1])
    
    width = calculate_min_width_for_text(text, font, language_code, padding)
    widget.setFixedWidth(width)


def adjust_button_sizes(
    buttons: List[QPushButton], 
    use_fixed_width: bool = False,
    language_code: Optional[str] = None
) -> None:
    """
    Adjust a group of buttons to have consistent sizes based on their text content.
    
    Args:
        buttons: List of buttons to adjust
        use_fixed_width: If True, sets a fixed width; if False, sets a minimum width
        language_code: Two-letter language code. If None, uses current language.
    """
    if not buttons:
        return
    
    # Find the longest text
    max_width = MIN_WIDTHS['button']
    
    for button in buttons:
        text = button.text()
        if text:
            width = calculate_min_width_for_text(text, button.font(), language_code)
            max_width = max(max_width, width)
    
    # Apply the width to all buttons
    for button in buttons:
        if use_fixed_width:
            button.setFixedWidth(max_width)
        else:
            button.setMinimumWidth(max_width)


def create_expanding_layout(
    widgets: List[QWidget], 
    stretch_indices: Optional[List[int]] = None,
    horizontal: bool = True
) -> Union[QHBoxLayout, QVBoxLayout]:
    """
    Create a layout where some widgets expand to fill available space.
    
    Args:
        widgets: List of widgets to add to the layout
        stretch_indices: Indices of widgets that should stretch to fill space.
                         If None, the last widget will stretch.
        horizontal: If True, creates a horizontal layout; otherwise, vertical.
    
    Returns:
        A QHBoxLayout or QVBoxLayout with the widgets added and properly configured.
    """
    layout = QHBoxLayout() if horizontal else QVBoxLayout()
    layout.setSpacing(DEFAULT_SPACING['horizontal' if horizontal else 'vertical'])
    layout.setContentsMargins(0, 0, 0, 0)
    
    if stretch_indices is None and widgets:
        stretch_indices = [len(widgets) - 1]
    
    for i, widget in enumerate(widgets):
        stretch = 1 if stretch_indices and i in stretch_indices else 0
        layout.addWidget(widget, stretch)
    
    return layout


def create_form_layout(
    label_widget_pairs: List[Tuple[QWidget, QWidget]],
    fixed_label_width: Optional[int] = None
) -> QFormLayout:
    """
    Create a form layout with consistent label widths.
    
    Args:
        label_widget_pairs: List of (label, field) widget pairs
        fixed_label_width: If provided, all labels will have this fixed width
    
    Returns:
        A QFormLayout with the widgets added
    """
    layout = QFormLayout()
    layout.setSpacing(DEFAULT_SPACING['form'])
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Find the widest label if fixed_label_width is not provided
    if fixed_label_width is None and label_widget_pairs:
        max_width = 0
        for label, _ in label_widget_pairs:
            if isinstance(label, QLabel):
                width = calculate_min_width_for_text(label.text(), label.font())
                max_width = max(max_width, width)
        
        fixed_label_width = max_width if max_width > 0 else None
    
    # Add widgets to the layout
    for label, widget in label_widget_pairs:
        if fixed_label_width is not None and isinstance(label, QLabel):
            label.setFixedWidth(fixed_label_width)
        
        layout.addRow(label, widget)
    
    return layout


def create_responsive_grid_layout(
    widgets: List[QWidget], 
    column_count: int = 2,
    equal_width_columns: bool = False
) -> QGridLayout:
    """
    Create a responsive grid layout for the given widgets.
    
    Args:
        widgets: List of widgets to arrange in a grid
        column_count: Number of columns in the grid
        equal_width_columns: If True, columns will have equal width
    
    Returns:
        A QGridLayout with the widgets arranged in a grid
    """
    layout = QGridLayout()
    layout.setSpacing(DEFAULT_SPACING['grid'])
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Add widgets to the grid
    for i, widget in enumerate(widgets):
        row = i // column_count
        col = i % column_count
        layout.addWidget(widget, row, col)
        
        if equal_width_columns:
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, widget.sizePolicy().verticalPolicy())
    
    return layout


# Example usage:
"""
# Button example
button = QPushButton("My Button")
set_min_width_for_text(button, button.text())

# Group of buttons with consistent widths
buttons = [QPushButton("OK"), QPushButton("Cancel"), QPushButton("Apply")]
adjust_button_sizes(buttons)

# Form layout with consistent label widths
name_label = QLabel("Name:")
name_field = QLineEdit()
age_label = QLabel("Age:")
age_field = QLineEdit()

form_layout = create_form_layout([
    (name_label, name_field),
    (age_label, age_field)
])

# Expanding layout (e.g., for a search box with a button)
search_field = QLineEdit()
search_button = QPushButton("Search")

search_layout = create_expanding_layout([search_field, search_button], [0])
""" 
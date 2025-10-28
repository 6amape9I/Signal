"""
Signal - A simple signal processing library for Python.

This library provides basic signal generation and processing capabilities.
"""

__version__ = "0.1.0"

from .core import Signal
from .generators import sine_wave, square_wave, sawtooth_wave
from .processors import apply_filter, compute_fft

__all__ = [
    "Signal",
    "sine_wave",
    "square_wave",
    "sawtooth_wave",
    "apply_filter",
    "compute_fft",
]

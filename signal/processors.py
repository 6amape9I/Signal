"""Signal processing utilities."""

import numpy as np
from .core import Signal


def apply_filter(signal, cutoff_frequency, filter_type="lowpass"):
    """
    Apply a simple filter to a signal.
    
    This is a basic implementation using a moving average for lowpass
    or simple difference for highpass filtering.
    
    Args:
        signal (Signal): The input signal.
        cutoff_frequency (float): Cutoff frequency in Hz.
        filter_type (str): Type of filter ('lowpass' or 'highpass'). Default is 'lowpass'.
    
    Returns:
        Signal: The filtered signal.
    """
    # Calculate window size based on cutoff frequency
    window_size = max(1, int(signal.sample_rate / (2 * cutoff_frequency)))
    
    if filter_type == "lowpass":
        # Simple moving average filter
        kernel = np.ones(window_size) / window_size
        filtered_data = np.convolve(signal.data, kernel, mode='same')
    elif filter_type == "highpass":
        # Simple difference-based highpass
        lowpass_kernel = np.ones(window_size) / window_size
        lowpass_data = np.convolve(signal.data, lowpass_kernel, mode='same')
        filtered_data = signal.data - lowpass_data
    else:
        raise ValueError(f"Unknown filter type: {filter_type}")
    
    return Signal(filtered_data, signal.sample_rate)


def compute_fft(signal):
    """
    Compute the Fast Fourier Transform (FFT) of a signal.
    
    Args:
        signal (Signal): The input signal.
    
    Returns:
        tuple: A tuple containing:
            - frequencies (np.ndarray): Frequency bins in Hz.
            - magnitude (np.ndarray): Magnitude spectrum.
    """
    # Compute FFT
    fft_result = np.fft.fft(signal.data)
    
    # Compute magnitude spectrum
    magnitude = np.abs(fft_result)
    
    # Compute frequency bins
    frequencies = np.fft.fftfreq(len(signal.data), 1.0 / signal.sample_rate)
    
    # Return only positive frequencies
    positive_freq_idx = frequencies >= 0
    frequencies = frequencies[positive_freq_idx]
    magnitude = magnitude[positive_freq_idx]
    
    return frequencies, magnitude

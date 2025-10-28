"""Signal generation utilities."""

import numpy as np
from .core import Signal


def sine_wave(frequency, duration, sample_rate=44100, amplitude=1.0, phase=0):
    """
    Generate a sine wave signal.
    
    Args:
        frequency (float): Frequency in Hz.
        duration (float): Duration in seconds.
        sample_rate (float): Sampling rate in Hz. Default is 44100.
        amplitude (float): Amplitude of the wave. Default is 1.0.
        phase (float): Phase offset in radians. Default is 0.
    
    Returns:
        Signal: A Signal object containing the sine wave.
    """
    num_samples = int(duration * sample_rate)
    t = np.arange(num_samples) / sample_rate
    data = amplitude * np.sin(2 * np.pi * frequency * t + phase)
    return Signal(data, sample_rate)


def square_wave(frequency, duration, sample_rate=44100, amplitude=1.0, duty_cycle=0.5):
    """
    Generate a square wave signal.
    
    Args:
        frequency (float): Frequency in Hz.
        duration (float): Duration in seconds.
        sample_rate (float): Sampling rate in Hz. Default is 44100.
        amplitude (float): Amplitude of the wave. Default is 1.0.
        duty_cycle (float): Duty cycle (0 to 1). Default is 0.5.
    
    Returns:
        Signal: A Signal object containing the square wave.
    """
    num_samples = int(duration * sample_rate)
    t = np.arange(num_samples) / sample_rate
    phase = (frequency * t) % 1.0
    data = amplitude * (phase < duty_cycle).astype(float)
    # Center around zero
    data = 2 * data - amplitude
    return Signal(data, sample_rate)


def sawtooth_wave(frequency, duration, sample_rate=44100, amplitude=1.0):
    """
    Generate a sawtooth wave signal.
    
    Args:
        frequency (float): Frequency in Hz.
        duration (float): Duration in seconds.
        sample_rate (float): Sampling rate in Hz. Default is 44100.
        amplitude (float): Amplitude of the wave. Default is 1.0.
    
    Returns:
        Signal: A Signal object containing the sawtooth wave.
    """
    num_samples = int(duration * sample_rate)
    t = np.arange(num_samples) / sample_rate
    phase = (frequency * t) % 1.0
    data = amplitude * (2 * phase - 1)
    return Signal(data, sample_rate)

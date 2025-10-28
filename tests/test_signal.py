"""Tests for the signal package."""

import unittest
import numpy as np
import sys
import os

# Add parent directory to path to import signal module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal import Signal, sine_wave, square_wave, sawtooth_wave, apply_filter, compute_fft


class TestSignal(unittest.TestCase):
    """Test cases for the Signal class."""
    
    def test_signal_creation(self):
        """Test Signal object creation."""
        data = [1, 2, 3, 4, 5]
        signal = Signal(data, sample_rate=100)
        self.assertEqual(len(signal), 5)
        self.assertEqual(signal.sample_rate, 100)
        np.testing.assert_array_equal(signal.data, np.array(data, dtype=np.float64))
    
    def test_signal_duration(self):
        """Test signal duration calculation."""
        data = np.zeros(1000)
        signal = Signal(data, sample_rate=100)
        self.assertEqual(signal.duration, 10.0)
    
    def test_signal_time_axis(self):
        """Test time axis generation."""
        data = np.zeros(100)
        signal = Signal(data, sample_rate=10)
        expected_time = np.arange(100) / 10
        np.testing.assert_array_almost_equal(signal.time_axis, expected_time)
    
    def test_signal_addition(self):
        """Test adding two signals."""
        signal1 = Signal([1, 2, 3], sample_rate=10)
        signal2 = Signal([4, 5, 6], sample_rate=10)
        result = signal1 + signal2
        np.testing.assert_array_equal(result.data, np.array([5, 7, 9]))
    
    def test_signal_scalar_addition(self):
        """Test adding a scalar to a signal."""
        signal = Signal([1, 2, 3], sample_rate=10)
        result = signal + 10
        np.testing.assert_array_equal(result.data, np.array([11, 12, 13]))
    
    def test_signal_multiplication(self):
        """Test multiplying a signal by a scalar."""
        signal = Signal([1, 2, 3], sample_rate=10)
        result = signal * 2
        np.testing.assert_array_equal(result.data, np.array([2, 4, 6]))
        result2 = 3 * signal
        np.testing.assert_array_equal(result2.data, np.array([3, 6, 9]))


class TestGenerators(unittest.TestCase):
    """Test cases for signal generators."""
    
    def test_sine_wave_length(self):
        """Test sine wave generates correct number of samples."""
        signal = sine_wave(frequency=440, duration=1.0, sample_rate=1000)
        self.assertEqual(len(signal), 1000)
    
    def test_sine_wave_frequency(self):
        """Test sine wave generates correct frequency."""
        signal = sine_wave(frequency=10, duration=1.0, sample_rate=1000)
        frequencies, magnitude = compute_fft(signal)
        peak_idx = magnitude.argmax()
        peak_freq = frequencies[peak_idx]
        self.assertAlmostEqual(peak_freq, 10.0, places=0)
    
    def test_square_wave_length(self):
        """Test square wave generates correct number of samples."""
        signal = square_wave(frequency=100, duration=0.5, sample_rate=1000)
        self.assertEqual(len(signal), 500)
    
    def test_sawtooth_wave_length(self):
        """Test sawtooth wave generates correct number of samples."""
        signal = sawtooth_wave(frequency=50, duration=2.0, sample_rate=1000)
        self.assertEqual(len(signal), 2000)


class TestProcessors(unittest.TestCase):
    """Test cases for signal processors."""
    
    def test_lowpass_filter(self):
        """Test lowpass filter."""
        # Create a signal with low and high frequency components
        low_freq = sine_wave(frequency=10, duration=1.0, sample_rate=1000, amplitude=1.0)
        high_freq = sine_wave(frequency=200, duration=1.0, sample_rate=1000, amplitude=0.5)
        combined = low_freq + high_freq
        
        # Apply lowpass filter
        filtered = apply_filter(combined, cutoff_frequency=50, filter_type="lowpass")
        
        # Filtered signal should have similar length
        self.assertEqual(len(filtered), len(combined))
    
    def test_highpass_filter(self):
        """Test highpass filter."""
        signal = sine_wave(frequency=100, duration=1.0, sample_rate=1000)
        filtered = apply_filter(signal, cutoff_frequency=50, filter_type="highpass")
        self.assertEqual(len(filtered), len(signal))
    
    def test_compute_fft(self):
        """Test FFT computation."""
        signal = sine_wave(frequency=100, duration=1.0, sample_rate=1000)
        frequencies, magnitude = compute_fft(signal)
        
        # Check that we get positive frequencies only
        self.assertTrue(np.all(frequencies >= 0))
        
        # Check that the peak is near the expected frequency
        peak_idx = magnitude.argmax()
        peak_freq = frequencies[peak_idx]
        self.assertAlmostEqual(peak_freq, 100.0, places=0)


if __name__ == "__main__":
    unittest.main()

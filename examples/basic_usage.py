"""
Example usage of the Signal library.

This script demonstrates basic signal generation and processing.
"""

import sys
import os

# Add parent directory to path to import signal module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal import sine_wave, square_wave, sawtooth_wave, apply_filter, compute_fft


def main():
    """Demonstrate signal generation and processing."""
    print("Signal Processing Sandbox - Examples")
    print("=" * 50)
    
    # Example 1: Generate a sine wave
    print("\n1. Generating a 440 Hz sine wave (1 second)...")
    signal = sine_wave(frequency=440, duration=1.0, sample_rate=44100)
    print(f"   {signal}")
    
    # Example 2: Generate a square wave
    print("\n2. Generating a 100 Hz square wave (0.5 seconds)...")
    square = square_wave(frequency=100, duration=0.5, sample_rate=44100)
    print(f"   {square}")
    
    # Example 3: Generate a sawtooth wave
    print("\n3. Generating a 220 Hz sawtooth wave (0.5 seconds)...")
    sawtooth = sawtooth_wave(frequency=220, duration=0.5, sample_rate=44100)
    print(f"   {sawtooth}")
    
    # Example 4: Add two signals
    print("\n4. Adding two sine waves (440 Hz + 880 Hz)...")
    signal1 = sine_wave(frequency=440, duration=1.0, sample_rate=44100, amplitude=0.5)
    signal2 = sine_wave(frequency=880, duration=1.0, sample_rate=44100, amplitude=0.5)
    combined = signal1 + signal2
    print(f"   {combined}")
    
    # Example 5: Apply a lowpass filter
    print("\n5. Applying lowpass filter (cutoff: 1000 Hz)...")
    noisy_signal = sine_wave(frequency=440, duration=1.0, sample_rate=44100)
    noise = sine_wave(frequency=5000, duration=1.0, sample_rate=44100, amplitude=0.2)
    noisy = noisy_signal + noise
    filtered = apply_filter(noisy, cutoff_frequency=1000, filter_type="lowpass")
    print(f"   Original: {noisy}")
    print(f"   Filtered: {filtered}")
    
    # Example 6: Compute FFT
    print("\n6. Computing FFT of 440 Hz sine wave...")
    test_signal = sine_wave(frequency=440, duration=0.1, sample_rate=44100)
    frequencies, magnitude = compute_fft(test_signal)
    # Find the peak frequency
    peak_idx = magnitude.argmax()
    peak_freq = frequencies[peak_idx]
    print(f"   Peak frequency found: {peak_freq:.2f} Hz")
    
    print("\n" + "=" * 50)
    print("Examples completed successfully!")


if __name__ == "__main__":
    main()

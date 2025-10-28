# Signal

A simple signal processing library for Python that provides basic signal generation and processing capabilities.

## Features

- **Signal Generation**: Generate common waveforms including sine, square, and sawtooth waves
- **Signal Processing**: Apply filters (lowpass/highpass) and compute FFT
- **Signal Manipulation**: Add signals together and perform scalar operations
- **Easy to Use**: Simple, intuitive API for quick prototyping

## Installation

### From Source

```bash
pip install numpy
python setup.py install
```

### Development Mode

```bash
pip install -e .
```

## Quick Start

```python
from signal import sine_wave, square_wave, apply_filter, compute_fft

# Generate a 440 Hz sine wave
signal = sine_wave(frequency=440, duration=1.0, sample_rate=44100)

# Generate a square wave
square = square_wave(frequency=100, duration=0.5, sample_rate=44100)

# Add two signals
combined = signal + square

# Apply a lowpass filter
filtered = apply_filter(combined, cutoff_frequency=1000, filter_type="lowpass")

# Compute FFT
frequencies, magnitude = compute_fft(signal)
```

## Examples

See the `examples/` directory for more detailed usage examples:

```bash
python examples/basic_usage.py
```

## Testing

Run the test suite:

```bash
python -m unittest discover tests
```

## API Reference

### Signal Class

The core `Signal` class represents a discrete-time signal:

```python
from signal import Signal

# Create a signal from data
signal = Signal(data=[1, 2, 3, 4, 5], sample_rate=1000)

# Properties
print(signal.duration)      # Duration in seconds
print(signal.time_axis)     # Time axis array
print(len(signal))          # Number of samples

# Operations
signal2 = signal * 2        # Multiply by scalar
signal3 = signal + signal2  # Add signals
```

### Signal Generators

Generate common waveforms:

```python
from signal import sine_wave, square_wave, sawtooth_wave

# Sine wave
sine = sine_wave(frequency=440, duration=1.0, sample_rate=44100, amplitude=1.0, phase=0)

# Square wave
square = square_wave(frequency=100, duration=1.0, sample_rate=44100, amplitude=1.0, duty_cycle=0.5)

# Sawtooth wave
sawtooth = sawtooth_wave(frequency=220, duration=1.0, sample_rate=44100, amplitude=1.0)
```

### Signal Processors

Process signals with filters and FFT:

```python
from signal import apply_filter, compute_fft

# Apply lowpass or highpass filter
filtered = apply_filter(signal, cutoff_frequency=1000, filter_type="lowpass")

# Compute FFT
frequencies, magnitude = compute_fft(signal)
```

## Requirements

- Python >= 3.7
- NumPy >= 1.19.0

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
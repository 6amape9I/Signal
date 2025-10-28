"""Core signal data structure and operations."""

import numpy as np


class Signal:
    """
    A class representing a discrete-time signal.
    
    Attributes:
        data (np.ndarray): The signal values.
        sample_rate (float): The sampling rate in Hz.
    """
    
    def __init__(self, data, sample_rate=1.0):
        """
        Initialize a Signal object.
        
        Args:
            data (array-like): The signal values.
            sample_rate (float): The sampling rate in Hz. Default is 1.0.
        """
        self.data = np.asarray(data, dtype=np.float64)
        self.sample_rate = float(sample_rate)
    
    @property
    def duration(self):
        """Get the duration of the signal in seconds."""
        return len(self.data) / self.sample_rate
    
    @property
    def time_axis(self):
        """Get the time axis for the signal."""
        return np.arange(len(self.data)) / self.sample_rate
    
    def __len__(self):
        """Return the number of samples in the signal."""
        return len(self.data)
    
    def __repr__(self):
        """Return a string representation of the Signal."""
        return f"Signal(samples={len(self.data)}, sample_rate={self.sample_rate}, duration={self.duration:.3f}s)"
    
    def __add__(self, other):
        """Add two signals or add a scalar to a signal."""
        if isinstance(other, Signal):
            if self.sample_rate != other.sample_rate:
                raise ValueError("Cannot add signals with different sample rates")
            # Pad the shorter signal with zeros
            max_len = max(len(self.data), len(other.data))
            data1 = np.pad(self.data, (0, max_len - len(self.data)))
            data2 = np.pad(other.data, (0, max_len - len(other.data)))
            return Signal(data1 + data2, self.sample_rate)
        else:
            return Signal(self.data + other, self.sample_rate)
    
    def __mul__(self, scalar):
        """Multiply the signal by a scalar."""
        return Signal(self.data * scalar, self.sample_rate)
    
    def __rmul__(self, scalar):
        """Right multiplication (scalar * signal)."""
        return self.__mul__(scalar)

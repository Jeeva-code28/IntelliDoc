import numpy as np
from typing import Tuple


def quantize_binary(vector: np.ndarray) -> np.ndarray:
    """
    Quantizes 384-dimensional float32 vector into 384 bits = 48 bytes (packed uint8).
    Converts positive dimensions (>0.0) to 1, and negative/zero (<=0.0) to 0.
    Achieves 8x storage reduction (1536 bytes -> 48 bytes).
    """
    vec = vector.ravel()
    bits = (vec > 0.0).astype(np.uint8)
    return np.packbits(bits)


def dequantize_binary(packed_uint8: np.ndarray, dim: int = 384) -> np.ndarray:
    """Unpacks 48-byte uint8 array back to 384-dimensional float32 vector (+1.0 / -1.0)."""
    unpacked_bits = np.unpackbits(packed_uint8)[:dim]
    return np.where(unpacked_bits == 1, 1.0, -1.0).astype(np.float32)


def binary_hamming_similarity(query_packed: np.ndarray, target_packed: np.ndarray) -> float:
    """Calculates normalized cosine similarity approximation from binary packed vectors using bitwise XOR."""
    xor_bytes = np.bitwise_xor(query_packed, target_packed)
    hamming_distance = int(np.unpackbits(xor_bytes).sum())
    total_bits = query_packed.shape[0] * 8
    return 1.0 - (2.0 * hamming_distance / total_bits)

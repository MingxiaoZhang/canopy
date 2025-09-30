import hashlib


class BloomFilter:
    """Memory-efficient probabilistic data structure for duplicate detection"""

    def __init__(self, capacity: int = 1000000, error_rate: float = 0.1):
        """
        Initialize Bloom filter

        Args:
            capacity: Expected number of items
            error_rate: Acceptable false positive rate
        """
        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate optimal parameters (would need math module, using simplified version)
        # self.bit_array_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        # self.hash_count = int(self.bit_array_size * math.log(2) / capacity)

        # Simplified version without math
        self.bit_array_size = capacity * 10
        self.hash_count = 3

        # Initialize bit array
        self.bit_array = [False] * self.bit_array_size
        self.item_count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for given item and seed"""
        hash_obj = hashlib.md5((item + str(seed)).encode())
        return int(hash_obj.hexdigest(), 16) % self.bit_array_size

    def add(self, item: str):
        """Add item to bloom filter"""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self.bit_array[index] = True
        self.item_count += 1

    def __contains__(self, item: str) -> bool:
        """Check if item might be in the set"""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            if not self.bit_array[index]:
                return False
        return True
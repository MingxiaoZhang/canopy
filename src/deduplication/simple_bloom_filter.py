class SimpleBloomFilter:
    """Simplified bloom filter implementation"""

    def __init__(self, capacity: int = 100000):
        self.capacity = capacity
        self.bit_array = [False] * (capacity * 10)  # 10x size for lower collision rate
        self.item_count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Simple hash function"""
        hash_value = hash(item + str(seed))
        return abs(hash_value) % len(self.bit_array)

    def add(self, item: str):
        """Add item to bloom filter"""
        for seed in range(3):  # Use 3 different hash functions
            index = self._hash(item, seed)
            self.bit_array[index] = True
        self.item_count += 1

    def __contains__(self, item: str) -> bool:
        """Check if item might be in the set"""
        for seed in range(3):
            index = self._hash(item, seed)
            if not self.bit_array[index]:
                return False
        return True
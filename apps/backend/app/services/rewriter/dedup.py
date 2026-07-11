import re
import random

# A large prime number for hashing computations (larger than 2^32 - 1)
PRIME_P = 4294967311


class MinHashLSH:
    def __init__(self, num_perm: int = 64, num_bands: int = 16, threshold: float = 0.5):
        """
        MinHash LSH for near-duplicate text detection.
        num_perm: number of permutations (hashes) for signature.
        num_bands: number of bands B. num_perm must be divisible by num_bands.
        threshold: Jaccard similarity threshold above which texts are near-duplicates.
        """
        assert num_perm % num_bands == 0, "num_perm must be divisible by num_bands"
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands
        self.threshold = threshold

        # Generate deterministic coefficients for hash functions using fixed seed
        random.seed(1337)
        self.hash_coef_a = [random.randint(1, PRIME_P - 1) for _ in range(self.num_perm)]
        self.hash_coef_b = [random.randint(0, PRIME_P - 1) for _ in range(self.num_perm)]

        # LSH Hash Tables: band_idx -> bucket_hash -> list of doc_ids
        self.bands = [{} for _ in range(self.num_bands)]
        
        # Keep track of added documents: doc_id -> (text, shingle_set, signature)
        self.docs = {}

    def _get_shingles(self, text: str) -> set:
        """Tokenize text into word-level 2-grams (shingles)."""
        # Lowercase and split on words
        words = [w.strip() for w in re.split(r"\W+", text.lower()) if w.strip()]
        shingles = set()
        for i in range(len(words) - 1):
            shingle = f"{words[i]} {words[i+1]}"
            shingles.add(shingle)
        return shingles

    def _compute_signature(self, shingles: set) -> list:
        """Compute the MinHash signature of a set of shingles."""
        signature = [PRIME_P] * self.num_perm
        
        for shingle in shingles:
            # Hash the shingle to a 32-bit integer
            shingle_hash = hash(shingle) & 0xFFFFFFFF
            
            # Update signature values
            for i in range(self.num_perm):
                # Permutation hash: (a * x + b) % p
                h_val = (self.hash_coef_a[i] * shingle_hash + self.hash_coef_b[i]) % PRIME_P
                if h_val < signature[i]:
                    signature[i] = h_val
        return signature

    def add(self, doc_id: str, text: str):
        """Add a document to the index and map it to LSH bands."""
        shingles = self._get_shingles(text)
        signature = self._compute_signature(shingles)
        
        self.docs[doc_id] = (text, shingles, signature)
        
        # Map signature to LSH bands
        for b in range(self.num_bands):
            start_row = b * self.rows_per_band
            end_row = start_row + self.rows_per_band
            band_bytes = tuple(signature[start_row:end_row])
            band_hash = hash(band_bytes)
            
            if band_hash not in self.bands[b]:
                self.bands[b][band_hash] = []
            self.bands[b][band_hash].append(doc_id)

    def find_near_duplicates(self, text: str) -> list:
        """Find candidate duplicates sharing at least one band bucket, verified by Jaccard similarity."""
        shingles = self._get_shingles(text)
        if not shingles:
            return []
            
        signature = self._compute_signature(shingles)
        candidates = set()
        
        # Step 1: Query LSH buckets for candidate doc_ids
        for b in range(self.num_bands):
            start_row = b * self.rows_per_band
            end_row = start_row + self.rows_per_band
            band_bytes = tuple(signature[start_row:end_row])
            band_hash = hash(band_bytes)
            
            if band_hash in self.bands[b]:
                candidates.update(self.bands[b][band_hash])
                
        # Step 2: Verify exact Jaccard similarity for candidates
        results = []
        for cand_id in candidates:
            cand_text, cand_shingles, _ = self.docs[cand_id]
            if not cand_shingles:
                continue
                
            intersection = len(shingles.intersection(cand_shingles))
            union = len(shingles.union(cand_shingles))
            jaccard = intersection / union if union > 0 else 0.0
            
            if jaccard >= self.threshold:
                results.append((cand_id, jaccard))
                
        # Sort candidates by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def is_duplicate(self, text: str) -> bool:
        """Returns True if the text shares similarity >= threshold with any document in the index."""
        matches = self.find_near_duplicates(text)
        return len(matches) > 0

    def filter_unique(self, texts: list) -> list:
        """Given a list of texts, filters and returns only unique items, adding them to the index."""
        unique_texts = []
        for i, text in enumerate(texts):
            if not self.is_duplicate(text):
                doc_id = f"doc_{len(self.docs)}_{i}"
                self.add(doc_id, text)
                unique_texts.append(text)
        return unique_texts

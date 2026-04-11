import math
import random

def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(x**2 for x in v1))
    mag2 = math.sqrt(sum(x**2 for x in v2))
    if mag1 == 0 or mag2 == 0: return 0.0
    return dot_product / (mag1 * mag2)

def test_security():
    # 1. Enrolled vector (Owner)
    owner_vector = [random.uniform(-1, 1) for _ in range(128)]
    
    # 2. Random Stranger face
    stranger_vector = [random.uniform(-1, 1) for _ in range(128)]
    
    # Calculate similarity
    sim = cosine_similarity(owner_vector, stranger_vector)
    print(f"Similarity between Owner and Stranger: {sim:.4f}")
    
    threshold = 0.85
    if sim < threshold:
        print(f"✅ PASSED: Stranger correctly REJECTED ({sim:.4f} < {threshold})")
    else:
        print(f"❌ FAILED: Stranger was incorrectly ACCEPTED ({sim:.4f} >= {threshold})")
    
    # 3. Test Owner again
    # In a real system, there's always noise (even with the same face), 
    # but in our current simulation, we reuse the vector for the owner.
    sim_owner = cosine_similarity(owner_vector, owner_vector)
    print(f"Similarity for Owner: {sim_owner:.4f}")
    if sim_owner >= threshold:
        print(f"✅ PASSED: Owner correctly ACCEPTED")

if __name__ == "__main__":
    test_security()

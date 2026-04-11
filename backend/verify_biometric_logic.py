import math

def cosine_similarity(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(x**2 for x in v1))
    mag2 = math.sqrt(sum(x**2 for x in v2))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
        
    return dot_product / (mag1 * mag2)

def test():
    # Mock vectors
    v1 = [1, 0, 0, 0]
    # v2 such that similarity is ~0.73
    # cos(theta) = 0.73 -> theta = 43 degrees
    v2 = [0.73, 0.68, 0, 0] # mag = sqrt(0.73^2 + 0.68^2) = sqrt(0.53 + 0.46) = sqrt(0.99) ~= 1
    
    sim = cosine_similarity(v1, v2)
    print(f"Calculated Similarity: {sim:.4f}")
    
    threshold = 0.70
    if sim >= threshold:
        print(f"✅ PASSED: {sim:.4f} >= {threshold}")
    else:
        print(f"❌ FAILED: {sim:.4f} < {threshold}")

if __name__ == "__main__":
    test()

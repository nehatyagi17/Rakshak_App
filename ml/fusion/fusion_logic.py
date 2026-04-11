def use_fusion(voice_score: float, motion_score: float) -> str:
    """
    Combines voice and motion anomaly probabilities into a single holistic threat level.
    Runs strictly on-device.
    """
    combined = (voice_score * 0.6) + (motion_score * 0.4)
    if combined >= 0.75:
        return 'HIGH'
    elif combined >= 0.45:
        return 'MEDIUM'
    else:
        return 'LOW'

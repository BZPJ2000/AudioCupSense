import numpy as np


def find_closest_cup(lst, target, tolerance=50):
    """
    原始的简单匹配算法（保留用于向后兼容）
    """
    min_diff = float('inf')
    closest_cup = -1
    for i, freq in enumerate(lst):
        if freq == 0:
            continue
        diff = abs(freq - target)
        if diff < min_diff and diff <= tolerance:
            min_diff = diff
            closest_cup = i
    return closest_cup


def find_closest_cup_with_confidence(cup_frequencies, cup_stds, target_freq,
                                     base_tolerance=50, confidence_threshold=0.5):
    """
    改进的匹配算法，使用动态容差和置信度评分

    Args:
        cup_frequencies: 各杯子的学习频率列表
        cup_stds: 各杯子的频率标准差列表
        target_freq: 待匹配的目标频率
        base_tolerance: 基础容差（Hz）
        confidence_threshold: 最低置信度阈值

    Returns:
        dict: 包含杯子索引、置信度、频率差等信息
    """
    best_match = {
        'cup_index': -1,
        'confidence': 0.0,
        'frequency_diff': float('inf'),
        'match_score': 0.0
    }

    for i, freq in enumerate(cup_frequencies):
        if freq == 0:
            continue

        # 计算频率差
        freq_diff = abs(freq - target_freq)

        # 动态容差：根据该杯子的标准差调整
        std = cup_stds[i] if i < len(cup_stds) and cup_stds[i] > 0 else 20
        dynamic_tolerance = base_tolerance + 2 * std  # 2倍标准差范围

        # 如果超出动态容差，跳过
        if freq_diff > dynamic_tolerance:
            continue

        # 计算匹配得分（归一化到0-1）
        # 频率越接近，得分越高
        freq_score = 1 - (freq_diff / dynamic_tolerance)

        # 稳定性得分：标准差越小，得分越高
        stability_score = 1 / (1 + std / 50)  # 归一化

        # 综合得分（加权平均）
        match_score = 0.7 * freq_score + 0.3 * stability_score

        # 计算置信度（考虑与其他杯子的区分度）
        confidence = match_score

        # 更新最佳匹配
        if match_score > best_match['match_score']:
            best_match = {
                'cup_index': i,
                'confidence': confidence,
                'frequency_diff': freq_diff,
                'match_score': match_score
            }

    # 如果置信度低于阈值，返回未匹配
    if best_match['confidence'] < confidence_threshold:
        best_match['cup_index'] = -1

    return best_match
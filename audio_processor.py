"""
优化的音频信号处理模块
包含改进的频率提取、聚类和信号质量评估算法
"""
import numpy as np
from scipy import signal
from sklearn.cluster import DBSCAN


class AudioProcessor:
    """音频信号处理器，提供高精度频率提取和分析功能"""

    def __init__(self, sample_rate=12000, chunk_size=4096):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        # 创建汉明窗，减少频谱泄漏
        self.window = np.hamming(chunk_size)

    def extract_frequency_with_harmonics(self, audio_data):
        """
        改进的频率提取算法
        使用加窗FFT和抛物线插值提高精度

        Args:
            audio_data: 音频数据数组

        Returns:
            dict: 包含主频率、幅度、谐波信息
        """
        # 应用汉明窗
        windowed_data = audio_data * self.window

        # 执行FFT
        fft_result = np.fft.fft(windowed_data)
        fft_magnitude = np.abs(fft_result[:self.chunk_size // 2])

        # 找到峰值索引
        peak_idx = np.argmax(fft_magnitude)

        # 抛物线插值提高频率分辨率
        if 0 < peak_idx < len(fft_magnitude) - 1:
            # 使用三点抛物线插值
            alpha = fft_magnitude[peak_idx - 1]
            beta = fft_magnitude[peak_idx]
            gamma = fft_magnitude[peak_idx + 1]

            # 计算插值偏移
            p = 0.5 * (alpha - gamma) / (alpha - 2 * beta + gamma)
            interpolated_idx = peak_idx + p
        else:
            interpolated_idx = peak_idx

        # 计算精确频率
        fundamental_freq = interpolated_idx * self.sample_rate / self.chunk_size
        amplitude = fft_magnitude[peak_idx]

        # 提取谐波信息（2倍频、3倍频）
        harmonics = self._extract_harmonics(fft_magnitude, peak_idx, 3)

        return {
            'frequency': fundamental_freq,
            'amplitude': amplitude,
            'harmonics': harmonics,
            'fft_magnitude': fft_magnitude
        }

    def _extract_harmonics(self, fft_magnitude, fundamental_idx, num_harmonics=3):
        """
        提取谐波信息

        Args:
            fft_magnitude: FFT幅度谱
            fundamental_idx: 基频索引
            num_harmonics: 要提取的谐波数量

        Returns:
            list: 谐波幅度列表
        """
        harmonics = []
        for i in range(2, num_harmonics + 1):
            harmonic_idx = int(fundamental_idx * i)
            if harmonic_idx < len(fft_magnitude):
                harmonics.append(fft_magnitude[harmonic_idx])
            else:
                harmonics.append(0)
        return harmonics

    def calculate_snr(self, audio_data, signal_freq_range=(2500, 6000)):
        """
        计算信噪比（SNR）评估信号质量

        Args:
            audio_data: 音频数据数组
            signal_freq_range: 信号频率范围 (min_freq, max_freq)

        Returns:
            float: 信噪比（dB）
        """
        # 执行FFT
        fft_result = np.fft.fft(audio_data * self.window)
        fft_magnitude = np.abs(fft_result[:self.chunk_size // 2])

        # 计算频率轴
        freqs = np.fft.fftfreq(self.chunk_size, 1 / self.sample_rate)[:self.chunk_size // 2]

        # 信号频段
        signal_mask = (freqs >= signal_freq_range[0]) & (freqs <= signal_freq_range[1])
        signal_power = np.sum(fft_magnitude[signal_mask] ** 2)

        # 噪声频段（低频噪声）
        noise_mask = freqs < signal_freq_range[0]
        noise_power = np.sum(fft_magnitude[noise_mask] ** 2)

        # 避免除零
        if noise_power == 0:
            return float('inf')

        # 计算SNR（dB）
        snr = 10 * np.log10(signal_power / noise_power)
        return snr

    def cluster_frequencies_dbscan(self, frequencies, eps=30, min_samples=3):
        """
        使用DBSCAN算法对频率进行聚类
        自动识别频率簇并过滤离群点

        Args:
            frequencies: 频率列表
            eps: DBSCAN的邻域半径（Hz）
            min_samples: 形成簇的最小样本数

        Returns:
            dict: 包含主频率、标准差、簇大小等信息
        """
        if len(frequencies) < min_samples:
            return None

        # 转换为二维数组（DBSCAN要求）
        freq_array = np.array(frequencies).reshape(-1, 1)

        # 执行DBSCAN聚类
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(freq_array)
        labels = clustering.labels_

        # 找到最大的簇（排除噪声点，标签为-1）
        unique_labels = set(labels)
        if -1 in unique_labels:
            unique_labels.remove(-1)

        if not unique_labels:
            return None

        # 找到最大簇
        largest_cluster_label = max(unique_labels,
                                   key=lambda label: np.sum(labels == label))
        cluster_mask = labels == largest_cluster_label
        cluster_freqs = freq_array[cluster_mask].flatten()

        return {
            'mean_frequency': np.mean(cluster_freqs),
            'std_deviation': np.std(cluster_freqs),
            'cluster_size': len(cluster_freqs),
            'total_samples': len(frequencies),
            'cluster_ratio': len(cluster_freqs) / len(frequencies)
        }

    def analyze_frequency_stability(self, frequencies):
        """
        分析频率稳定性，计算变异系数

        Args:
            frequencies: 频率列表

        Returns:
            dict: 包含均值、标准差、变异系数
        """
        if not frequencies:
            return None

        freq_array = np.array(frequencies)
        mean_freq = np.mean(freq_array)
        std_freq = np.std(freq_array)

        # 变异系数（CV）= 标准差 / 均值
        cv = std_freq / mean_freq if mean_freq > 0 else float('inf')

        return {
            'mean': mean_freq,
            'std': std_freq,
            'cv': cv,
            'stability_score': 1 / (1 + cv)  # 稳定性评分，越接近1越稳定
        }

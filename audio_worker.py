import numpy as np
import pyaudio
from PyQt5.QtCore import QObject, pyqtSignal
from audio_processor import AudioProcessor

class AudioWorker(QObject):
    frequencyDetected = pyqtSignal(float)
    # 新增信号：发送频率和信号质量信息
    frequencyWithQuality = pyqtSignal(dict)

    def __init__(self):
        super(AudioWorker, self).__init__()
        self.CHUNK = 4096
        self.RATE = 12000
        self.CHUNK_2 = self.CHUNK // 2
        self.data_end = np.zeros(self.CHUNK_2)
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=self.RATE,
                                  input=True,
                                  frames_per_buffer=self.CHUNK_2)
        self.data2 = []

        # 初始化音频处理器
        self.audio_processor = AudioProcessor(sample_rate=self.RATE, chunk_size=self.CHUNK)

        # 信号质量阈值
        self.min_snr = 5.0  # 最小信噪比（dB）

        print("音频Worker初始化完成（已启用优化算法）")

    def process_audio(self):
        print("音频处理开始")
        try:
            while True:
                audio_chunk = self.stream.read(self.CHUNK_2, exception_on_overflow=False)
                audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_data = np.concatenate((audio_data, self.data_end), axis=None)

                # 使用优化的频率提取算法
                freq_info = self.audio_processor.extract_frequency_with_harmonics(
                    audio_data[:self.CHUNK])
                f_max = freq_info['frequency']
                amplitude = freq_info['amplitude']

                # 计算信噪比
                snr = self.audio_processor.calculate_snr(audio_data[:self.CHUNK])

                # 只处理高质量信号
                if f_max > 2500 and snr > self.min_snr:
                    self.data2.append(f_max)

                    if len(self.data2) > 25:
                        # 使用DBSCAN聚类算法
                        cluster_result = self.audio_processor.cluster_frequencies_dbscan(
                            self.data2, eps=30, min_samples=3)

                        if cluster_result:
                            f_max = cluster_result['mean_frequency']
                            quality_info = {
                                'frequency': f_max,
                                'snr': snr,
                                'cluster_size': cluster_result['cluster_size'],
                                'std': cluster_result['std_deviation']
                            }
                            self.frequencyWithQuality.emit(quality_info)
                            print(f"发送频率：{f_max:.1f} Hz, SNR: {snr:.1f} dB, "
                                  f"簇大小: {cluster_result['cluster_size']}")
                        else:
                            # 回退到原始算法
                            freq_mode = self.seekingMode(self.data2)
                            if freq_mode:
                                f_max = freq_mode[0]
                            quality_info = {'frequency': f_max, 'snr': snr}
                            self.frequencyWithQuality.emit(quality_info)

                        self.data2 = []
                        self.frequencyDetected.emit(f_max)
                    else:
                        self.frequencyDetected.emit(f_max)
        except KeyboardInterrupt:
            print("用户终止程序。")
        except Exception as e:
            print(f"发生错误：{e}")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
            print("音频流已关闭。")

    def seekingMode(self, numList):
        if not numList:
            return []
        uniqueList = list(set(numList))
        frequencyDict = {num: numList.count(num) for num in uniqueList}
        sortedDict = sorted(frequencyDict.items(), key=lambda item: item[1], reverse=True)
        maxFrequency = sortedDict[0][1]
        keys = [key for key, value in frequencyDict.items() if value == maxFrequency]
        keys.sort()
        return keys
import numpy as np
import pyaudio
from PyQt5.QtCore import QObject, pyqtSignal

class AudioWorker(QObject):
    frequencyDetected = pyqtSignal(float)

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
        print("音频Worker初始化完成")

    def process_audio(self):
        print("音频处理开始")
        try:
            while True:
                audio_chunk = self.stream.read(self.CHUNK_2, exception_on_overflow=False)
                audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_data = np.concatenate((audio_data, self.data_end), axis=None)

                sound_fft = np.fft.fft(audio_data[:self.CHUNK])
                f_max = np.argmax(np.abs(sound_fft)[:self.CHUNK_2]) * self.RATE / self.CHUNK

                if f_max > 2500:
                    self.data2.append(f_max)

                    if len(self.data2) > 25:
                        freq_mode = self.seekingMode(self.data2)
                        if freq_mode:
                            f_max = freq_mode[0]
                        self.data2 = []
                        self.frequencyDetected.emit(f_max)
                        print(f"发送频率：{f_max}")
                    else:
                        self.frequencyDetected.emit(f_max)
                        print(f"发送频率：{f_max}")
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
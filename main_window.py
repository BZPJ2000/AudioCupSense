from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox
from PyQt5.QtCore import QTimer, QThread
from audio_worker import AudioWorker
from utils import find_closest_cup, find_closest_cup_with_confidence
from audio_processor import AudioProcessor

class AudioControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.location = [0.0] * 8  # 确保列表元素为浮点数
        self.location_stds = [0.0] * 8  # 存储各杯子的频率标准差
        self.current_mode = "idle"
        self.frequencies = []
        self.audio_processor = AudioProcessor()  # 音频处理器实例

    def initUI(self):
        self.setWindowTitle("音频控制面板")
        self.resize(1412, 751)

        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)

        controlGroupBox = QGroupBox("控制按键")
        controlLayout = QVBoxLayout(controlGroupBox)

        self.startButton = QPushButton("启动")
        self.startButton.setMinimumHeight(50)
        self.startButton.clicked.connect(self.startAudioAnalysis)

        self.detectButton = QPushButton("检测")
        self.detectButton.setMinimumHeight(50)
        self.detectButton.clicked.connect(self.detectAudio)

        self.testFrequencyButton = QPushButton("测试频率")
        self.testFrequencyButton.setMinimumHeight(50)
        self.testFrequencyButton.clicked.connect(self.testFrequency)

        controlLayout.addWidget(self.startButton)
        controlLayout.addWidget(self.detectButton)
        controlLayout.addWidget(self.testFrequencyButton)
        mainLayout.addWidget(controlGroupBox)

        resultGroupBox = QGroupBox("检测结果显示")
        resultLayout = QVBoxLayout(resultGroupBox)

        # 杯子编号显示
        cupLayout = QHBoxLayout()
        self.resultLabel = QLabel()
        self.resultLabel.setFont(QtGui.QFont("Arial", 36, QtGui.QFont.Bold))
        self.resultLabel.setStyleSheet("color: rgb(255, 0, 0);")
        self.resultLabel.setText("")

        cupLabel = QLabel("号杯子")
        cupLabel.setFont(QtGui.QFont("Arial", 36))

        cupLayout.addWidget(self.resultLabel, 0, QtCore.Qt.AlignHCenter)
        cupLayout.addWidget(cupLabel)
        resultLayout.addLayout(cupLayout)

        # 置信度显示
        self.confidenceLabel = QLabel()
        self.confidenceLabel.setFont(QtGui.QFont("Arial", 18))
        self.confidenceLabel.setStyleSheet("color: rgb(100, 255, 100);")
        self.confidenceLabel.setText("")
        resultLayout.addWidget(self.confidenceLabel, 0, QtCore.Qt.AlignHCenter)

        mainLayout.addWidget(resultGroupBox)

        learningGroupBox = QGroupBox("杯子学习按键")
        learningLayout = QHBoxLayout(learningGroupBox)

        self.cupButtons = {}
        for i in range(1, 9):
            button = QPushButton(f"{i}号杯子")
            button.setMinimumHeight(80)
            button.clicked.connect(lambda _, cup=i: self.learnCup(cup))
            self.cupButtons[f"cup_{i}"] = button
            learningLayout.addWidget(button)
        mainLayout.addWidget(learningGroupBox)

        self.audio_worker = AudioWorker()
        self.audio_thread = QThread()
        self.audio_worker.moveToThread(self.audio_thread)
        self.audio_worker.frequencyDetected.connect(self.updateResultLabel)
        # 连接新的质量信号
        self.audio_worker.frequencyWithQuality.connect(self.updateResultWithQuality)
        self.audio_thread.started.connect(self.audio_worker.process_audio)
        self.audio_thread.start()

        self.setStyleSheet(self.getStyleSheet())

    def getStyleSheet(self):
        return """
        QWidget {
            background-color: #000000;
        }
        QGroupBox {
            color: rgb(255, 255, 255);
            font: 18pt "Agency FB";
            border: 2px solid rgb(255, 255, 255);
        }
        QLabel {
            color: rgb(255, 255, 255);
            font: 18pt "Agency FB";
        }
        QPushButton {
            background-color: rgb(85, 255, 255);
            font: 18pt "Agency FB";
        }
        QPushButton:hover {
            background-color: rgb(100, 255, 200);
        }
        QPushButton:pressed {
            background-color: rgb(50, 200, 200);
        }
        """

    def startAudioAnalysis(self):
        self.resultLabel.setText("启动中...")
        QtCore.QTimer.singleShot(1000, lambda: self.resultLabel.setText("已启动"))

    def detectAudio(self):
        self.current_mode = "detection"
        self.resultLabel.setText("检测中...")

    def testFrequency(self):
        self.resultLabel.setText("测试中...")
        QtCore.QTimer.singleShot(1500, lambda: self.resultLabel.setText("测试完成"))

    def learnCup(self, cup_number):
        self.current_mode = f"learning_{cup_number}"
        self.resultLabel.setText(f"{cup_number}号杯子学习中...")
        self.frequencies = []
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.finishLearning(cup_number))
        self.timer.start(2000)  # 2秒学习时间

    def updateResultWithQuality(self, quality_info):
        """处理带质量信息的频率数据"""
        frequency = quality_info.get('frequency', 0)
        print(f"收到频率（带质量）：{frequency:.1f} Hz")

        if self.current_mode.startswith("learning_"):
            self.frequencies.append(frequency)
        elif self.current_mode == "detection":
            # 使用优化的匹配算法
            match_result = find_closest_cup_with_confidence(
                self.location, self.location_stds, frequency,
                base_tolerance=50, confidence_threshold=0.5)

            if match_result['cup_index'] != -1:
                cup_num = match_result['cup_index'] + 1
                confidence = match_result['confidence'] * 100
                self.resultLabel.setText(f"{cup_num}")
                self.confidenceLabel.setText(
                    f"置信度: {confidence:.1f}% | 频差: {match_result['frequency_diff']:.1f} Hz")
            else:
                self.resultLabel.setText("?")
                self.confidenceLabel.setText("未找到匹配杯子")

    def updateResultLabel(self, frequency):
        """处理简单频率数据（向后兼容）"""
        print(f"收到频率：{frequency}")
        if self.current_mode.startswith("learning_"):
            self.frequencies.append(frequency)
        elif self.current_mode == "detection":
            closest_cup = find_closest_cup(self.location, frequency)
            if closest_cup != -1:
                self.resultLabel.setText(f"{closest_cup + 1}")
                self.confidenceLabel.setText("")
            else:
                self.resultLabel.setText("?")
                self.confidenceLabel.setText("未找到匹配杯子")

    def finishLearning(self, cup_number):
        self.timer.stop()
        if self.frequencies:
            # 使用DBSCAN聚类算法
            cluster_result = self.audio_processor.cluster_frequencies_dbscan(
                self.frequencies, eps=30, min_samples=3)

            if cluster_result:
                # 使用聚类结果
                learned_freq = cluster_result['mean_frequency']
                learned_std = cluster_result['std_deviation']
                self.location[cup_number - 1] = learned_freq
                self.location_stds[cup_number - 1] = learned_std
                print(f"学习完成，{cup_number}号杯子频率：{learned_freq:.1f} Hz, "
                      f"标准差：{learned_std:.1f} Hz")
                print(f"位置数组：{self.location}")
                self.resultLabel.setText(f"{cup_number}")
                self.confidenceLabel.setText(
                    f"学习完成 | 频率: {learned_freq:.1f} Hz | 稳定性: {learned_std:.1f} Hz")
            else:
                # 回退到原始算法
                freq_mode = self.seekingMode(self.frequencies)
                if freq_mode:
                    self.location[cup_number - 1] = freq_mode[0]
                    self.location_stds[cup_number - 1] = 20.0  # 默认标准差
                    print(f"学习完成（回退算法），{cup_number}号杯子频率：{freq_mode[0]}")
                self.resultLabel.setText(f"{cup_number}号杯子学习完成")
                self.confidenceLabel.setText("")
        self.current_mode = "idle"
        self.frequencies = []

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
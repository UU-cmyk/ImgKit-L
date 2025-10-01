import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFileDialog, QListWidget, QListWidgetItem, QSlider, QMessageBox, QCheckBox, QComboBox)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

class ImageCompressor:
    def __init__(self):
        pass

    def compress_image(self, image_path, quality=75, output_format="jpg", max_size=None):
        """压缩图像"""
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            return None, None
        
        # 如果指定了最大尺寸，调整图像大小
        if max_size:
            height, width = image.shape[:2]
            max_dim = max(height, width)
            if max_dim > max_size:
                scale = max_size / max_dim
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # 计算压缩参数
        if output_format.lower() in ["jpg", "jpeg"]:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        elif output_format.lower() == "webp":
            encode_param = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
        elif output_format.lower() == "png":
            # PNG压缩级别 (0-9) 对应0-100%质量
            png_quality = min(9, max(0, int((100 - quality) / 10)))
            encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), png_quality]
        else:
            encode_param = []
        
        # 压缩图像
        success, compressed_image = cv2.imencode(f".{output_format}", image, encode_param)
        
        if not success:
            return None, None
        
        return compressed_image.tobytes(), output_format

    def save_compressed_image(self, compressed_data, output_format, output_dir, base_name):
        """保存压缩后的图像"""
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成唯一文件名
        output_path = os.path.join(output_dir, f"{base_name}_compressed.{output_format}")
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(output_dir, f"{base_name}_compressed_{counter}.{output_format}")
            counter += 1
        
        # 保存文件
        with open(output_path, "wb") as f:
            f.write(compressed_data)
        
        return output_path

class ImageCompressionController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageYZ-图像压缩工具")
        self.setGeometry(100, 100, 800, 600)
        self.compressor = ImageCompressor()
        self.image_paths = []
        self.output_dir = ""
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # 顶部按钮布局
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("添加图片")
        self.add_button.clicked.connect(self.add_images)
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)
        self.output_button = QPushButton("选择输出目录")
        self.output_button.clicked.connect(self.select_output_dir)
        self.process_button = QPushButton("开始压缩")
        self.process_button.clicked.connect(self.process_images)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.output_button)
        button_layout.addWidget(self.process_button)
        main_layout.addLayout(button_layout)

        # 参数设置
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("质量:"))
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(75)
        param_layout.addWidget(self.quality_slider)
        self.quality_label = QLabel("75")
        self.quality_slider.valueChanged.connect(lambda: self.quality_label.setText(str(self.quality_slider.value())))
        param_layout.addWidget(self.quality_label)
        
        param_layout.addWidget(QLabel("最大尺寸:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(100, 4000)
        self.size_slider.setValue(2000)
        param_layout.addWidget(self.size_slider)
        self.size_label = QLabel("2000")
        self.size_slider.valueChanged.connect(lambda: self.size_label.setText(str(self.size_slider.value())))
        param_layout.addWidget(self.size_label)
        
        param_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPG", "PNG", "WEBP"])
        param_layout.addWidget(self.format_combo)
        
        main_layout.addLayout(param_layout)

        # 图片列表和预览
        content_layout = QHBoxLayout()
        self.image_list = QListWidget()
        self.image_list.itemSelectionChanged.connect(self.preview_image)
        content_layout.addWidget(self.image_list, 1)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setText("图片预览")
        content_layout.addWidget(self.preview_label, 1)

        main_layout.addLayout(content_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.dds)"
        )
        if not files:
            return

        for file in files:
            item = QListWidgetItem(os.path.basename(file))
            item.setData(Qt.UserRole, file)
            self.image_list.addItem(item)
            self.image_paths.append(file)

    def clear_list(self):
        self.image_list.clear()
        self.image_paths = []
        self.preview_label.setText("图片预览")

    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir = directory
            QMessageBox.information(self, "输出目录", f"已选择: {directory}")

    def preview_image(self):
        current_item = self.image_list.currentItem()
        if not current_item:
            return

        image_path = current_item.data(Qt.UserRole)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview_label.setText("无法加载图片")
            return

        # 调整预览大小
        scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled_pixmap)

    def process_images(self):
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先添加图片")
            return
            
        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return

        quality = self.quality_slider.value()
        max_size = self.size_slider.value()
        output_format = self.format_combo.currentText().lower()
        
        for path in self.image_paths:
            base_name = os.path.splitext(os.path.basename(path))[0]
            compressed_data, format_used = self.compressor.compress_image(
                path, quality, output_format, max_size
            )
            
            if compressed_data is None:
                QMessageBox.warning(self, "错误", f"无法压缩图片: {os.path.basename(path)}")
                continue
                
            output_path = self.compressor.save_compressed_image(
                compressed_data, format_used, self.output_dir, base_name
            )
            
        QMessageBox.information(self, "完成", f"已压缩 {len(self.image_paths)} 张图片")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = ImageCompressionController()
    window.show()
    sys.exit(app.exec_())

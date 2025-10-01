import os
import cv2
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                            QFileDialog, QListWidget, QLabel, QSlider, QGroupBox,
                            QHBoxLayout, QComboBox, QGridLayout, QSizePolicy, QProgressBar,
                            QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont

class FlipWorker(QThread):
    """用于后台处理图像的线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    
    def __init__(self, flipper, file_list, flip_type, angle):
        super().__init__()
        self.flipper = flipper
        self.file_list = file_list
        self.flip_type = flip_type
        self.angle = angle
        
    def run(self):
        results = []
        for i, file_path in enumerate(self.file_list):
            result = self.flipper.flip_image(file_path, self.flip_type, self.angle)
            results.append(result)
            self.progress.emit(i + 1)
        self.finished.emit(results)

class ImageFlipper:
    """核心图像翻转处理器"""
    def __init__(self):
        self.output_dir = ""
        self.preview_image = None
        
    def set_output_dir(self, path):
        self.output_dir = path
        
    def flip_image(self, input_path, flip_type, angle=0):
        """执行图像翻转/旋转"""
        try:
            img = cv2.imread(input_path)
            if img is None:
                raise ValueError("无法读取图像")
                
            # 旋转处理
            if angle != 0:
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(img, M, (w, h))
            
            # 翻转处理
            if flip_type == 'horizontal':
                img = cv2.flip(img, 1)
            elif flip_type == 'vertical':
                img = cv2.flip(img, 0)
            elif flip_type == 'both':
                img = cv2.flip(img, -1)  # 水平+垂直翻转
                
            # 保存结果
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)
            
            output_path = os.path.join(self.output_dir, f"{name}_flipped{ext}")
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(self.output_dir, f"{name}_flipped_{counter}{ext}")
                counter += 1
                
            cv2.imwrite(output_path, img)
            return output_path
        except Exception as e:
            print(f"翻转失败: {str(e)}")
            return None

    def process_for_preview(self, input_path, flip_type, angle=0):
        """处理图像用于预览"""
        try:
            img = cv2.imread(input_path)
            if img is None:
                return None
                
            # 旋转处理
            if angle != 0:
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(img, M, (w, h))
            
            # 翻转处理
            if flip_type == 'horizontal':
                img = cv2.flip(img, 1)
            elif flip_type == 'vertical':
                img = cv2.flip(img, 0)
            elif flip_type == 'both':
                img = cv2.flip(img, -1)  # 水平+垂直翻转
                
            # 转换颜色空间从BGR到RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return img_rgb
        except Exception as e:
            print(f"预览处理失败: {str(e)}")
            return None

class ImageFlipController(QWidget):
    """图像翻转UI控制器"""
    def __init__(self):
        super().__init__()
        self.flipper = ImageFlipper()
        self.current_file_index = 0
        self.file_paths = []  # 存储文件路径列表
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('ImageCL-图像翻转工具')
        self.setMinimumSize(700, 650)
        
        # 设置主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_label = QLabel("图像翻转工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        main_layout.addWidget(title_label)
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()
        
        file_btn_layout = QHBoxLayout()
        self.btn_select = QPushButton('选择图片')
        self.btn_select.clicked.connect(self.select_files)
        self.btn_output = QPushButton('选择输出目录')
        self.btn_output.clicked.connect(self.select_output_dir)
        file_btn_layout.addWidget(self.btn_select)
        file_btn_layout.addWidget(self.btn_output)
        file_layout.addLayout(file_btn_layout)
        
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        file_layout.addWidget(self.file_list)
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # 控制和预览区域
        control_preview_layout = QHBoxLayout()
        
        # 控制面板
        control_group = QGroupBox("翻转控制")
        control_layout = QVBoxLayout()
        
        # 翻转类型选择
        flip_type_layout = QVBoxLayout()
        flip_type_layout.addWidget(QLabel("翻转类型:"))
        self.flip_combo = QComboBox()
        self.flip_combo.addItems(['无翻转', '水平翻转', '垂直翻转', '水平+垂直'])
        self.flip_combo.currentTextChanged.connect(self.update_preview)
        flip_type_layout.addWidget(self.flip_combo)
        control_layout.addLayout(flip_type_layout)
        
        # 旋转角度控制
        rotation_layout = QVBoxLayout()
        rotation_layout.addWidget(QLabel("旋转角度:"))
        
        angle_control_layout = QHBoxLayout()
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 360)
        self.angle_slider.setValue(0)
        self.angle_slider.valueChanged.connect(self.update_angle_label)
        self.angle_slider.valueChanged.connect(self.update_preview)
        self.angle_label = QLabel("0°")
        self.angle_label.setFixedWidth(40)
        angle_control_layout.addWidget(self.angle_slider)
        angle_control_layout.addWidget(self.angle_label)
        rotation_layout.addLayout(angle_control_layout)
        
        control_layout.addLayout(rotation_layout)
        
        # 添加一些间距
        control_layout.addSpacing(20)
        
        # 执行按钮
        self.btn_flip = QPushButton('执行翻转')
        self.btn_flip.clicked.connect(self.start_flipping)
        self.btn_flip.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.btn_flip)
        
        # 添加弹性空间使按钮保持在底部
        control_layout.addStretch(1)
        
        control_group.setLayout(control_layout)
        control_group.setFixedWidth(250)
        control_preview_layout.addWidget(control_group)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 250)
        self.preview_label.setStyleSheet("border: 1px solid #cccccc; background-color: #f8f8f8;")
        self.preview_label.setText("选择图片以预览")
        preview_layout.addWidget(self.preview_label)
        
        # 预览控制
        preview_control_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一个")
        self.prev_btn.clicked.connect(self.prev_image)
        self.next_btn = QPushButton("下一个")
        self.next_btn.clicked.connect(self.next_image)
        preview_control_layout.addWidget(self.prev_btn)
        preview_control_layout.addWidget(self.next_btn)
        preview_layout.addLayout(preview_control_layout)
        
        preview_group.setLayout(preview_layout)
        control_preview_layout.addWidget(preview_group)
        
        main_layout.addLayout(control_preview_layout)
        
        # 状态栏
        status_group = QGroupBox("状态")
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f8f8f8; border-radius: 3px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        status_layout.addWidget(self.status_label, 3)
        status_layout.addWidget(self.progress_bar, 1)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        self.setLayout(main_layout)
        
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if files:
            self.file_list.clear()
            self.file_paths = files  # 保存文件路径
            self.file_list.addItems([os.path.basename(f) for f in files])
            self.current_file_index = 0
            self.file_list.setCurrentRow(0)
            self.update_preview()
            
    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.flipper.set_output_dir(directory)
            self.status_label.setText(f"输出目录设置为: {directory}")
            
    def update_angle_label(self, value):
        self.angle_label.setText(f"{value}°")
            
    def load_preview(self, image_path, flip_type, angle):
        try:
            # 使用处理后的图像进行预览
            processed_img = self.flipper.process_for_preview(image_path, flip_type, angle)
            if processed_img is not None:
                # 转换为QImage
                height, width, channel = processed_img.shape
                bytes_per_line = 3 * width
                q_img = QImage(processed_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                # 转换为QPixmap并缩放
                pixmap = QPixmap.fromImage(q_img)
                scaled = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText("预览加载失败")
        except Exception as e:
            self.preview_label.setText(f"预览加载失败: {str(e)}")
            
    def update_preview(self):
        if not self.file_paths:
            return
            
        current_file = self.file_paths[self.current_file_index]
        flip_type = self.get_flip_type_code()
        angle = self.angle_slider.value()
        self.load_preview(current_file, flip_type, angle)
            
    def on_file_selected(self, index):
        if index >= 0 and index < len(self.file_paths):
            self.current_file_index = index
            self.update_preview()
            
    def prev_image(self):
        if self.file_paths:
            self.current_file_index = (self.current_file_index - 1) % len(self.file_paths)
            self.file_list.setCurrentRow(self.current_file_index)
            
    def next_image(self):
        if self.file_paths:
            self.current_file_index = (self.current_file_index + 1) % len(self.file_paths)
            self.file_list.setCurrentRow(self.current_file_index)
            
    def get_flip_type_code(self):
        """获取翻转类型的代码"""
        flip_text = self.flip_combo.currentText()
        flip_map = {
            '无翻转': None,
            '水平翻转': 'horizontal',
            '垂直翻转': 'vertical',
            '水平+垂直': 'both'
        }
        return flip_map[flip_text]
            
    def start_flipping(self):
        if not self.flipper.output_dir:
            QMessageBox.warning(self, "错误", "请先选择输出目录")
            return
            
        if not self.file_paths:
            QMessageBox.warning(self, "错误", "请先选择要处理的图片")
            return
            
        flip_type = self.get_flip_type_code()
        angle = self.angle_slider.value()
        
        # 禁用按钮，防止重复操作
        self.btn_flip.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.btn_output.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.file_paths))
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.worker = FlipWorker(self.flipper, self.file_paths, flip_type, angle)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_flipping_finished)
        self.worker.start()
        
    def on_flipping_finished(self, results):
        # 启用按钮
        self.btn_flip.setEnabled(True)
        self.btn_select.setEnabled(True)
        self.btn_output.setEnabled(True)
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        success_count = sum(1 for r in results if r is not None)
        failed_count = len(results) - success_count
        
        if failed_count == 0:
            self.status_label.setText(f"处理完成! 成功: {success_count}/{len(self.file_paths)}")
            QMessageBox.information(self, "完成", f"所有图像处理成功! 共处理 {success_count} 张图像。")
        else:
            self.status_label.setText(f"处理完成! 成功: {success_count}/{len(self.file_paths)}，失败: {failed_count}")
            QMessageBox.warning(self, "完成", f"处理完成! 成功: {success_count}，失败: {failed_count}")

if __name__ == '__main__':
    app = QApplication([])
    window = ImageFlipController()
    window.show()
    app.exec_()
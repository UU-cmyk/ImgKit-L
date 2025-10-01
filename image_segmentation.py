import sys
import os
import numpy as np
from PIL import Image, ImageDraw
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QSpinBox, QMessageBox, QProgressBar,
                             QListWidget, QListWidgetItem, QSlider, QGroupBox, QCheckBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QIcon

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(int, int)  # 成功数量, 总数量
    
    def __init__(self, image_paths, output_dir, threshold, min_area, alpha_threshold, use_alpha, use_white):
        super().__init__()
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.threshold = threshold
        self.min_area = min_area
        self.alpha_threshold = alpha_threshold
        self.use_alpha = use_alpha
        self.use_white = use_white
        self.success_count = 0
        self.is_running = True  # 添加运行状态标志
        
    def run(self):
        total = len(self.image_paths)
        for i, image_path in enumerate(self.image_paths):
            if not self.is_running:  # 检查是否应该停止
                break
                
            try:
                self.progress_updated.emit(i + 1, f"正在处理: {os.path.basename(image_path)}")
                
                # 处理单张图片
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                original_image = Image.open(image_path).convert('RGBA')
                image_array = np.array(original_image)
                height, width, _ = image_array.shape

                # 创建二值化图像
                binary_image = np.zeros((height, width), dtype=np.uint8)
                r, g, b, a = image_array[:,:,0], image_array[:,:,1], image_array[:,:,2], image_array[:,:,3]
                
                # 背景检测条件
                background_mask_alpha = a < self.alpha_threshold
                background_mask_white = (r > self.threshold) & (g > self.threshold) & (b > self.threshold) & (a > 200)
                
                # 合并背景条件
                if self.use_alpha and self.use_white:
                    background_mask = background_mask_alpha | background_mask_white
                elif self.use_alpha:
                    background_mask = background_mask_alpha
                elif self.use_white:
                    background_mask = background_mask_white
                else:
                    # 如果没有选择任何背景检测方式，默认使用alpha检测
                    background_mask = background_mask_alpha
                    
                binary_image[background_mask] = 0
                binary_image[~background_mask] = 1

                # 查找连通区域 - 使用更高效的算法
                from scipy import ndimage
                labeled_array, num_features = ndimage.label(binary_image)
                
                components = []
                for i in range(1, num_features + 1):
                    points = np.where(labeled_array == i)
                    if len(points[0]) > 0:
                        ys, xs = points
                        min_x, max_x = np.min(xs), np.max(xs)
                        min_y, max_y = np.min(ys), np.max(ys)
                        comp_width = max_x - min_x + 1
                        comp_height = max_y - min_y + 1
                        area = comp_width * comp_height
                        if area >= self.min_area:
                            components.append((min_x, min_y, max_x, max_y))

                # 导出元素
                for idx, bbox in enumerate(components):
                    min_x, min_y, max_x, max_y = bbox
                    element_region = original_image.crop((min_x, min_y, max_x+1, max_y+1))
                    output_filename = f"{base_name}_element_{idx+1}.png"
                    output_path = os.path.join(self.output_dir, output_filename)
                    element_region.save(output_path, 'PNG')
                
                self.success_count += 1
                
            except Exception as e:
                self.progress_updated.emit(i + 1, f"处理失败: {os.path.basename(image_path)} - {str(e)}")
        
        self.finished.emit(self.success_count, total)
        
    def stop(self):
        self.is_running = False

class ImageSegmentationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.output_dir = ""
        self.processing_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('ImageCF-UI元素提取工具')
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 顶部按钮区域
        top_layout = QHBoxLayout()
        self.btn_add = QPushButton('添加图片')
        self.btn_add.clicked.connect(self.add_images)
        self.btn_clear = QPushButton('清空列表')
        self.btn_clear.clicked.connect(self.clear_list)
        self.btn_output = QPushButton('选择输出目录')
        self.btn_output.clicked.connect(self.select_output_dir)
        self.btn_export = QPushButton('开始导出')
        self.btn_export.clicked.connect(self.export_elements)
        self.btn_export.setEnabled(False)
        self.btn_stop = QPushButton('停止处理')
        self.btn_stop.clicked.connect(self.stop_processing)
        self.btn_stop.setEnabled(False)

        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_clear)
        top_layout.addWidget(self.btn_output)
        top_layout.addWidget(self.btn_export)
        top_layout.addWidget(self.btn_stop)
        main_layout.addLayout(top_layout)

        # 分割器：左侧图片列表，右侧预览和参数
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：图片列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("图片列表"))
        self.list_images = QListWidget()
        self.list_images.itemSelectionChanged.connect(self.preview_image)
        left_layout.addWidget(self.list_images)
        splitter.addWidget(left_widget)
        
        # 右侧：预览和参数
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 预览区域
        preview_group = QGroupBox("图片预览")
        preview_layout = QVBoxLayout()
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(400, 300)
        self.lbl_preview.setText("请选择图片")
        self.lbl_preview.setStyleSheet("border: 1px solid gray;")
        preview_layout.addWidget(self.lbl_preview)
        
        self.lbl_info = QLabel("未选择图片")
        preview_layout.addWidget(self.lbl_info)
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)
        
        # 参数设置区域
        params_group = QGroupBox("提取参数")
        params_layout = QVBoxLayout()
        
        # 阈值参数
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel('检测灵敏度 (阈值):'))
        self.slider_threshold = QSlider(Qt.Horizontal)
        self.slider_threshold.setRange(0, 255)
        self.slider_threshold.setValue(240)
        self.slider_threshold.valueChanged.connect(self.update_threshold_label)
        threshold_layout.addWidget(self.slider_threshold)
        self.lbl_threshold = QLabel('240')
        threshold_layout.addWidget(self.lbl_threshold)
        params_layout.addLayout(threshold_layout)
        
        # Alpha阈值参数
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(QLabel('Alpha通道阈值:'))
        self.slider_alpha = QSlider(Qt.Horizontal)
        self.slider_alpha.setRange(0, 255)
        self.slider_alpha.setValue(30)
        self.slider_alpha.valueChanged.connect(self.update_alpha_label)
        alpha_layout.addWidget(self.slider_alpha)
        self.lbl_alpha = QLabel('30')
        alpha_layout.addWidget(self.lbl_alpha)
        params_layout.addLayout(alpha_layout)
        
        # 最小面积参数
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel('最小元素面积:'))
        self.spin_min_area = QSpinBox()
        self.spin_min_area.setRange(1, 10000)
        self.spin_min_area.setValue(100)
        area_layout.addWidget(self.spin_min_area)
        area_layout.addWidget(QLabel('像素'))
        params_layout.addLayout(area_layout)
        
        # 选项复选框
        options_layout = QHBoxLayout()
        self.cb_use_alpha = QCheckBox('使用Alpha通道检测')
        self.cb_use_alpha.setChecked(True)
        options_layout.addWidget(self.cb_use_alpha)
        
        self.cb_use_white = QCheckBox('排除白色背景')
        self.cb_use_white.setChecked(True)
        options_layout.addWidget(self.cb_use_white)
        
        params_layout.addLayout(options_layout)
        params_group.setLayout(params_layout)
        right_layout.addWidget(params_group)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        main_layout.addWidget(splitter, 1)
        
        # 进度条和状态
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel('准备就绪')
        main_layout.addWidget(self.lbl_status)

    def update_threshold_label(self):
        self.lbl_threshold.setText(str(self.slider_threshold.value()))
        
    def update_alpha_label(self):
        self.lbl_alpha.setText(str(self.slider_alpha.value()))

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if not files:
            return

        for file in files:
            if file not in self.image_paths:
                item = QListWidgetItem(os.path.basename(file))
                item.setData(Qt.UserRole, file)
                
                # 添加缩略图
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(pixmap))
                
                self.list_images.addItem(item)
                self.image_paths.append(file)
        
        self.update_export_button()
        self.lbl_status.setText(f"已添加 {len(files)} 张图片，总共 {len(self.image_paths)} 张")

    def clear_list(self):
        self.list_images.clear()
        self.image_paths = []
        self.lbl_preview.setText("请选择图片")
        self.lbl_info.setText("未选择图片")
        self.update_export_button()
        self.lbl_status.setText("已清空图片列表")

    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir = directory
            self.update_export_button()
            self.lbl_status.setText(f"输出目录: {directory}")

    def update_export_button(self):
        self.btn_export.setEnabled(len(self.image_paths) > 0 and self.output_dir != "")

    def preview_image(self):
        current_item = self.list_images.currentItem()
        if not current_item:
            return

        image_path = current_item.data(Qt.UserRole)
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self.lbl_preview.setText("无法加载图片")
                self.lbl_info.setText("无法加载图片")
                return

            # 显示图片信息
            img = Image.open(image_path)
            width, height = img.size
            mode = img.mode
            self.lbl_info.setText(f"尺寸: {width}×{height} | 模式: {mode}")

            # 调整预览大小
            scaled_pixmap = pixmap.scaled(
                self.lbl_preview.width() - 20, 
                self.lbl_preview.height() - 20,
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.lbl_preview.setPixmap(scaled_pixmap)
        except Exception as e:
            self.lbl_preview.setText("图片加载失败")
            self.lbl_info.setText(f"错误: {str(e)}")

    def export_elements(self):
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先添加图片！")
            return
            
        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return

        # 检查输出目录是否存在，如果不存在则创建
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建输出目录: {str(e)}")
                return

        # 获取参数
        threshold = self.slider_threshold.value()
        min_area = self.spin_min_area.value()
        alpha_threshold = self.slider_alpha.value()
        use_alpha = self.cb_use_alpha.isChecked()
        use_white = self.cb_use_white.isChecked()

        # 禁用按钮，防止重复操作
        self.set_controls_enabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.image_paths))
        
        # 创建处理线程
        self.processing_thread = ProcessingThread(
            self.image_paths, self.output_dir, threshold, min_area, 
            alpha_threshold, use_alpha, use_white
        )
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.start()

    def stop_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait()
            self.lbl_status.setText("处理已停止")
            self.set_controls_enabled(True)
            self.btn_stop.setEnabled(False)

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)

    def on_processing_finished(self, success_count, total_count):
        self.progress_bar.setVisible(False)
        self.set_controls_enabled(True)
        self.btn_stop.setEnabled(False)
        
        if success_count == total_count:
            QMessageBox.information(self, "完成", f"成功导出所有 {success_count} 张图片的元素")
        else:
            QMessageBox.warning(self, "完成", 
                               f"处理完成，成功: {success_count}/{total_count} 张图片")
        
        self.lbl_status.setText(f"处理完成: {success_count}/{total_count} 成功")

    def set_controls_enabled(self, enabled):
        self.btn_add.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_output.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.list_images.setEnabled(enabled)

    def closeEvent(self, event):
        # 确保在关闭窗口时停止线程
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageSegmentationController()
    ex.show()
    sys.exit(app.exec_())
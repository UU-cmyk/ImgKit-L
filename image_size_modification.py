import sys
import os
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QListWidget, QListWidgetItem,
                            QSlider, QSpinBox, QComboBox, QCheckBox, QMessageBox, 
                            QProgressBar, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

class ImageResizer:
    """图像大小调整核心类"""
    
    def __init__(self):
        self.supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']
    
    def resize_image(self, image_path, output_path, width, height, 
                    keep_aspect_ratio=True, resample_method=Image.LANCZOS):
        """
        调整图像大小
        
        参数:
            image_path: 输入图像路径
            output_path: 输出图像路径
            width: 目标宽度
            height: 目标高度
            keep_aspect_ratio: 是否保持宽高比
            resample_method: 重采样方法
        """
        try:
            with Image.open(image_path) as img:
                # 转换模式为RGB（避免调色板问题）
                if img.mode in ('P', 'RGBA', 'LA'):
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
                
                original_width, original_height = img.size
                
                # 计算目标尺寸
                if keep_aspect_ratio:
                    # 保持宽高比
                    ratio = min(width / original_width, height / original_height)
                    new_width = int(original_width * ratio)
                    new_height = int(original_height * ratio)
                else:
                    new_width = width
                    new_height = height
                
                # 调整大小
                resized_img = img.resize((new_width, new_height), resample_method)
                
                # 保存图像
                if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
                    resized_img = resized_img.convert('RGB')  # JPEG不支持透明度
                
                resized_img.save(output_path, quality=95)
                return True, f"成功调整: {os.path.basename(image_path)}"
                
        except Exception as e:
            return False, f"处理失败 {os.path.basename(image_path)}: {str(e)}"
    
    def get_resample_method(self, method_name):
        """获取PIL重采样方法"""
        methods = {
            "最近邻": Image.NEAREST,
            "双线性": Image.BILINEAR,
            "双三次": Image.BICUBIC,
            "Lanczos": Image.LANCZOS
        }
        return methods.get(method_name, Image.LANCZOS)

class ResizeWorker(QThread):
    """后台处理线程"""
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(int, int)  # 成功数量, 总数量
    
    def __init__(self, image_paths, output_dir, width, height, 
                 keep_ratio, resample_method, prefix="resized"):
        super().__init__()
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.keep_ratio = keep_ratio
        self.resample_method = resample_method
        self.prefix = prefix
        self.success_count = 0
        self.resizer = ImageResizer()
    
    def run(self):
        total = len(self.image_paths)
        for i, image_path in enumerate(self.image_paths):
            try:
                # 生成输出文件名
                base_name = os.path.basename(image_path)
                name, ext = os.path.splitext(base_name)
                output_filename = f"{self.prefix}_{name}{ext}"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # 处理重名文件
                counter = 1
                while os.path.exists(output_path):
                    output_filename = f"{self.prefix}_{name}_{counter}{ext}"
                    output_path = os.path.join(self.output_dir, output_filename)
                    counter += 1
                
                # 调整图像大小
                success, message = self.resizer.resize_image(
                    image_path, output_path, self.width, self.height,
                    self.keep_ratio, self.resample_method
                )
                
                if success:
                    self.success_count += 1
                    self.progress_updated.emit(i + 1, f"成功: {base_name}")
                else:
                    self.progress_updated.emit(i + 1, message)
                    
            except Exception as e:
                self.progress_updated.emit(i + 1, f"错误: {os.path.basename(image_path)} - {str(e)}")
        
        self.finished.emit(self.success_count, total)

class ImageResizeController(QMainWindow):
    """图像大小调整界面控制器"""
    
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.output_dir = ""
        self.worker_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("ImageSC-图像大小调整器")
        self.setGeometry(100, 100, 1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 顶部按钮区域
        self.create_top_buttons(layout)
        
        # 参数设置区域
        self.create_parameter_section(layout)
        
        # 分割器：图片列表和预览
        splitter = QSplitter(Qt.Horizontal)
        self.create_image_list_section(splitter)
        self.create_preview_section(splitter)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter, 1)
        
        # 进度和状态区域
        self.create_progress_section(layout)
    
    def create_top_buttons(self, parent_layout):
        """创建顶部按钮区域"""
        button_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("添加图片")
        self.btn_add.clicked.connect(self.add_images)
        
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self.clear_list)
        
        self.btn_output = QPushButton("选择输出目录")
        self.btn_output.clicked.connect(self.select_output_dir)
        
        self.btn_process = QPushButton("开始调整")
        self.btn_process.clicked.connect(self.process_images)
        self.btn_process.setEnabled(False)
        
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_clear)
        button_layout.addWidget(self.btn_output)
        button_layout.addWidget(self.btn_process)
        button_layout.addStretch()
        
        parent_layout.addLayout(button_layout)
    
    def create_parameter_section(self, parent_layout):
        """创建参数设置区域"""
        param_group = QGroupBox("调整参数")
        param_layout = QVBoxLayout()
        
        # 尺寸设置
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("宽度:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 10000)
        self.spin_width.setValue(800)
        size_layout.addWidget(self.spin_width)
        
        size_layout.addWidget(QLabel("高度:"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 10000)
        self.spin_height.setValue(600)
        size_layout.addWidget(self.spin_height)
        
        self.cb_keep_ratio = QCheckBox("保持宽高比")
        self.cb_keep_ratio.setChecked(True)
        size_layout.addWidget(self.cb_keep_ratio)
        
        size_layout.addStretch()
        param_layout.addLayout(size_layout)
        
        # 算法设置
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("缩放算法:"))
        self.combo_algo = QComboBox()
        self.combo_algo.addItems(["最近邻", "双线性", "双三次", "Lanczos"])
        self.combo_algo.setCurrentText("Lanczos")
        algo_layout.addWidget(self.combo_algo)
        
        algo_layout.addWidget(QLabel("文件名前缀:"))
        self.edit_prefix = QComboBox()
        self.edit_prefix.setEditable(True)
        self.edit_prefix.addItems(["resized", "adjusted", "scaled"])
        self.edit_prefix.setCurrentText("resized")
        algo_layout.addWidget(self.edit_prefix)
        
        algo_layout.addStretch()
        param_layout.addLayout(algo_layout)
        
        param_group.setLayout(param_layout)
        parent_layout.addWidget(param_group)
    
    def create_image_list_section(self, splitter):
        """创建图片列表区域"""
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        
        list_layout.addWidget(QLabel("图片列表"))
        self.list_images = QListWidget()
        self.list_images.itemSelectionChanged.connect(self.preview_image)
        list_layout.addWidget(self.list_images)
        
        splitter.addWidget(list_widget)
    
    def create_preview_section(self, splitter):
        """创建预览区域"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # 原图预览
        preview_group = QGroupBox("图片预览")
        preview_group_layout = QVBoxLayout(preview_group)
        
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(400, 300)
        self.lbl_preview.setText("请选择图片进行预览")
        self.lbl_preview.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        preview_group_layout.addWidget(self.lbl_preview)
        
        self.lbl_info = QLabel("未选择图片")
        preview_group_layout.addWidget(self.lbl_info)
        
        preview_layout.addWidget(preview_group)
        splitter.addWidget(preview_widget)
    
    def create_progress_section(self, parent_layout):
        """创建进度和状态区域"""
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        parent_layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("准备就绪")
        parent_layout.addWidget(self.lbl_status)
    
    def add_images(self):
        """添加图片到列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;所有文件 (*.*)"
        )
        
        if not files:
            return
        
        new_count = 0
        for file_path in files:
            if file_path not in self.image_paths:
                # 创建列表项
                item = QListWidgetItem(os.path.basename(file_path))
                item.setData(Qt.UserRole, file_path)
                
                # 添加缩略图
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    thumb = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(thumb))
                
                self.list_images.addItem(item)
                self.image_paths.append(file_path)
                new_count += 1
        
        self.update_process_button()
        self.lbl_status.setText(f"已添加 {new_count} 张图片，总共 {len(self.image_paths)} 张")
    
    def clear_list(self):
        """清空图片列表"""
        self.list_images.clear()
        self.image_paths = []
        self.lbl_preview.setText("请选择图片进行预览")
        self.lbl_info.setText("未选择图片")
        self.update_process_button()
        self.lbl_status.setText("已清空图片列表")
    
    def select_output_dir(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir = directory
            self.update_process_button()
            self.lbl_status.setText(f"输出目录: {directory}")
    
    def update_process_button(self):
        """更新处理按钮状态"""
        has_images = len(self.image_paths) > 0
        has_output = bool(self.output_dir)
        self.btn_process.setEnabled(has_images and has_output)
    
    def preview_image(self):
        """预览选中的图片"""
        current_item = self.list_images.currentItem()
        if not current_item:
            return
        
        image_path = current_item.data(Qt.UserRole)
        pixmap = QPixmap(image_path)
        
        if pixmap.isNull():
            self.lbl_preview.setText("无法加载图片")
            self.lbl_info.setText("无法加载图片")
            return
        
        # 显示图片信息
        img = Image.open(image_path)
        width, height = img.size
        file_size = os.path.getsize(image_path) / 1024  # KB
        
        info_text = (f"尺寸: {width} × {height} | "
                     f"格式: {img.format} | "
                     f"大小: {file_size:.1f} KB")
        self.lbl_info.setText(info_text)
        
        # 调整预览大小
        scaled_pixmap = pixmap.scaled(
            self.lbl_preview.width() - 20,
            self.lbl_preview.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.lbl_preview.setPixmap(scaled_pixmap)
    
    def process_images(self):
        """开始处理图片"""
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先添加图片！")
            return
        
        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return
        
        # 获取参数
        width = self.spin_width.value()
        height = self.spin_height.value()
        keep_ratio = self.cb_keep_ratio.isChecked()
        resample_method = ImageResizer().get_resample_method(self.combo_algo.currentText())
        prefix = self.edit_prefix.currentText()
        
        # 禁用控件
        self.set_controls_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.image_paths))
        
        # 创建处理线程
        self.worker_thread = ResizeWorker(
            self.image_paths, self.output_dir, width, height,
            keep_ratio, resample_method, prefix
        )
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.finished.connect(self.on_processing_finished)
        self.worker_thread.start()
    
    def update_progress(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)
    
    def on_processing_finished(self, success_count, total_count):
        """处理完成回调"""
        self.progress_bar.setVisible(False)
        self.set_controls_enabled(True)
        
        if success_count == total_count:
            QMessageBox.information(self, "完成", 
                                   f"成功处理所有 {success_count} 张图片！\n输出目录: {self.output_dir}")
        else:
            QMessageBox.warning(self, "完成", 
                               f"处理完成！成功: {success_count}/{total_count} 张图片")
        
        self.lbl_status.setText(f"处理完成: {success_count}/{total_count} 成功")
    
    def set_controls_enabled(self, enabled):
        """设置控件启用状态"""
        self.btn_add.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_output.setEnabled(enabled)
        self.btn_process.setEnabled(enabled and len(self.image_paths) > 0 and bool(self.output_dir))
        self.list_images.setEnabled(enabled)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = ImageResizeController()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

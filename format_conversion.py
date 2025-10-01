import os
import shutil
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QFileDialog, QListWidget, QLabel, QComboBox, QGroupBox,
                            QGridLayout, QSizePolicy, QSpacerItem, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap


class FormatConverter:
    """核心格式转换处理器"""
    SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.dds']
    
    def __init__(self):
        self.output_dir = ""
        self.preview_image = None
        
    def set_output_dir(self, path):
        self.output_dir = path
        
    def convert_image(self, input_path, output_format):
        """执行单张图片格式转换"""
        try:
            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                return None
                
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)
            
            # 检查输出目录是否存在，不存在则创建
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            # 防重复名称处理
            output_path = os.path.join(self.output_dir, f"{name}.{output_format}")
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(self.output_dir, f"{name}_{counter}.{output_format}")
                counter += 1
                
            # 使用上下文管理器确保文件正确关闭
            with Image.open(input_path) as img:
                # 处理不支持Alpha通道的格式
                if output_format.lower() in ['jpg', 'jpeg', 'bmp']:
                    # 检查图像是否有Alpha通道
                    if img.mode in ['RGBA', 'LA', 'P']:
                        # 对于有透明度的图像，创建白色背景
                        if img.mode in ['RGBA', 'LA']:
                            # 创建白色背景
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'RGBA':
                                # 使用alpha通道作为掩码
                                background.paste(img, mask=img.split()[-1])
                            else:
                                # 对于LA模式（灰度+透明度）
                                background.paste(img.convert('RGBA'), mask=img.split()[-1])
                            img = background
                        else:
                            # 对于调色板模式等其他模式，直接转换为RGB
                            img = img.convert('RGB')
                    elif img.mode != 'RGB':
                        # 其他非RGB模式也转换为RGB
                        img = img.convert('RGB')
                elif img.mode == 'P':
                    # 对于调色板模式，转换为RGBA或RGB
                    img = img.convert('RGBA' if output_format.lower() in ['png', 'tiff'] else 'RGB')
                
                # 保存图像
                save_params = {}
                if output_format.lower() in ['jpg', 'jpeg']:
                    save_params['quality'] = 95  # 设置JPG质量
                elif output_format.lower() in ['tiff']:
                    save_params['compression'] = 'tiff_lzw'  # 设置TIFF压缩
                
                img.save(output_path, format=output_format.upper(), **save_params)
            return output_path
                
        except Exception as e:
            print(f"转换失败: {str(e)}")
            return None

    def batch_convert(self, file_list, output_format):
        """批量转换处理"""
        results = []
        for file_path in file_list:
            results.append(self.convert_image(file_path, output_format))
        return results

class FormatConversionController(QWidget):
    """格式转换UI控制器"""
    def __init__(self):
        super().__init__()
        self.converter = FormatConverter()
        self.current_files = []  # 存储当前文件列表
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('ImageTT - 图像格式转换工具')
        self.setGeometry(300, 300, 800, 600)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        control_panel = QGroupBox("转换控制")
        control_panel.setMaximumWidth(470)
        control_layout = QVBoxLayout()
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()
        
        self.btn_select = QPushButton('选择图片文件', self)
        self.btn_select.clicked.connect(self.select_files)
        file_layout.addWidget(self.btn_select)
        
        self.file_list = QListWidget(self)
        self.file_list.setMinimumHeight(150)
        self.file_list.currentRowChanged.connect(self.on_file_selection_changed)
        file_layout.addWidget(self.file_list)
        
        # 添加清空列表按钮
        self.btn_clear = QPushButton('清空列表', self)
        self.btn_clear.clicked.connect(self.clear_file_list)
        file_layout.addWidget(self.btn_clear)
        
        file_group.setLayout(file_layout)
        control_layout.addWidget(file_group)
        
        # 格式选择区域
        format_group = QGroupBox("输出设置")
        format_layout = QGridLayout()
        
        format_layout.addWidget(QLabel("输出格式:"), 0, 0)
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(['png', 'jpg', 'jpeg', 'bmp', 'tiff'])
        format_layout.addWidget(self.format_combo, 0, 1)
        
        self.btn_output = QPushButton('选择输出目录', self)
        self.btn_output.clicked.connect(self.select_output_dir)
        format_layout.addWidget(self.btn_output, 1, 0, 1, 2)
        
        # 添加输出目录显示
        self.output_dir_label = QLabel("未选择输出目录", self)
        format_layout.addWidget(self.output_dir_label, 2, 0, 1, 2)
        
        format_group.setLayout(format_layout)
        control_layout.addWidget(format_group)
        
        # 操作按钮
        self.btn_convert = QPushButton('开始转换', self)
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_convert.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.btn_convert)
        
        # 状态显示
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("准备就绪", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border: 1px solid #d0d0d0; }")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        control_layout.addWidget(status_group)
        
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel)
        
        # 右侧预览区域
        preview_panel = QGroupBox("图片预览")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 400)
        self.preview_label.setStyleSheet("QLabel { background-color: #f8f8f8; border: 1px solid #d0d0d0; }")
        self.preview_label.setText("预览区域\n\n选择图片后可查看预览")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        
        # 预览信息
        info_group = QGroupBox("图片信息")
        info_layout = QGridLayout()
        
        self.info_name = QLabel("文件名: -")
        info_layout.addWidget(self.info_name, 0, 0)
        
        self.info_size = QLabel("尺寸: -")
        info_layout.addWidget(self.info_size, 0, 1)
        
        self.info_format = QLabel("格式: -")
        info_layout.addWidget(self.info_format, 1, 0)
        
        self.info_path = QLabel("路径: -")
        self.info_path.setWordWrap(True)
        info_layout.addWidget(self.info_path, 1, 1, 1, 2)
        
        info_group.setLayout(info_layout)
        preview_layout.addWidget(info_group)
        
        preview_panel.setLayout(preview_layout)
        main_layout.addWidget(preview_panel)
        
        self.setLayout(main_layout)
        
    def on_file_selection_changed(self, current_row):
        """当文件选择变化时更新预览"""
        if current_row >= 0 and current_row < len(self.current_files):
            file_path = self.current_files[current_row]
            self.load_preview(file_path)
            self.update_file_info(file_path)
        
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.dds)"
        )
        if files:
            self.file_list.clear()
            self.current_files = files  # 保存完整路径列表
            # 只显示文件名在列表中
            self.file_list.addItems([os.path.basename(f) for f in files])
            self.load_preview(files[0])
            self.update_file_info(files[0])
            self.status_label.setText(f"已选择 {len(files)} 个文件")
            
    def clear_file_list(self):
        """清空文件列表"""
        self.file_list.clear()
        self.current_files = []
        self.preview_label.setText("预览区域\n\n选择图片后可查看预览")
        self.update_file_info(None)
        self.status_label.setText("已清空文件列表")
            
    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.converter.set_output_dir(directory)
            self.status_label.setText(f"输出目录: {directory}")
            # 缩短显示路径，避免界面过长
            short_path = directory
            if len(directory) > 40:
                short_path = "..." + directory[-40:]
            self.output_dir_label.setText(f"输出目录: {short_path}")
            self.output_dir_label.setToolTip(directory)  # 设置完整路径为提示
            
    def load_preview(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放预览图以适应标签大小
                scaled = pixmap.scaled(
                    self.preview_label.width() - 20, 
                    self.preview_label.height() - 20,
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText("无法加载预览\n可能是格式不受支持")
        except Exception as e:
            self.preview_label.setText(f"预览加载失败\n{str(e)}")
            
    def update_file_info(self, image_path):
        try:
            if not image_path:
                self.info_name.setText("文件名: -")
                self.info_size.setText("尺寸: -")
                self.info_format.setText("格式: -")
                self.info_path.setText("路径: -")
                return
                
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            
            self.info_name.setText(f"文件名: {filename}")
            # 缩短显示路径，避免界面过长
            short_path = image_path
            if len(image_path) > 50:
                short_path = "..." + image_path[-50:]
            self.info_path.setText(f"路径: {short_path}")
            self.info_path.setToolTip(image_path)  # 设置完整路径为提示
            
            # 使用Pillow获取更准确的图像信息
            try:
                with Image.open(image_path) as img:
                    self.info_size.setText(f"尺寸: {img.width} x {img.height}")
                    # 显示图像模式
                    self.info_format.setText(f"格式: {ext.upper()} ({img.mode})")
            except:
                # 备用方案：使用QPixmap获取图像信息
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.info_size.setText(f"尺寸: {pixmap.width()} x {pixmap.height()}")
                    self.info_format.setText(f"格式: {ext.upper()}")
                else:
                    self.info_size.setText("尺寸: -")
                    self.info_format.setText(f"格式: {ext.upper()}")
        except:
            self.info_name.setText("文件名: -")
            self.info_size.setText("尺寸: -")
            self.info_format.setText("格式: -")
            self.info_path.setText("路径: -")
            
    def start_conversion(self):
        if not self.converter.output_dir:
            self.status_label.setText("错误: 请先选择输出目录")
            QMessageBox.warning(self, "警告", "请先选择输出目录")
            return
            
        if not self.current_files:
            self.status_label.setText("错误: 请先选择要转换的文件")
            QMessageBox.warning(self, "警告", "请先选择要转换的文件")
            return
            
        output_format = self.format_combo.currentText()
        
        # 禁用按钮防止重复操作
        self.btn_convert.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_output.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.current_files))
        self.progress_bar.setValue(0)
        
        # 执行转换
        results = []
        for i, file_path in enumerate(self.current_files):
            self.status_label.setText(f"正在转换: {os.path.basename(file_path)}")
            self.progress_bar.setValue(i)
            QApplication.processEvents()  # 更新UI
            
            result = self.converter.convert_image(file_path, output_format)
            results.append(result)
            
            # 如果转换失败，显示错误信息
            if result is None:
                QMessageBox.warning(self, "转换失败", f"文件 {os.path.basename(file_path)} 转换失败")
        
        # 更新进度条到完成状态
        self.progress_bar.setValue(len(self.current_files))
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 重新启用按钮
        self.btn_convert.setEnabled(True)
        self.btn_select.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.btn_output.setEnabled(True)
        
        # 统计成功转换的文件数
        success_count = len([r for r in results if r is not None])
        self.status_label.setText(f"转换完成! 成功转换 {success_count}/{len(self.current_files)} 个文件")
        
        if success_count == len(self.current_files):
            QMessageBox.information(self, "完成", f"所有文件转换成功!")
        elif success_count > 0:
            QMessageBox.information(self, "完成", f"成功转换 {success_count} 个文件，{len(self.current_files) - success_count} 个文件失败")
        else:
            QMessageBox.warning(self, "错误", "所有文件转换失败!")

if __name__ == '__main__':
    app = QApplication([])
    window = FormatConversionController()
    window.show()
    app.exec_()
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QDesktopWidget, QGridLayout, QStatusBar,
                            QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QFontDatabase

class ImageToolLauncher(QMainWindow):
    """统一启动台"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('ImgKit-L')
        self.setMinimumSize(500, 400)
        self.setFixedSize(500,480)
        
        # 设置窗口图标
        try:
            self.setWindowIcon(QIcon('./Assets/Img/App_Icon.png'))
            print("主窗口图标加载成功")
        except:
            print("主窗口图标加载失败")
            pass
        
        # 居中显示
        self.center()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("ImgKit-L")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        main_layout.addWidget(title_label)
        
        # 版本信息
        version_label = QLabel("版本 1.1.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #7f8c8d;")
        main_layout.addWidget(version_label)
       
        author_label = QLabel("by.K_Lan")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
        main_layout.addWidget(author_label)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(separator)
        
        # 功能按钮区域
        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(10, 10, 10, 10)
        
        # 获取图标基础路径
        script_path = os.path.abspath(__file__)
        icon_base_path = os.path.join(os.path.dirname(script_path), "Assets", "Img", "Function_Icon")
        
        # 功能按钮
        buttons = [
            ('格式转换', 'format_conversion_svg', self.open_format_converter, 0, 0),
            ('图像翻转', 'image_flip_svg', self.open_image_flipper, 0, 1),
            ('轮廓分割', 'image_segmentation_svg', self.open_segmenter, 1, 0),
            ('图像查重', 'image_deduplication_svg', self.open_deduplicator, 1, 1),
            ('图像压缩', 'image_compression_svg', self.open_compressor, 2, 0),
            ('大小调整', 'image_size_modification_svg', self.open_modification, 2, 1)
        ]
        
        for text, icon_name, callback, row, col in buttons:
            btn = QPushButton(text, self)
            btn.setMinimumHeight(50)
            
            # 设置按钮图标
            icon_path = os.path.join(icon_base_path, f"{icon_name}.svg")
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(24, 24))  # 设置图标大小
            
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    padding: 10px;
                    text-align: left;
                    padding-left: 15px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """)
            btn.clicked.connect(callback)
            button_layout.addWidget(btn, row, col)
        
        # 添加弹性空间使按钮居中
        button_layout.setColumnStretch(2, 1)
        button_layout.setRowStretch(3, 1)
        
        main_layout.addLayout(button_layout)
        
        # 底部信息
        info_label = QLabel("选择上方功能开始图像处理操作")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #95a5a6; margin-top: 30px; font-style: italic;")
        main_layout.addWidget(info_label)
        
        central_widget.setLayout(main_layout)
        
        # 创建状态栏
        self.statusBar().showMessage('就绪')
        
    def center(self):
        """居中窗口"""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
    def open_format_converter(self):
        self.statusBar().showMessage('正在打开格式转换工具...')
        try:
            from format_conversion import FormatConversionController
            self.window = FormatConversionController()
            self.window.show()
            self.statusBar().showMessage('格式转换工具已打开')
        except ImportError as e:
            self.statusBar().showMessage(f'错误: 无法导入格式转换模块 - {str(e)}')
        
    def open_image_flipper(self):
        self.statusBar().showMessage('正在打开图像翻转工具...')
        try:
            from image_flip import ImageFlipController
            self.window = ImageFlipController()
            self.window.show()
            self.statusBar().showMessage('图像翻转工具已打开')
        except ImportError as e:
            self.statusBar().showMessage(f'错误: 无法导入图像翻转模块 - {str(e)}')
        
    def open_segmenter(self):
        self.statusBar().showMessage('正在打开轮廓分割工具...')
        try:
            from image_segmentation import ImageSegmentationController
            self.window = ImageSegmentationController()
            self.window.show()
            self.statusBar().showMessage('轮廓分割工具已打开')
        except ImportError as e:
            self.statusBar().showMessage(f'错误: 无法导入轮廓分割模块 - {str(e)}')
        
    def open_deduplicator(self):
        self.statusBar().showMessage('正在打开图像查重工具...')
        try:
            from image_deduplication import ImageDeduplicationController
            self.window = ImageDeduplicationController()
            self.window.show()
            self.statusBar().showMessage('图像查重工具已打开')
        except ImportError as e:
            self.statusBar().showMessage(f'错误: 无法导入图像查重模块 - {str(e)}')
        
    def open_compressor(self):
        self.statusBar().showMessage('正在打开图像压缩工具...')
        try:
            from image_compression import ImageCompressionController
            self.window = ImageCompressionController()
            self.window.show()
            self.statusBar().showMessage('图像压缩工具已打开')
        except ImportError as e:
            self.statusBar().showMessage(f'错误: 无法导入图像压缩模块 - {str(e)}')

    def open_modification(self):
        self.statusBar().showMessage('正在打开图像大小调整工具...')
        try:
            from image_size_modification import ImageResizeController
            self.window = ImageResizeController()
            self.window.show()
            self.statusBar().showMessage('大小调整工具已打开')
        except ImportError as e:
            self.statusBar().showMessage(f'错误: 无法导入大小调整模块 - {str(e)}')

def load_custom_font():
    """加载自定义字体文件"""
    # 获取当前脚本的绝对路径
    script_path = os.path.abspath(__file__)
    # 构建字体文件路径
    font_path = os.path.join(os.path.dirname(script_path), "Assets", "Font", "Siyuan_Heiti.otf")
    
    # 检查字体文件是否存在
    if not os.path.exists(font_path):
        print(f"警告: 字体文件不存在: {font_path}")
        return None
    
    # 加载字体
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        print(f"错误: 无法加载字体文件: {font_path}")
        return None
    
    # 获取字体家族
    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if not font_families:
        print(f"错误: 字体文件中未找到有效字体家族: {font_path}")
        return None
    
    # 创建字体对象
    custom_font = QFont(font_families[0])
    custom_font.setPointSize(10)  # 设置默认字体大小
    
    return custom_font

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 尝试加载自定义字体
    custom_font = load_custom_font()
    if custom_font:
        app.setFont(custom_font)
        print(f"成功加载并使用字体: {custom_font.family()}")
    else:
        print("使用系统默认字体")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    launcher = ImageToolLauncher()
    launcher.show()
    sys.exit(app.exec_())
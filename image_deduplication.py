import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFileDialog, QListWidget, QListWidgetItem, QSlider, QMessageBox, QCheckBox, QComboBox,
                             QProgressBar, QTextEdit, QTreeWidget, QTreeWidgetItem, QSplitter, QGroupBox)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
import imagehash
from PIL import Image
import subprocess
import sys
import shutil
from datetime import datetime
from collections import defaultdict

class ImageDeduplicator:
    def __init__(self):
        pass

    def compute_hash(self, image_path, hash_method='phash'):
        """计算图像的哈希值"""
        try:
            image = Image.open(image_path)
            if hash_method == 'ahash':
                hash_value = imagehash.average_hash(image)
            elif hash_method == 'phash':
                hash_value = imagehash.phash(image)
            elif hash_method == 'dhash':
                hash_value = imagehash.dhash(image)
            elif hash_method == 'whash':
                hash_value = imagehash.whash(image)
            else:
                raise ValueError("不支持的哈希方法")
            return str(hash_value)
        except Exception as e:
            print(f"处理图片错误 {image_path}: {e}")
            return None

    def find_duplicate_groups(self, image_paths, hash_method='phash', threshold=5):
        """查找重复图片组"""
        hash_groups = defaultdict(list)
        
        for path in image_paths:
            img_hash = self.compute_hash(path, hash_method)
            if img_hash is None:
                continue
                
            # 检查是否与现有组匹配
            matched = False
            for existing_hash in list(hash_groups.keys()):
                hamming_distance = bin(int(img_hash, 16) ^ int(existing_hash, 16)).count("1")
                if hamming_distance <= threshold:
                    hash_groups[existing_hash].append(path)
                    matched = True
                    break
            
            if not matched:
                hash_groups[img_hash].append(path)
        
        # 只返回包含重复的组
        duplicate_groups = [group for group in hash_groups.values() if len(group) > 1]
        return duplicate_groups

    def find_duplicate_groups_by_sift(self, image_paths, ratio=0.7, min_matches=10):
        """使用SIFT特征匹配查找重复图片组"""
        # 实现SIFT分组逻辑
        # 由于SIFT实现较为复杂，这里简化处理，实际实现需要更复杂的逻辑
        duplicates = []
        sift = cv2.SIFT_create()
        matcher = cv2.BFMatcher()

        features = {}
        for path in image_paths:
            try:
                pil_image = Image.open(path).convert('L')
                img = np.array(pil_image)
                
                if img.dtype != np.uint8:
                    img = img.astype(np.uint8)
                    
                kp, des = sift.detectAndCompute(img, None)
                if des is not None:
                    features[path] = des
            except Exception as e:
                print(f"处理图片错误 {path}: {e}")
                continue

        # 简化的分组实现 - 实际应使用更复杂的分组算法
        processed = set()
        groups = []
        paths = list(features.keys())
        
        for i, path1 in enumerate(paths):
            if path1 in processed:
                continue
                
            group = [path1]
            des1 = features[path1]
            
            for j, path2 in enumerate(paths[i+1:], i+1):
                if path2 in processed:
                    continue
                    
                des2 = features[path2]
                try:
                    matches = matcher.knnMatch(des1, des2, k=2)
                    good_matches = []
                    for m, n in matches:
                        if m.distance < ratio * n.distance:
                            good_matches.append(m)

                    if len(good_matches) >= min_matches:
                        group.append(path2)
                        processed.add(path2)
                except Exception as e:
                    print(f"匹配错误 {path1} 和 {path2}: {e}")
                    continue
            
            if len(group) > 1:
                groups.append(group)
                processed.add(path1)
        
        return groups

class BatchFileCleaner:
    """批处理文件清理工具"""
    
    @staticmethod
    def generate_cleanup_bat(directory, files_to_clean):
        """生成清理批处理文件"""
        bat_path = os.path.join(directory, "cleanup_generated_files.bat")
        
        try:
            with open(bat_path, "w", encoding='utf-8') as bat_file:
                bat_file.write("@echo off\n")
                bat_file.write("chcp 65001 >nul\n")
                bat_file.write("setlocal enabledelayedexpansion\n")
                bat_file.write("title 图像查重工具 - 清理生成文件\n")
                bat_file.write("echo ============================================\n")
                bat_file.write("echo           图像查重工具 - 清理生成文件\n")
                bat_file.write("echo ============================================\n")
                bat_file.write("echo.\n")
                bat_file.write("echo 警告: 此操作将删除以下生成的文件!\n")
                bat_file.write("echo.\n")
                
                # 列出要删除的文件
                for file_info in files_to_clean:
                    bat_file.write(f"echo {file_info['path']}\n")
                
                bat_file.write("echo.\n")
                bat_file.write("set /p confirm=确认删除以上文件? (y/n): \n")
                bat_file.write("if /i \"!confirm!\" neq \"y\" (\n")
                bat_file.write("    echo 操作已取消\n")
                bat_file.write("    pause\n")
                bat_file.write("    exit /b\n")
                bat_file.write(")\n")
                bat_file.write("echo.\n")
                bat_file.write("echo 开始删除文件...\n")
                bat_file.write("echo.\n")
                
                # 初始化计数器
                bat_file.write("set /a deleted_count=0\n")
                bat_file.write("set /a error_count=0\n")
                bat_file.write("set /a not_found_count=0\n")
                
                # 删除文件
                for file_info in files_to_clean:
                    file_path = file_info['path']
                    description = file_info.get('description', '生成文件')
                    
                    bat_file.write(f'echo 删除: {description}\n')
                    bat_file.write(f'if exist "{file_path}" (\n')
                    bat_file.write(f'    del /f "{file_path}"\n')
                    bat_file.write(f'    if exist "{file_path}" (\n')
                    bat_file.write(f'        echo [错误] 无法删除: {description}\n')
                    bat_file.write(f'        set /a error_count+=1\n')
                    bat_file.write(f'    ) else (\n')
                    bat_file.write(f'        echo [成功] 已删除: {description}\n')
                    bat_file.write(f'        set /a deleted_count+=1\n')
                    bat_file.write(f'    )\n')
                    bat_file.write(f') else (\n')
                    bat_file.write(f'    echo [警告] 文件不存在: {description}\n')
                    bat_file.write(f'    set /a not_found_count+=1\n')
                    bat_file.write(f')\n')
                
                bat_file.write("echo.\n")
                bat_file.write("echo ============================================\n")
                bat_file.write("echo 清理完成总结:\n")
                bat_file.write("echo 成功删除: !deleted_count! 个文件\n")
                bat_file.write("echo 删除失败: !error_count! 个文件\n")
                bat_file.write("echo 文件不存在: !not_found_count! 个文件\n")
                bat_file.write("echo ============================================\n")
                bat_file.write("echo.\n")
                
                # 询问是否删除清理批处理自身
                bat_file.write("set /p delete_self=是否删除此清理批处理文件? (y/n): \n")
                bat_file.write("if /i \"!delete_self!\" equ \"y\" (\n")
                bat_file.write("    echo 正在删除清理批处理文件...\n")
                bat_file.write("    del /f \"%~f0\"\n")
                bat_file.write("    echo 清理完成，批处理文件已自删除\n")
                bat_file.write(") else (\n")
                bat_file.write("    echo 清理完成，批处理文件保留\n")
                bat_file.write(")\n")
                bat_file.write("pause\n")
            
            return bat_path
        except Exception as e:
            print(f"生成清理批处理文件错误: {e}")
            return None

class DeduplicationThread(QThread):
    """后台查重线程"""
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str)
    
    def __init__(self, deduplicator, image_paths, method, threshold):
        super().__init__()
        self.deduplicator = deduplicator
        self.image_paths = image_paths
        self.method = method
        self.threshold = threshold
        self.duplicate_groups = []
    
    def run(self):
        try:
            self.log_signal.emit("开始查重处理...")
            total = len(self.image_paths)
            
            if self.method == "感知哈希":
                self.duplicate_groups = self.deduplicator.find_duplicate_groups(
                    self.image_paths, 'phash', self.threshold)
            else:
                self.duplicate_groups = self.deduplicator.find_duplicate_groups_by_sift(
                    self.image_paths, ratio=0.7, min_matches=self.threshold)
            
            self.progress_signal.emit(100)
            self.result_signal.emit(self.duplicate_groups)
            self.log_signal.emit(f"查重完成，找到 {len(self.duplicate_groups)} 组重复图片")
            
        except Exception as e:
            self.log_signal.emit(f"查重过程出错: {e}")
            self.result_signal.emit([])

class ImageDeduplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageCC-图像查重工具 v2.0")
        self.setGeometry(100, 100, 1200, 800)
        self.deduplicator = ImageDeduplicator()
        self.batch_cleaner = BatchFileCleaner()
        self.image_paths = []
        self.duplicate_groups = []
        self.generated_files = []  # 记录生成的文件
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # 顶部按钮布局
        top_group = QGroupBox("操作")
        top_layout = QHBoxLayout()
        self.add_button = QPushButton("添加图片")
        self.add_button.clicked.connect(self.add_images)
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)
        self.detect_button = QPushButton("开始查重")
        self.detect_button.clicked.connect(self.detect_duplicates)
        self.export_button = QPushButton("开始清除")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        self.cleanup_button = QPushButton("清理生成文件")
        self.cleanup_button.clicked.connect(self.cleanup_generated_files)
        self.cleanup_button.setEnabled(False)

        top_layout.addWidget(self.add_button)
        top_layout.addWidget(self.clear_button)
        top_layout.addWidget(self.detect_button)
        top_layout.addWidget(self.export_button)
        top_layout.addWidget(self.cleanup_button)
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # 方法选择区域
        method_group = QGroupBox("查重设置")
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("查重方法:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["感知哈希", "SIFT特征匹配"])
        method_layout.addWidget(self.method_combo)

        # 参数设置
        method_layout.addWidget(QLabel("阈值:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 20)
        self.threshold_slider.setValue(5)
        method_layout.addWidget(self.threshold_slider)
        self.threshold_label = QLabel("5")
        self.threshold_slider.valueChanged.connect(lambda: self.threshold_label.setText(str(self.threshold_slider.value())))
        method_layout.addWidget(self.threshold_label)

        method_layout.addStretch()
        method_group.setLayout(method_layout)
        main_layout.addWidget(method_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 主内容区域
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 图片列表和预览
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("图片列表:"))
        self.image_list = QListWidget()
        self.image_list.setIconSize(QSize(64, 64))
        self.image_list.itemSelectionChanged.connect(self.preview_image)
        left_layout.addWidget(self.image_list, 3)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setText("图片预览")
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        left_layout.addWidget(preview_group, 2)
        
        left_widget.setLayout(left_layout)
        content_splitter.addWidget(left_widget)
        
        # 右侧面板 - 重复组和文件选择
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("重复组:"))
        
        # 重复组树形控件
        self.duplicate_tree = QTreeWidget()
        self.duplicate_tree.setHeaderLabels(["文件", "路径", "操作"])
        self.duplicate_tree.setColumnWidth(0, 200)
        self.duplicate_tree.setColumnWidth(1, 400)
        self.duplicate_tree.itemChanged.connect(self.on_selection_changed)
        right_layout.addWidget(self.duplicate_tree, 3)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.deselect_all_btn = QPushButton("全不选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_files)
        self.auto_select_btn = QPushButton("自动选择")
        self.auto_select_btn.clicked.connect(self.auto_select_files)
        action_layout.addWidget(self.select_all_btn)
        action_layout.addWidget(self.deselect_all_btn)
        action_layout.addWidget(self.auto_select_btn)
        action_layout.addStretch()
        right_layout.addLayout(action_layout)
        
        right_widget.setLayout(right_layout)
        content_splitter.addWidget(right_widget)
        
        content_splitter.setSizes([400, 600])
        main_layout.addWidget(content_splitter, 1)

        # 日志输出
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # 初始化工作线程
        self.worker_thread = None

    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.dds *.svg)"
        )
        if not files:
            return

        added_count = 0
        for file in files:
            if not os.path.exists(file):
                self.log_message(f"文件不存在: {file}")
                continue
                
            item = QListWidgetItem(os.path.basename(file))
            item.setData(Qt.UserRole, file)
            try:
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(pixmap))
                self.image_list.addItem(item)
                self.image_paths.append(file)
                added_count += 1
            except Exception as e:
                self.log_message(f"无法加载图片 {file}: {e}")

        if added_count > 0:
            self.log_message(f"成功添加 {added_count} 张图片")

    def clear_list(self):
        self.image_list.clear()
        self.duplicate_tree.clear()
        self.image_paths = []
        self.duplicate_groups = []
        self.preview_label.setText("图片预览")
        self.export_button.setEnabled(False)
        self.cleanup_button.setEnabled(False)
        self.log_message("已清空图片列表")

    def detect_duplicates(self):
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先添加图片")
            return

        # 禁用按钮，防止重复操作
        self.detect_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        method = self.method_combo.currentText()
        threshold = self.threshold_slider.value()

        # 创建工作线程
        self.worker_thread = DeduplicationThread(
            self.deduplicator, self.image_paths, method, threshold
        )
        
        # 连接信号
        self.worker_thread.progress_signal.connect(self.progress_bar.setValue)
        self.worker_thread.result_signal.connect(self.on_detection_complete)
        self.worker_thread.log_signal.connect(self.log_message)
        
        # 启动线程
        self.worker_thread.start()
        self.log_message("开始查重处理...")

    def on_detection_complete(self, duplicate_groups):
        """查重完成回调"""
        self.duplicate_groups = duplicate_groups
        self.duplicate_tree.clear()
        
        # 填充树形控件
        for i, group in enumerate(duplicate_groups):
            group_item = QTreeWidgetItem(self.duplicate_tree)
            group_item.setText(0, f"重复组 {i+1} ({len(group)} 个文件)")
            group_item.setFlags(group_item.flags() | Qt.ItemIsAutoTristate)
            
            for file_path in group:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, os.path.basename(file_path))
                file_item.setText(1, file_path)
                file_item.setCheckState(0, Qt.Unchecked)
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                
                try:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        file_item.setIcon(0, QIcon(pixmap))
                except Exception as e:
                    self.log_message(f"无法加载缩略图 {file_path}: {e}")
            
            group_item.setExpanded(True)

        # 恢复UI状态
        self.detect_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        if self.duplicate_groups:
            self.export_button.setEnabled(True)
            self.log_message(f"查重完成，找到 {len(self.duplicate_groups)} 组重复图片")
            QMessageBox.information(self, "完成", f"找到{len(self.duplicate_groups)}组重复图片")
        else:
            self.export_button.setEnabled(False)
            self.log_message("查重完成，未找到重复图片")
            QMessageBox.information(self, "完成", "未找到重复图片")

    def on_selection_changed(self, item, column):
        """处理用户选择变化"""
        if column != 0 or not item.parent():
            return
            
        # 确保至少选择一个文件
        parent = item.parent()
        selected_count = 0
        for i in range(parent.childCount()):
            if parent.child(i).checkState(0) == Qt.Checked:
                selected_count += 1
                
        if selected_count == 0:
            # 不允许全部取消选择，至少保留一个
            item.setCheckState(0, Qt.Checked)
            QMessageBox.warning(self, "警告", "每个重复组必须至少保留一个文件")

    def select_all_files(self):
        """选择所有文件"""
        for i in range(self.duplicate_tree.topLevelItemCount()):
            group_item = self.duplicate_tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                group_item.child(j).setCheckState(0, Qt.Checked)

    def deselect_all_files(self):
        """取消选择所有文件（但确保每个组至少保留一个）"""
        for i in range(self.duplicate_tree.topLevelItemCount()):
            group_item = self.duplicate_tree.topLevelItem(i)
            # 先全部取消选择
            for j in range(group_item.childCount()):
                group_item.child(j).setCheckState(0, Qt.Unchecked)
            # 然后选择第一个文件
            if group_item.childCount() > 0:
                group_item.child(0).setCheckState(0, Qt.Checked)

    def auto_select_files(self):
        """自动选择文件（基于文件大小和修改日期）"""
        for i in range(self.duplicate_tree.topLevelItemCount()):
            group_item = self.duplicate_tree.topLevelItem(i)
            
            # 收集文件信息
            file_info = []
            for j in range(group_item.childCount()):
                file_path = group_item.child(j).text(1)
                try:
                    size = os.path.getsize(file_path)
                    mtime = os.path.getmtime(file_path)
                    file_info.append((j, size, mtime))
                except:
                    file_info.append((j, 0, 0))
            
            # 按文件大小和修改日期排序（优先保留较大的和较新的文件）
            file_info.sort(key=lambda x: (x[1], x[2]), reverse=True)
            
            # 选择最好的文件，取消选择其他文件
            for idx, (j, _, _) in enumerate(file_info):
                if idx == 0:
                    group_item.child(j).setCheckState(0, Qt.Checked)
                else:
                    group_item.child(j).setCheckState(0, Qt.Unchecked)

    def get_selected_files_to_delete(self):
        """获取用户选择要删除的文件"""
        files_to_delete = []
        
        for i in range(self.duplicate_tree.topLevelItemCount()):
            group_item = self.duplicate_tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if file_item.checkState(0) == Qt.Unchecked:
                    files_to_delete.append(file_item.text(1))
        
        return files_to_delete

    def export_results(self):
        if not self.duplicate_groups:
            return

        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not directory:
            return

        try:
            # 获取用户选择要删除的文件
            files_to_delete = self.get_selected_files_to_delete()
            
            if not files_to_delete:
                QMessageBox.information(self, "信息", "没有选择要删除的文件")
                return

            # 保存结果文本文件
            txt_file = os.path.join(directory, "duplicates.txt")
            with open(txt_file, "w", encoding='utf-8') as f:
                f.write("重复图片组:\n")
                for i, group in enumerate(self.duplicate_groups):
                    f.write(f"\n组 {i+1}:\n")
                    for file_path in group:
                        f.write(f"  {file_path}\n")
                
                f.write(f"\n用户选择删除的文件 ({len(files_to_delete)} 个):\n")
                for file_path in files_to_delete:
                    f.write(f"  {file_path}\n")
            
            self.generated_files.append({
                'path': txt_file,
                'description': '重复结果文本文件'
            })

            # 询问用户是否立即删除文件
            reply = QMessageBox.question(
                self, "确认删除", 
                f"确定要删除 {len(files_to_delete)} 个重复文件吗？此操作不可恢复！",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                deleted_count = 0
                error_count = 0
                
                for file_path in files_to_delete:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            if not os.path.exists(file_path):
                                deleted_count += 1
                                self.log_message(f"已删除: {file_path}")
                            else:
                                error_count += 1
                                self.log_message(f"删除失败: {file_path}")
                        else:
                            self.log_message(f"文件不存在: {file_path}")
                    except Exception as e:
                        error_count += 1
                        self.log_message(f"删除错误 {file_path}: {e}")
                
                QMessageBox.information(
                    self, "删除完成", 
                    f"删除完成:\n成功删除: {deleted_count} 个文件\n删除失败: {error_count} 个文件"
                )
            else:
                self.log_message("用户取消了删除操作")

            self.cleanup_button.setEnabled(True)
            self.log_message(f"结果已导出到: {directory}")
            QMessageBox.information(self, "导出完成", f"结果已保存到{directory}")
            
        except Exception as e:
            self.log_message(f"导出失败: {e}")
            QMessageBox.critical(self, "导出错误", f"导出失败: {e}")

    def cleanup_generated_files(self):
        """清理生成的文件"""
        if not self.generated_files:
            QMessageBox.information(self, "信息", "没有需要清理的生成文件")
            return

        # 显示文件列表
        file_list = "\n".join([f["path"] for f in self.generated_files])
        reply = QMessageBox.question(
            self, "确认清理", 
            f"确定要删除以下生成的文件吗?\n\n{file_list}\n\n此操作不可恢复!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = 0
            error_count = 0
            
            for file_info in self.generated_files:
                file_path = file_info['path']
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        if not os.path.exists(file_path):
                            deleted_count += 1
                            self.log_message(f"已删除: {file_path}")
                        else:
                            error_count += 1
                            self.log_message(f"删除失败: {file_path}")
                    except Exception as e:
                        error_count += 1
                        self.log_message(f"删除错误 {file_path}: {e}")
                else:
                    self.log_message(f"文件不存在: {file_path}")
            
            # 清空记录
            self.generated_files.clear()
            self.cleanup_button.setEnabled(False)
            
            QMessageBox.information(
                self, "清理完成", 
                f"清理完成:\n成功删除: {deleted_count} 个文件\n删除失败: {error_count} 个文件"
            )

    def preview_image(self):
        current_item = self.image_list.currentItem()
        if not current_item:
            return

        image_path = current_item.data(Qt.UserRole)
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self.preview_label.setText("无法加载图片")
                return

            scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
        except Exception as e:
            self.preview_label.setText(f"加载图片出错: {e}")

    def preview_duplicate_pair(self, item):
        if not item.parent():
            return
            
        file_path = item.text(1)
        preview_win = QMainWindow(self)
        preview_win.setWindowTitle("图片预览")
        preview_win.setGeometry(200, 200, 600, 600)

        central_widget = QWidget()
        layout = QVBoxLayout()
        
        try:
            label = QLabel()
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(pixmap)
                label.setToolTip(file_path)
            layout.addWidget(label)
            
            info_label = QLabel(f"文件: {os.path.basename(file_path)}\n路径: {file_path}")
            layout.addWidget(info_label)
        except Exception as e:
            error_label = QLabel(f"加载图片出错: {e}")
            layout.addWidget(error_label)

        central_widget.setLayout(layout)
        preview_win.setCentralWidget(central_widget)
        preview_win.show()

if __name__ == "__main__":
    import sys
    if sys.platform.startswith('win'):
        import os
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
        
    app = QApplication(sys.argv)
    window = ImageDeduplicationController()
    window.show()
    sys.exit(app.exec_())
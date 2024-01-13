# 函数说明：将src目录下的文件每个目录随机选x个到目标目录下去。
# 文件过多时 缩减目标数量进行测试。

import os
import random
import shutil
from pathlib import Path

def random_copy(src_path, dst_path, num_files):
    # 遍历源目录下的所有子目录
    for root, dirs, files in os.walk(src_path):
        for dir in dirs:
            full_dir_path = os.path.join(root, dir)
            all_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(full_dir_path) for f in filenames]
            selected_files = random.sample(all_files, min(len(all_files), num_files))

            for file in selected_files:
                relative_path = os.path.relpath(file, src_path)
                dst_file_path = os.path.join(dst_path, relative_path)
                
                os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)
                shutil.copy(file, dst_file_path)

# # 使用示例
# src_directory = '/path/to/source'  # 源目录路径
# dst_directory = '/path/to/destination'  # 目标目录路径
# num_files_to_copy = 1000

# 使用示例
src_directory = '/Users/tyu/Downloads/THUCNews/'  # 源目录路径
dst_directory = '/Users/tyu/Downloads/THUCNews_simple/'  # 目标目录路径
num_files_to_copy = 1000


random_copy(src_directory, dst_directory, num_files_to_copy)

# 体育	娱乐	家居	彩票	房产	教育	时尚	时政	星座	游戏	社会	科技	股票	财经

import pandas as pd
import os

def read_txt_to_csv(folder_path, csv_file_path):
    data = {'label': [], 'txt': []}

    # 获取子目录列表
    _, subdirs, _ = next(os.walk(folder_path), (None, [], None))
    print(subdirs)
    print(folder_path)
    for subdir in subdirs:
        subdir_path = os.path.join(folder_path, subdir)
        print(subdir_path)
        for root, dirs, files in os.walk(subdir_path):
            for file in files:
                print(file)
                if file.endswith(".txt"):
                    file_path = os.path.join(root, file)
                    print(file_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        data['label'].append(subdir)  # 使用子目录名作为标签
                        data['txt'].append(text)

    df = pd.DataFrame(data)
    df.to_csv(csv_file_path, index=False)

# 使用示例
folder_path = '/Users/tyu/HW_work/Code_Proj23/testdata/THUCNews_simple/'  # TXT 文件所在的目录路径
csv_file_path = '/Users/tyu/HW_work/Code_Proj23/testdata/THUCNews_simple/data.csv'  # CSV 文件的保存路径

read_txt_to_csv(folder_path, csv_file_path)

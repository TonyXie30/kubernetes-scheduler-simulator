import os
import shutil
import json
import sys
import matplotlib.pyplot as plt
import numpy as np


def generate_pod_configs(target_path, json_str):
    # 确保目标路径存在，如果路径不为空先删除路径下文件
    if os.path.exists(target_path):
        for root, dirs, files in os.walk(target_path, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                shutil.rmtree(dir_path)
    else:
        os.makedirs(target_path)

    try:
        # 将JSON字符串解析为Python字典
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"错误:无法解析传入的JSON字符串: {json_str}")
        return

    for num, replicas in data.items():
        num = int(num)
        gpu_count = num
        # 生成文件名
        filename = os.path.join(target_path, f"gpu-rs-{num}.yaml")

        # 生成YAML内容
        yaml_content = f"""apiVersion: apps/v1
kind: ReplicaSet
metadata:
  labels:
    app: gpu-rs-{num}
  name: gpu-rs-{num}
  namespace: pai-gpu
  annotations:
    alibabacloud.com/gpu-milli: "1000"
    alibabacloud.com/gpu-count: "{gpu_count}"
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: gpu-deploy-{num}
  template:
    metadata:
      labels:
        app: gpu-deploy-{num}
    spec:
      containers:
      - image: tensorflow:latest
        name: main
        resources:
          limits:
            cpu: {4 * num}
            memory: {9216 * num}Mi
          requests:
            cpu: {4 * num}
            memory: {9216 * num}Mi
      hostNetwork: true
"""

        # 写入文件
        with open(filename, 'w') as f:
            f.write(yaml_content)

        print(f"Generated {filename}")

    return data


def plot_gpu_cdf(data):
    # 提取所有 pod 需求的 GPU 数目
    gpu_demands = []
    for num, replicas in data.items():
        gpu_demands.extend([int(num)] * replicas)

    # 对 GPU 需求进行排序
    gpu_demands.sort()

    # 计算 CDF
    n = len(gpu_demands)
    cdf = np.arange(1, n + 1) / n

    # 绘制 CDF 图
    plt.figure(figsize=(10, 6))
    plt.plot(gpu_demands, cdf * 100, marker='o', linestyle='-')
    plt.xlabel('GPU Requests of Pods', fontsize=20)
    plt.ylabel('CDF (%)', fontsize=20)
    plt.grid(True)
    plt.xticks(np.unique(gpu_demands))
    plt.tight_layout()

    # 设置横纵坐标刻度标签的字体大小
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)

    # 保存图片
    j = 1
    while True:
        save_dir = f'datas/test_group_{j}'
        if os.path.exists(save_dir) and os.listdir(save_dir):
            j += 1
        else:
            break

    # 创建目录
    os.makedirs(save_dir, exist_ok=True)

    # 保存图片
    save_path = os.path.join(save_dir, 'gpu_demand_cdf.png')
    plt.savefig(save_path, dpi=300)
    print(f"CDF 图已保存为 {save_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("请提供目标路径和 JSON 字符串作为参数")
        sys.exit(1)

    target_path = sys.argv[1]
    json_str = sys.argv[2]
    data = generate_pod_configs(target_path, json_str)

    if data:
        plot_gpu_cdf(data)


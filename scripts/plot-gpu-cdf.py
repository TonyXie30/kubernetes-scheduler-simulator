import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def calculate_average_in_group(group_dir):
    group_results = {
        "allo_dict": {},
        "quad_dict": {},
        "amnt_dict": {},
        "totl_dict": {}
    }
    file_count = 0

    for root, dirs, files in os.walk(group_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    for outer_key in group_results.keys():
                        if outer_key not in group_results:
                            group_results[outer_key] = {}
                        for inner_key in data[outer_key].keys():
                            if inner_key not in group_results[outer_key]:
                                group_results[outer_key][inner_key] = {}
                            for sub_key in data[outer_key][inner_key].keys():
                                if sub_key not in group_results[outer_key][inner_key]:
                                    group_results[outer_key][inner_key][sub_key] = 0
                                group_results[outer_key][inner_key][sub_key] += data[outer_key][inner_key][sub_key]
                file_count += 1

    for outer_key in group_results.keys():
        for inner_key in group_results[outer_key].keys():
            for sub_key in group_results[outer_key][inner_key].keys():
                group_results[outer_key][inner_key][sub_key] /= file_count

    return group_results


def extract_gpu_schedule(all_group_results):
    extracted_data_allo = []
    extracted_data_q2 = []
    extracted_data_frag = []

    for group_result in all_group_results:
        group_extracted_allo = {}
        group_extracted_q2 = {}
        group_extracted_frag = {}

        allo_dict = group_result["allo_dict"]
        quad_dict = group_result["quad_dict"]

        for key in ["Rw", "Rwo", "Fw", "Fwo"]:
            # 提取 allo_dict 中的 gpu 调度数据
            if "gpu_post_deschedule" in allo_dict[key]:
                group_extracted_allo[key] = allo_dict[key]["gpu_post_deschedule"]
            elif "gpu_init_schedule" in allo_dict[key]:
                group_extracted_allo[key] = allo_dict[key]["gpu_init_schedule"]
            else:
                group_extracted_allo[key] = 0

            # 提取 quad_dict 中的 q2_lack_gpu 数据
            if "q2_lack_gpu_post_deschedule" in quad_dict[key]:
                group_extracted_q2[key] = quad_dict[key]["q2_lack_gpu_post_deschedule"] 
            elif "q2_lack_gpu_init_schedule" in quad_dict[key]:
                group_extracted_q2[key] = quad_dict[key]["q2_lack_gpu_init_schedule"] 
            else:
                group_extracted_q2[key] = 0

            # 提取 quad_dict 中的 frag_gpu_milli 数据
            if "frag_gpu_milli_post_deschedule" in quad_dict[key]:
                group_extracted_frag[key] = quad_dict[key]["frag_gpu_milli_post_deschedule"] 
            elif "frag_gpu_milli_init_schedule" in quad_dict[key]:
                group_extracted_frag[key] = quad_dict[key]["frag_gpu_milli_init_schedule"] 
            else:
                group_extracted_frag[key] = 0

        extracted_data_allo.append(group_extracted_allo)
        extracted_data_q2.append(group_extracted_q2)
        extracted_data_frag.append(group_extracted_frag)

    return extracted_data_allo, extracted_data_q2, extracted_data_frag

def plot_line_chart(all_group_results, output_dir):
    folder_names = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    x_tick_values = [float(folder_name.split('_')[-1]) for folder_name in folder_names]
    x_tick_labels = [f"{value * 100:.0f}%" for value in x_tick_values]

    sorted_indices = np.argsort(x_tick_values)
    x_tick_values = [x_tick_values[i] for i in sorted_indices]
    x_tick_labels = [x_tick_labels[i] for i in sorted_indices]

    labels = ["Rwo", "Rw", "Fwo", "Fw"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a']

    # 计算最大数据占比
    max_percentage = max(x_tick_values) * 100
    # 确定横坐标刻度，以 10% 为单位
    tick_positions = [i / 100 for i in range(0, int(max_percentage) + 1, 10)]
    tick_labels = [f"{i}%" for i in range(0, int(max_percentage) + 1, 10)]

    for i, label in enumerate(labels):
        frag_gpu_milli_values = []
        for group_result in all_group_results:
            quad_dict = group_result["quad_dict"]
            if label in quad_dict:
                if "frag_gpu_milli_post_deschedule" in quad_dict[label]:
                    frag_gpu_milli_values.append(quad_dict[label]["frag_gpu_milli_post_deschedule"])
                elif "frag_gpu_milli_init_schedule" in quad_dict[label]:
                    frag_gpu_milli_values.append(quad_dict[label]["frag_gpu_milli_init_schedule"])
                else:
                    frag_gpu_milli_values.append(0)
            else:
                frag_gpu_milli_values.append(0)

        plt.plot(x_tick_values, frag_gpu_milli_values, label=label, marker='o', color=colors[i])

    plt.xlabel('Workload', fontsize=14)
    plt.ylabel('Frag GPU Milli Value(%)', fontsize=14)
    plt.title('Frag GPU Milli Comparison for Test Groups', fontsize=16)
    # 设置横坐标刻度
    plt.xticks(tick_positions, tick_labels, fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(fontsize=12, loc='upper left')

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'all_labels_frag_gpu_milli_line_chart.png')
    plt.savefig(output_path)
    plt.close()

from scipy.interpolate import interp1d

def plot_gpu_cdf(group_dir):
    file_paths = [
        os.path.join(group_dir, 'fgd', 'check', 'PostDeschedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'fgd', 'noncheck', 'InitSchedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'random', 'check', 'PostDeschedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'random', 'noncheck', 'InitSchedule', 'node-snapshot.csv')
    ]
    labels = ["Fw", "Fwo", "Rw", "Rwo"]
    colors = ['#3a923a', '#e1812c', '#3274a1', '#c03d3e']
    linestyles = ['-', '--', '-.', ':']  # 定义不同的线条样式
    num_interpolation_points = 500  # 插值点数

    for file_path, label, color in zip(file_paths, labels, colors):
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            gpu_usage_sums = []
            for index, row in df.iterrows():
                gpu_milli_left_sum = sum([row[f'gpu_milli_left_{i}'] for i in range(8)])
                gpu_usage_sums.append(gpu_milli_left_sum // 1000)

            gpu_usage_sums = np.array(gpu_usage_sums)
            sorted_gpu_usage = np.sort(gpu_usage_sums)
            cdf = np.arange(1, len(sorted_gpu_usage) + 1) / len(sorted_gpu_usage)

            # 进行插值以得到平滑曲线
            f = interp1d(sorted_gpu_usage, cdf, kind='linear')
            new_x = np.linspace(sorted_gpu_usage.min(), sorted_gpu_usage.max(), num_interpolation_points)
            new_y = f(new_x)

            # 绘制平滑曲线
            plt.plot(new_x, new_y, label=label, color=color,
                     linestyle=linestyles[labels.index(label)])
        else:
            print(f"文件 {file_path} 不存在，跳过。")

    plt.xlabel('Sum of GPU Milli Left (in units of 1000)')
    plt.ylabel('CDF')
    plt.title('GPU Usage CDF for Different Scenarios')
    plt.legend()

    output_path = os.path.join(group_dir, 'gpu_usage_cdf.png')
    plt.savefig(output_path)
    plt.close()

def plot_gpu_schedule(extracted_data, output_dir, plot_name):
    num_groups = len(extracted_data)
    bar_width = 0.2
    index = np.arange(num_groups)

    labels = ["Rwo", "Rw", "Fwo", "Fw"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a']
    hatches = ['\\', '/', '|', '+']

    # 从文件夹名字中提取百分比作为 X 轴标签
    folder_names = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    x_tick_values = [float(folder_name.split('_')[-1]) for folder_name in folder_names]
    x_tick_labels = [f"{value * 100:.0f}%" for value in x_tick_values]

    # 根据百分比从小到大排序
    sorted_indices = np.argsort(x_tick_values)
    x_tick_values = [x_tick_values[i] for i in sorted_indices]
    x_tick_labels = [x_tick_labels[i] for i in sorted_indices]
    extracted_data = [extracted_data[i] for i in sorted_indices]

    for i, label in enumerate(labels):
        values = [data[label] for data in extracted_data]
        plt.bar(index + i * bar_width, values, width=bar_width, label=label, color=colors[i],
                edgecolor='black',
                linewidth=1,
                hatch=hatches[i])

    plt.xlabel('Workload', fontsize=14)
    if plot_name == 'GPU Schedule':
        plt.ylabel('GPU Schedule Value', fontsize=14)
    elif plot_name == 'Q2 Lack GPU':
        plt.ylabel('Q2 Lack GPU Percentage (%)', fontsize=14)
    elif plot_name == 'Frag GPU Milli':
        plt.ylabel('Frag GPU Milli Percentage (%)', fontsize=14)
    # plt.title(f'{plot_name} Comparison for Test Groups', fontsize=16)
    plt.xticks(index + bar_width * (len(labels) - 1) / 2, x_tick_labels, fontsize=12)
    plt.yticks(fontsize=12)

    # 设置图例位置为左上角，且为 4 行 1 列布局
    plt.legend(fontsize=12, loc='upper left', ncol=num_groups)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{plot_name}_comparison.png')
    plt.savefig(output_path)
    plt.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("请提供数据目录路径和图像输出目录路径作为参数")
        sys.exit(1)

    data_directory = sys.argv[1]
    all_group_results = []
    test_groups = [os.path.join(data_directory, d) for d in os.listdir(data_directory) if os.path.isdir(os.path.join(data_directory, d))]
    for test_group in test_groups:
        group_result = calculate_average_in_group(test_group)
        all_group_results.append(group_result)
        plot_gpu_cdf(test_group)
    extracted_data_allo, extracted_data_q2, extracted_data_frag = extract_gpu_schedule(all_group_results)
    plot_line_chart(all_group_results,data_directory)
    plot_gpu_schedule(extracted_data_allo, data_directory, 'GPU Schedule')
    plot_gpu_schedule(extracted_data_q2, data_directory, 'Q2 Lack GPU')
    plot_gpu_schedule(extracted_data_frag, data_directory, 'Frag GPU Milli')

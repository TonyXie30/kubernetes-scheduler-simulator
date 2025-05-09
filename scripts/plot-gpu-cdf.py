import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

def calculate_average_in_group(group_dir):
    group_results = {
        "allo_dict": {},
        "quad_dict": {},
        "amnt_dict": {},
        "totl_dict": {}
    }
    file_count = 0

    for root, _, files in os.walk(group_dir):  # 忽略未使用的 dirs 变量
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

        for key in ["Random+checkpoint", "Random", "FGD+checkpoint", "FGD", "BestFit+checkpoint", "BestFit"]:
            # 提取 allo_dict 中的 gpu 调度数据
            if "gpu_post_deschedule" in allo_dict[key]:
                group_extracted_allo[key] = allo_dict[key]["milli_gpu_post_deschedule"]
            elif "gpu_init_schedule" in allo_dict[key]:
                group_extracted_allo[key] = allo_dict[key]["milli_gpu_init_schedule"]
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

    labels = ["Random", "Random+checkpoint", "BestFit", "BestFit+checkpoint", "FGD", "FGD+checkpoint"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a', '#964b00', '#8064a2']

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

def plot_gpu_cdf(group_dir):
    file_paths = [
        os.path.join(group_dir, 'fgd', 'check', 'PostDeschedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'fgd', 'noncheck', 'InitSchedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'random', 'check', 'PostDeschedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'random', 'noncheck', 'InitSchedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'bestfit', 'check', 'PostDeschedule', 'node-snapshot.csv'),
        os.path.join(group_dir, 'bestfit', 'noncheck', 'InitSchedule', 'node-snapshot.csv')
    ]
    labels = ["Random", "Random+checkpoint", "BestFit", "BestFit+checkpoint", "FGD", "FGD+checkpoint"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a', '#964b00', '#8064a2']
    linestyles = ['-', '--', '-.', ':', '-', '--']
    num_interpolation_points = 500  # 插值点数

    for file_path, label, color in zip(file_paths, labels, colors):
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            gpu_usage_sums = []
            for _, row in df.iterrows():  # 忽略未使用的 index 变量
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
    labels = ["Random", "Random+checkpoint", "BestFit", "BestFit+checkpoint", "FGD", "FGD+checkpoint"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a', '#964b00', '#8064a2']
    hatches = ['\\', '/', '|', '+', 'x', 'o']

    bar_width = 0.8
    index = np.arange(len(labels))

    for group_idx, data in enumerate(extracted_data):
        values = [data[label] for label in labels]

        plt.figure()
        bars = plt.bar(index, values, width=bar_width, label=labels, color=colors,
                       edgecolor='black',
                       linewidth=1,
                       hatch=hatches)

        # 在每个柱子上标注数值
        for bar in bars:
            height = bar.get_height()
            plt.annotate(f'{height:.2f}',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),  # 3 points vertical offset
                         textcoords="offset points",
                         ha='center', va='bottom',
                         fontsize=10)

        plt.xlabel('Scheduling Method', fontsize=14)
        if plot_name == 'GPU Schedule':
            plt.ylabel('Allocated GPU Value (%)', fontsize=14)
        elif plot_name == 'Q2 Lack GPU':
            plt.ylabel('Lack GPU Percentage (%)', fontsize=14)
        elif plot_name == 'Frag GPU Milli':
            plt.ylabel('Frag GPU Value (%)', fontsize=14)
        plt.title(f'Average Frag Value Comparison', fontsize=16)
        # plt.xticks(index, labels, fontsize=12, rotation=45)
        plt.yticks(fontsize=12)

        # 设置图例位置为右上角
        plt.legend(fontsize=12)

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'{plot_name}_comparison_group_{group_idx + 1}.png')
        plt.savefig(output_path)
        plt.close()


def plot_new_line_charts(extracted_data_allo, extracted_data_frag, test_groups, output_dir):
    labels = ["Random", "Random+checkpoint", "BestFit", "BestFit+checkpoint", "FGD", "FGD+checkpoint"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a', '#964b00', '#8064a2']
    linestyles = ['-.', ':', '-.', ':', '-.', ':']  # 与 plot_gpu_cdf 中的线条样式对应
    # 假设 test_groups 目录名包含比例信息，提取并排序
    x_percentages = [float(os.path.basename(group).split('_')[-1]) * 100 for group in test_groups]
    sorted_indices = np.argsort(x_percentages)
    sorted_test_groups = [test_groups[i] for i in sorted_indices]
    x_labels = ["80%", "90%", "100%", "110%"]

    # 设置图片大小，与前面图形保持一致
    plt.rcParams['figure.figsize'] = (10, 6)

    def plot_with_horizontal_and_vertical_lines(data, ylabel, title, output_path):
        all_values = [value for sublist in data for value in sublist.values()]
        min_value = min(all_values)
        max_value = max(all_values)
        # 确定水平参考线的间隔，这里设置为 10，可按需调整
        step = 10
        # 计算合适的参考线起始值
        start = int(min_value // step) * step
        end = int(max_value // step + 1) * step

        plt.figure()
        # 添加水平参考线
        for y in range(start, end + step, step):
            plt.axhline(y=y, color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        # 添加垂直参考线
        for x_label in x_labels:
            x_index = x_labels.index(x_label)
            plt.axvline(x=x_index, color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        for i, label in enumerate(labels):
            sorted_values = [data[i][label] for i in sorted_indices]
            # 增加 linewidth 参数，将线条加粗，这里设置为 2，可按需调整
            plt.plot(x_labels, sorted_values, label=label, marker='o', color=colors[i], linestyle=linestyles[i], linewidth=4)
        plt.xlabel('Workload', fontsize=16)
        plt.ylabel(ylabel, fontsize=16)
        plt.title(title, fontsize=16)
        plt.xticks(rotation=45, fontsize=14)
        plt.yticks(fontsize=14)
        plt.legend(fontsize=14)

        # 自动调整布局
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    # 绘制 GPU Schedule 折线图
    plot_with_horizontal_and_vertical_lines(extracted_data_allo, 'GPU Schedule Value (%)', 'GPU Schedule Value Change', os.path.join(output_dir, 'gpu_schedule_change_line_chart.png'))
    # 绘制 Frag GPU Milli 折线图
    plot_with_horizontal_and_vertical_lines(extracted_data_frag, 'Frag GPU Value (%)', 'Frag GPU Value Change', os.path.join(output_dir, 'frag_gpu_milli_change_line_chart.png'))

def plot_grouped_bar_charts(extracted_data_allo, extracted_data_frag, test_groups, output_dir):
    labels = ["Random", "Random+checkpoint", "BestFit", "BestFit+checkpoint", "FGD", "FGD+checkpoint"]
    colors = ['#c03d3e', '#3274a1', '#e1812c', '#3a923a', '#964b00', '#8064a2']
    hatches = ['\\', '/', '|', '+', 'x', 'o']

    # 假设 test_groups 目录名包含比例信息，提取并排序
    x_percentages = [float(os.path.basename(group).split('_')[-1]) * 100 for group in test_groups]
    sorted_indices = np.argsort(x_percentages)
    sorted_test_groups = [test_groups[i] for i in sorted_indices]
    x_labels = ["20%", "40%", "60%", "80%"]

    # 设置图片大小，与前面图形保持一致
    plt.rcParams['figure.figsize'] = (10, 6)

    def plot_single_grouped_bar(data, ylabel, title, output_path):
        num_groups = len(x_labels)
        num_bars_per_group = len(labels)
        bar_width = 0.8 / num_bars_per_group
        index = np.arange(num_groups)
        bars = []

        for i, label in enumerate(labels):
            sorted_values = [data[j][label] for j in sorted_indices]
            bar = plt.bar(index + i * bar_width, sorted_values, width=bar_width, label=label, color=colors[i],
                          edgecolor='black', linewidth=1, hatch=hatches[i])
            bars.append(bar)

        # 为每个 group 的最后一个柱状图添加数值标注
        for group_idx in range(num_groups):
            last_bar = bars[-1][group_idx]
            height = last_bar.get_height()
            plt.annotate(f'{height:.2f}',
                         xy=(last_bar.get_x() + last_bar.get_width() / 2, height),
                         xytext=(0, 3),  # 3 points vertical offset
                         textcoords="offset points",
                         ha='center', va='bottom',
                         fontsize=12)

        plt.xlabel('Workload', fontsize=16)
        plt.ylabel(ylabel, fontsize=16)
        plt.title(title, fontsize=16)
        plt.xticks(index + (num_bars_per_group - 1) * bar_width / 2, x_labels, fontsize=14, rotation=45)
        plt.yticks(fontsize=14)
        plt.legend(fontsize=14, loc='upper right')

        # 自动调整布局
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    # 绘制 GPU Schedule 分组柱状图
    plot_single_grouped_bar(extracted_data_allo, 'Allocated GPU Value (%)', 'GPU Schedule Value Comparison for Test Groups',
                            os.path.join(output_dir, 'gpu_schedule_grouped_bar_chart.png'))
    # 绘制 Frag GPU Milli 分组柱状图
    plot_single_grouped_bar(extracted_data_frag, 'Frag GPU Value (%)', 'Frag GPU Value Comparison for Test Groups',
                            os.path.join(output_dir, 'frag_gpu_milli_grouped_bar_chart.png'))


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
    plot_line_chart(all_group_results, data_directory)
    plot_gpu_schedule(extracted_data_allo, data_directory, 'GPU Schedule')
    plot_gpu_schedule(extracted_data_q2, data_directory, 'Q2 Lack GPU')
    plot_gpu_schedule(extracted_data_frag, data_directory, 'Frag GPU Milli')
    plot_new_line_charts(extracted_data_allo, extracted_data_frag, test_groups, data_directory)
    plot_grouped_bar_charts(extracted_data_allo, extracted_data_frag, test_groups, data_directory)

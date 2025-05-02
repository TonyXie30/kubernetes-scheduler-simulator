import os
import json
import matplotlib.pyplot as plt
import numpy as np


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
                group_extracted_q2[key] = quad_dict[key]["q2_lack_gpu_post_deschedule"] * 100
            elif "q2_lack_gpu_init_schedule" in quad_dict[key]:
                group_extracted_q2[key] = quad_dict[key]["q2_lack_gpu_init_schedule"] * 100
            else:
                group_extracted_q2[key] = 0

            # 提取 quad_dict 中的 frag_gpu_milli 数据
            if "frag_gpu_milli_post_deschedule" in quad_dict[key]:
                group_extracted_frag[key] = quad_dict[key]["frag_gpu_milli_post_deschedule"] * 100
            elif "frag_gpu_milli_init_schedule" in quad_dict[key]:
                group_extracted_frag[key] = quad_dict[key]["frag_gpu_milli_init_schedule"] * 100
            else:
                group_extracted_frag[key] = 0

        extracted_data_allo.append(group_extracted_allo)
        extracted_data_q2.append(group_extracted_q2)
        extracted_data_frag.append(group_extracted_frag)

    return extracted_data_allo, extracted_data_q2, extracted_data_frag


def plot_gpu_schedule(extracted_data, output_dir, plot_name):
    num_groups = len(extracted_data)
    bar_width = 0.2
    index = np.arange(num_groups)

    labels = ["Rw", "Rwo", "Fw", "Fwo"]
    colors = ['#3274a1', '#c03d3e', '#3a923a', '#e1812c']
    hatches = ['/', '\\', '+', '|']

    for i, label in enumerate(labels):
        values = [data[label] for data in extracted_data]
        plt.bar(index + i * bar_width, values, width=bar_width, label=label, color=colors[i],
                edgecolor='black',
                linewidth=1,
                hatch=hatches[i])

    plt.xlabel('Test Group', fontsize=14)
    if plot_name == 'GPU Schedule':
        plt.ylabel('GPU Schedule Value', fontsize=14)
    elif plot_name == 'Q2 Lack GPU':
        plt.ylabel('Q2 Lack GPU Percentage (%)', fontsize=14)
    elif plot_name == 'Frag GPU Milli':
        plt.ylabel('Frag GPU Milli Percentage (%)', fontsize=14)
    plt.title(f'{plot_name} Comparison for Test Groups', fontsize=16)
    plt.xticks(index + bar_width * (len(labels) - 1) / 2, [f'test_group_{i + 1}' for i in range(num_groups)],
               fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(fontsize=12)

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

    extracted_data_allo, extracted_data_q2, extracted_data_frag = extract_gpu_schedule(all_group_results)

    plot_gpu_schedule(extracted_data_allo, data_directory, 'GPU Schedule')
    plot_gpu_schedule(extracted_data_q2, data_directory, 'Q2 Lack GPU')
    plot_gpu_schedule(extracted_data_frag, data_directory, 'Frag GPU Milli')

import os
import subprocess
import json
import random
import multiprocessing


# # 执行 go mod vendor 和 make 命令
# try:
#     subprocess.run(['go', 'mod','vendor'], check=True)
#     subprocess.run(['make'], check=True)
# except subprocess.CalledProcessError as e:
#     print(f"Error occurred while running go mod vendor or make: {e}")
#     exit(1)


# 蒙特卡洛模拟生成负载配置
def monte_carlo_load_generation():
    all_loads = []
    target_percentages = [0.4]

    for percentage in target_percentages:
        # 初始化负载配置
        load = {str(i): random.randint(10, 100) for i in range(1, 8)}
        # 计算其他卡数任务的总 GPU 需求
        other_gpu_demand = sum(int(key) * value for key, value in load.items())
        # 计算 8 卡任务的数量
        eight_gpu_demand = other_gpu_demand * percentage / (1 - percentage)
        eight_gpu_count = int(eight_gpu_demand / 8)
        load["8"] = eight_gpu_count
        all_loads.append(load)
    return all_loads

# def monte_carlo_load_generation(num_simulations=50, max_increase=30):
#     all_loads = []
#     load = {
#         "1": 10,
#         "2": 10,
#         "3": 10,
#         "4": 10,
#         "5": 10,
#         "6": 10,
#         "7": 10,
#         "8": 100
#     }
#     # for _ in range(num_simulations):
#     #     # 初始化一个字典，键为 1 到 8，值初始为 0
#     #     load = {str(i): 10 for i in range(1, 9)}
#     #     # 随机生成总任务数量，范围在 10 到 100 之间
#     #     total_tasks = random.randint(10, 100)
#     #     for _ in range(total_tasks):
#     #         # 随机选择一个 1 到 8 之间的卡数
#     #         gpu_num = str(random.randint(1, 8))
#     #         load[gpu_num] += 1
#     all_loads.append(load)        
#     return all_loads



# 单个模拟任务的函数
def run_simulation(j, loads):
    # 定义节点数量和每个节点的 GPU 数量
    node_cnt = 500
    gpu_per_node = 8
    total_gpus = node_cnt * gpu_per_node

    current_load = loads[j - 1]

    # 计算负载占比
    total_pod_gpu_demand = sum(int(key) * value for key, value in current_load.items())
    workload_ratio = round(total_pod_gpu_demand / total_gpus, 2)

    # 检查 datas/ 目录是否存在
    os.makedirs(f'datas/test_group_{j}_{workload_ratio}', exist_ok=True)
    os.makedirs(f'datas/test_group_{j}_{workload_ratio}/cluster', exist_ok=True)
    os.makedirs(f'datas/test_group_{j}_{workload_ratio}/cfg', exist_ok=True)
    os.makedirs(f'tmp/test_group_{j}_{workload_ratio}', exist_ok=True)  # 用于存储输出文件

    # 生成 pod 配置并执行实验
    pod_generate_script_path = "scripts/generate_pod_config.py"
    pod_target_path = f"datas/test_group_{j}_{workload_ratio}/cluster"
    running_script_path = "scripts/running_experiments.py"
    pod_plot_output_path = f'tmp/test_group_{j}_{workload_ratio}'
    if not os.path.isfile(pod_generate_script_path):
        print(f"Python script {pod_generate_script_path} not found.")
        exit(1)
    if not os.path.isfile(running_script_path):
        print(f"Python script {running_script_path} not found.")
        exit(1)
    # 调用 Python 脚本生成 pod 配置
    try:
        subprocess.run(['python3', pod_generate_script_path, pod_target_path, json.dumps(current_load), pod_plot_output_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running pod generation script: {e}")
        exit(1)

    # 生成节点配置
    node_generate_script_path = "scripts/generate_node_config.py"
    node_target_path = f"datas/test_group_{j}_{workload_ratio}/cluster"
    if not os.path.isfile(node_generate_script_path):
        print(f"Python script {node_generate_script_path} not found.")
        exit(1)
    try:
        subprocess.run(['python3', node_generate_script_path, node_target_path, str(node_cnt)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running node generation script: {e}")
        exit(1)
    
    for i in range(5):
        running_target_path = f"tmp/test_group_{i}_{workload_ratio}"
        for _ in range(10):
            # 执行实验
            try:
                subprocess.run(['python3', running_script_path, running_target_path, json.dumps(current_load), f"datas/test_group_{j}_{workload_ratio}/cfg", f'datas/test_group_{j}_{workload_ratio}/cluster',str(i*0.2)])
            except subprocess.CalledProcessError as e:
                print(f"Error occurred while running running_experiments script: {e}")
                exit(1)


if __name__ == "__main__":
    # 获取模拟次数
    simulation_count = 1
    loads = monte_carlo_load_generation()
    run_simulation(1, loads)
    # 创建进程池
    # pool = multiprocessing.Pool()

    # # 并行执行模拟任务
    # jobs = [pool.apply_async(run_simulation, args=(j, loads)) for j in range(1, simulation_count + 1)]

    # # 关闭进程池，不再接受新的任务
    # pool.close()
    # # 等待所有进程完成任务
    # pool.join()

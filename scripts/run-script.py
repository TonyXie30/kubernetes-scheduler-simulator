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
def monte_carlo_load_generation(num_simulations=10, max_increase=30):
    initial_load = {str(i): 10 for i in range(1, 9)}
    all_loads = []
    all_loads.append(initial_load)
    for _ in range(num_simulations-1):
        new_load = {}
        for key, value in initial_load.items():
            if random.random() < 0.5:
                increase = random.randint(1, max_increase)
                new_load[key] = value + increase
            else:
                new_load[key] = value
        all_loads.append(new_load)
        initial_load = new_load
    return all_loads


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
    
    for _ in range(1):
        running_target_path = f"tmp/test_group_{j}_{workload_ratio}"
        # 执行实验
        try:
            subprocess.run(['python3', running_script_path, running_target_path, json.dumps(current_load), f"datas/test_group_{j}_{workload_ratio}/cfg", f'datas/test_group_{j}_{workload_ratio}/cluster'])
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running running_experiments script: {e}")
            exit(1)


if __name__ == "__main__":
    # 获取模拟次数
    simulation_count = 1
    loads = monte_carlo_load_generation(simulation_count)

    # 创建进程池
    pool = multiprocessing.Pool()

    # 并行执行模拟任务
    jobs = [pool.apply_async(run_simulation, args=(j, loads)) for j in range(1, simulation_count + 1)]

    # 关闭进程池，不再接受新的任务
    pool.close()
    # 等待所有进程完成任务
    pool.join()

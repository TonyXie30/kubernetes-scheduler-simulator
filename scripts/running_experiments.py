#!/usr/bin/env python3
import json
import sys
import re
import subprocess
import os
import concurrent.futures
import uuid
import yaml
import numpy as np

def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def log_to_dict(content: str):
    ALLO_KEYS = ['MilliCpu', 'Memory', 'Gpu', 'MilliGpu']
    QUAD_KEYS = ["q1_lack_both", 'q2_lack_gpu', 'q3_satisfied', 'q4_lack_cpu', 'xl_satisfied', 'xr_lack_cpu',
                 'no_access', "frag_gpu_milli"]

    NUM_CLUSTER_ANALYSIS_LINE = 16
    counter = 0
    allo_dict = {}
    quad_dict = {}
    amnt_dict = {}
    totl_dict = {}

    for line in content.split('\n'):
        INFOMSG = "level=info msg="
        if INFOMSG not in line:
            continue
        line = line.split(INFOMSG)[1]
        line = line[1:-2]  # get rid of " and \n"

        if 'Cluster Analysis' in line:
            tag = line.split(')')[0].split('(')[1]
            counter += 1
        if 0 < counter <= NUM_CLUSTER_ANALYSIS_LINE:
            counter = 0 if counter == NUM_CLUSTER_ANALYSIS_LINE else counter + 1

            line = line.strip()
            item = line.split(":")
            if len(item) <= 1:
                continue

            key, value = item[0].strip(), item[1].strip()
            if key in ALLO_KEYS:
                ratio = float(value.split('%')[0])
                allo_dict[camel_to_snake(key + tag)] = ratio
                amount = float(value.split('(')[1].split('/')[0])
                amnt_dict[camel_to_snake(key + 'Amount' + tag)] = amount

                total = float(value.split(')')[0].split('/')[1])
                totl_dict[camel_to_snake(key + 'Total')] = total  # update without tag
            elif key in QUAD_KEYS:
                quad_dict[camel_to_snake(key + tag)] = float(value.split('(')[1].split('%')[0].strip())

    return allo_dict, quad_dict, amnt_dict, totl_dict


def run_command(cmd_info):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    name = cmd_info["name"]
    args = cmd_info["args"]
    log_file = os.path.join(log_dir, f"{name}_{os.popen('date +%Y%m%d%H%M%S').read().strip()}.log")

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout + result.stderr

        # 将输出写入日志文件
        with open(log_file, "w") as f:
            f.write(output)

        return name, log_to_dict(output)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {' '.join(args)}: {e.stderr}")
        sys.exit(1)

def generate_schedule_cfg(schedule_type):
    schedule_plugin_name = ''
    gpu_select_method = ''
    if schedule_type == 'random':
        schedule_plugin_name = "RandomScore"
        gpu_select_method = "random"
    elif schedule_type == "fgd":
        schedule_plugin_name = "FGDScore"
        gpu_select_method = "FGDScore"
    elif schedule_type == "bestfit":
        schedule_plugin_name = "BestFitScore"
        gpu_select_method = "best"
    else:
        print("Wrong schedule type")
        sys.exit(1)

    if gpu_select_method != "random":
        pre_score_enabled = "null"
    else:
        pre_score_enabled = """
      - name: RandomScore"""

    return f'''apiVersion: kubescheduler.config.k8s.io/v1beta1
kind: KubeSchedulerConfiguration
percentageOfNodesToScore: 100
profiles:
- pluginConfig:
  - args:
      dimExtMethod: share
      normMethod: max
    name: {schedule_plugin_name}
  - args:
      dimExtMethod: share
      gpuSelMethod: {gpu_select_method}
      normMethod: max
    name: Open-Gpu-Share
  plugins:
    bind:
      disabled:
      - name: DefaultBinder
      enabled:
      - name: Simon
    filter:
      enabled:
      - name: Open-Gpu-Share
    preScore:
      disabled:
      - name: RandomScore
      enabled: {pre_score_enabled}
    reserve:
      enabled:
      - name: Open-Gpu-Share
    score:
      disabled:
      - name: RandomScore
      - name: DotProductScore
      - name: GpuClusteringScore
      - name: GpuPackingScore
      - name: BestFitScore
      - name: FGDScore
      - name: ImageLocality
      - name: NodeAffinity
      - name: PodTopologySpread
      - name: TaintToleration
      - name: NodeResourcesBalancedAllocation
      - name: InterPodAffinity
      - name: NodeResourcesLeastAllocated
      - name: NodePreferAvoidPods
      enabled:
      - name: {schedule_plugin_name}
        weight: 1000
  schedulerName: simon-scheduler
'''

def kl_divergence(p, q):
    """
    计算两个概率分布 p 和 q 之间的 KL 散度。
    :param p: 实际的概率分布
    :param q: 生成的概率分布
    :return: KL 散度值
    """
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    p = p / np.sum(p)
    q = q / np.sum(q)
    return np.sum(np.where(p != 0, p * np.log(p / q), 0))

def generate_pod_cfg(pod_distribution, difference):
    pod_distribution = json.loads(pod_distribution)
    total = sum(pod_distribution.values())
    actual_ratios = np.array([value / total for value in pod_distribution.values()])

    target_kl = float(difference)
    while True:
        # 随机生成新的分布
        new_distribution = np.random.rand(len(pod_distribution))
        new_ratios = new_distribution / np.sum(new_distribution)
        current_kl = kl_divergence(actual_ratios, new_ratios)
        if abs(current_kl - target_kl) < 0.01:  # 允许一定的误差范围
            break

    # 将 numpy 数组元素转换为原生 Python 浮点数
    new_ratios = [float(ratio) for ratio in new_ratios]
    new_ratios_dict = {key: ratio for key, ratio in zip(pod_distribution.keys(), new_ratios)}

    # 更新 YAML 配置结构
    yaml_config = {
        "gpuPodRatios": new_ratios_dict
    }

    yaml_string = yaml.dump(yaml_config, default_flow_style=False)

    return yaml_string


def generate_cluster_cfg(cluster_path:str,export_path:str,checkpointOrNot:bool,schedule_type:str):
    snapshot_export_path = os.path.join(export_path,schedule_type,"check" if checkpointOrNot else "noncheck")
    os.makedirs(snapshot_export_path,exist_ok=True)
    return f"""apiVersion: simon/v1alpha1
kind: Config
metadata:
  name: simon-openb-config
spec:
  appList: null
  cluster:
    customConfig: {cluster_path}
  customConfig:
    descheduleConfig:
      ratio: {'0.99' if checkpointOrNot else '0.0'}
      policy: "binPacking"
    exportConfig:
      nodeSnapshotCSVFilePrefix: {snapshot_export_path}
      podSnapshotYamlFilePrefix: {snapshot_export_path}
    newWorkloadConfig: null
    shufflePod: true
    typicalPodsConfig:
      gpuResWeight: 0
      isInvolvedCpuPods: false
      podPopularityThreshold: 95
    workloadInflationConfig:
      ratio: 1
      seed: 233
    workloadTuningConfig:
      ratio: 1.1
      seed: 42
  newNode: example/newnode/gpushare
"""

def save_yaml_files(input_cfg_path, schedule_type, pod_distribution, cluster_path, export_path, checkpointOrNot,difference):
    # 确保目录存在
    if not os.path.exists(input_cfg_path):
        os.makedirs(input_cfg_path)

    # 生成调度配置
    schedule_yaml = generate_schedule_cfg(schedule_type)
    schedule_file_path = os.path.join(input_cfg_path, "test-scheduler-config.yaml")
    with open(schedule_file_path, 'w') as f:
        f.write(schedule_yaml)

    # 生成 Pod 配置
    pod_yaml = generate_pod_cfg(pod_distribution,difference)
    pod_file_path = os.path.join(input_cfg_path, "test-pod-distribution-config.yaml")
    with open(pod_file_path, 'w') as f:
        f.write(pod_yaml)

    # 生成集群配置
    cluster_yaml = generate_cluster_cfg(cluster_path, export_path, checkpointOrNot, schedule_type)
    cluster_file_path = os.path.join(input_cfg_path, "test-cluster-config.yaml")
    with open(cluster_file_path, 'w') as f:
        f.write(cluster_yaml)

    print(f"Generated YAML files saved to {input_cfg_path}")
    
if __name__ == "__main__":
    os.makedirs('tmp', exist_ok=True)
    if len(sys.argv) != 6:
        print("Provide 5 arg: output file path and pod distribution and the path of generating config and cluster path and difference among pod distribution config")
    
    output_file_path = sys.argv[1]
    pod_distribution = sys.argv[2]
    input_cfg_path = sys.argv[3]
    cluster_path = sys.argv[4]
    difference = sys.argv[5]

    # Random with deschedule
    save_yaml_files(os.path.join(input_cfg_path,"Random-with-deschedule-config"),"random",pod_distribution,cluster_path,output_file_path,True,difference)
    save_yaml_files(os.path.join(input_cfg_path,"Random-without-deschedule-config"),"random",pod_distribution,cluster_path,output_file_path,False,difference)
    save_yaml_files(os.path.join(input_cfg_path,"FGD-with-deschedule-config"),"fgd",pod_distribution,cluster_path,output_file_path,True,difference)
    save_yaml_files(os.path.join(input_cfg_path,"FGD-without-deschedule-config"),"fgd",pod_distribution,cluster_path,output_file_path,False,difference)
    save_yaml_files(os.path.join(input_cfg_path,"BestFit-with-deschedule-config"),"bestfit",pod_distribution,cluster_path,output_file_path,True,difference)
    save_yaml_files(os.path.join(input_cfg_path,"BestFit-without-deschedule-config"),"bestfit",pod_distribution,cluster_path,output_file_path,False,difference)

    # 原有的命令参数
    commands = [
    {
        "name": "Random+checkpoint",
        "args": [
            "bin/simon", "apply", "--extended-resources", "gpu",
            "-f", os.path.join(input_cfg_path, "Random-with-deschedule-config", "test-cluster-config.yaml"),
            "-s", os.path.join(input_cfg_path, "Random-with-deschedule-config", "test-scheduler-config.yaml"),
            "-p", os.path.join(input_cfg_path, "Random-with-deschedule-config", "test-pod-distribution-config.yaml")
        ]
    },
    {
        "name": "Random",
        "args": [
            "bin/simon", "apply", "--extended-resources", "gpu",
            "-f", os.path.join(input_cfg_path, "Random-without-deschedule-config", "test-cluster-config.yaml"),
            "-s", os.path.join(input_cfg_path, "Random-without-deschedule-config", "test-scheduler-config.yaml"),
            "-p", os.path.join(input_cfg_path, "Random-without-deschedule-config", "test-pod-distribution-config.yaml")
        ]
    },
    {
        "name": "FGD+checkpoint",
        "args": [
            "bin/simon", "apply", "--extended-resources", "gpu",
            "-f", os.path.join(input_cfg_path, "FGD-with-deschedule-config", "test-cluster-config.yaml"),
            "-s", os.path.join(input_cfg_path, "FGD-with-deschedule-config", "test-scheduler-config.yaml"),
            "-p", os.path.join(input_cfg_path, "FGD-with-deschedule-config", "test-pod-distribution-config.yaml")
        ]
    },
    {
        "name": "FGD",
        "args": [
            "bin/simon", "apply", "--extended-resources", "gpu",
            "-f", os.path.join(input_cfg_path, "FGD-without-deschedule-config", "test-cluster-config.yaml"),
            "-s", os.path.join(input_cfg_path, "FGD-without-deschedule-config", "test-scheduler-config.yaml"),
            "-p", os.path.join(input_cfg_path, "FGD-without-deschedule-config", "test-pod-distribution-config.yaml")
        ]
    },
    {
        "name": "BestFit+checkpoint",
        "args": [
            "bin/simon", "apply", "--extended-resources", "gpu",
            "-f", os.path.join(input_cfg_path, "BestFit-with-deschedule-config", "test-cluster-config.yaml"),
            "-s", os.path.join(input_cfg_path, "BestFit-with-deschedule-config", "test-scheduler-config.yaml"),
            "-p", os.path.join(input_cfg_path, "BestFit-with-deschedule-config", "test-pod-distribution-config.yaml")
        ]
    },
    {
        "name": "BestFit",
        "args": [
            "bin/simon", "apply", "--extended-resources", "gpu",
            "-f", os.path.join(input_cfg_path, "BestFit-without-deschedule-config", "test-cluster-config.yaml"),
            "-s", os.path.join(input_cfg_path, "BestFit-without-deschedule-config", "test-scheduler-config.yaml"),
            "-p", os.path.join(input_cfg_path, "BestFit-without-deschedule-config", "test-pod-distribution-config.yaml")
        ]
    }
]

    all_results = {
        "allo_dict": {},
        "quad_dict": {},
        "amnt_dict": {},
        "totl_dict": {}
    }

    # 使用线程池进行并行计算
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(run_command, commands))

    # 处理并行计算的结果
    for name, (allo_dict, quad_dict, amnt_dict, totl_dict) in results:
        all_results["allo_dict"][name] = allo_dict
        all_results["quad_dict"][name] = quad_dict
        all_results["amnt_dict"][name] = amnt_dict
        all_results["totl_dict"][name] = totl_dict

    unique_filename = str(uuid.uuid4()) + ".json"
    result_path = os.path.join(output_file_path, unique_filename)

    # 将 all_results 保存为 JSON 文件
    with open(result_path, 'w') as f:
        json.dump(all_results, f,indent=4)

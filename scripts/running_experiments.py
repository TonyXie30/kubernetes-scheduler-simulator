#!/usr/bin/env python3
import json
import sys
import re
import subprocess
import os
import concurrent.futures
import uuid


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


if __name__ == "__main__":
    
    random_filename = f"datas/{uuid.uuid4().hex}.json"
    input_str = random_filename
    if len(sys.argv) > 1:
        input_str = sys.argv[1]
    else:
        os.makedirs('datas', exist_ok=True)
    # 原有的命令参数
    commands = [
        {
            "name": "Rw",
            "args": [
                "bin/simon", "apply", "--extended-resources", "gpu",
                "-f", "example/Random-with-deschedule-config/test-cluster-config.yaml",
                "-s", "example/Random-with-deschedule-config/test-scheduler-config.yaml",
                "-p", "example/Random-with-deschedule-config/test-pod-distribution-config.yaml"
            ]
        },
        {
            "name": "Rwo",
            "args": [
                "bin/simon", "apply", "--extended-resources", "gpu",
                "-f", "example/Random-without-deschedule-config/test-cluster-config.yaml",
                "-s", "example/Random-without-deschedule-config/test-scheduler-config.yaml",
                "-p", "example/Random-without-deschedule-config/test-pod-distribution-config.yaml"
            ]
        },
        {
            "name": "Fw",
            "args": [
                "bin/simon", "apply", "--extended-resources", "gpu",
                "-f", "example/FGD-with-deschedule-config/test-cluster-config.yaml",
                "-s", "example/FGD-with-deschedule-config/test-scheduler-config.yaml",
                "-p", "example/FGD-with-deschedule-config/test-pod-distribution-config.yaml"
            ]
        },
        {
            "name": "Fwo",
            "args": [
                "bin/simon", "apply", "--extended-resources", "gpu",
                "-f", "example/FGD-without-deschedule-config/test-cluster-config.yaml",
                "-s", "example/FGD-without-deschedule-config/test-scheduler-config.yaml",
                "-p", "example/FGD-without-deschedule-config/test-pod-distribution-config.yaml"
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


    # 将 all_results 保存为 JSON 文件
    with open(input_str, 'w') as f:
        json.dump(all_results, f,indent=4)

import sys
import re
import subprocess
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def log_to_dict(content:str):

    ALLO_KEYS = ['MilliCpu','Memory','Gpu','MilliGpu']
    QUAD_KEYS = ["q1_lack_both", 'q2_lack_gpu', 'q3_satisfied', 'q4_lack_cpu', 'xl_satisfied', 'xr_lack_cpu', 'no_access', "frag_gpu_milli"]

    NUM_CLUSTER_ANALYSIS_LINE = 16
    counter = 0
    allo_dict = {}
    quad_dict = {}
    amnt_dict = {}
    totl_dict = {}

    for line in content.split('\n'):
        INFOMSG="level=info msg="
        if INFOMSG not in line:
            continue
        line = line.split(INFOMSG)[1]
        line = line[1:-2] # get rid of " and \n"

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
                allo_dict[camel_to_snake(key+tag)] = ratio
                amount = float(value.split('(')[1].split('/')[0])
                amnt_dict[camel_to_snake(key+'Amount'+tag)] = amount

                total = float(value.split(')')[0].split('/')[1])
                totl_dict[camel_to_snake(key+'Total')] = total # update without tag
            elif key in QUAD_KEYS:
                quad_dict[camel_to_snake(key+tag)] = float(value.split('(')[1].split('%')[0].strip())

    return allo_dict, quad_dict, amnt_dict, totl_dict

# 创建 logs 文件夹（如果不存在）
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 定义命令参数
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

outputs = {}


# 运行命令并捕获输出
for cmd_info in commands:
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
        outputs[name] = output
        
        # 将输出写入日志文件
        with open(log_file, "w") as f:
            f.write(output)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {' '.join(args)}: {e.stderr}")
        sys.exit(1)

    allo_dict, quad_dict, amnt_dict, totl_dict = log_to_dict(output)
    # 打印输出
    print(allo_dict)
    print(quad_dict)
    print(amnt_dict)
    print(totl_dict)
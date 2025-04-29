#!/bin/bash

go mod vendor
make

# 创建 logs 文件夹（如果不存在）
mkdir -p logs

# 定义日志文件路径
log_file_R_w="logs/Rw_$(date +%Y%m%d%H%M%S).log"
log_file_R_wo="logs/Rwo_$(date +%Y%m%d%H%M%S).log"
log_file_F_w="logs/Fw_$(date +%Y%m%d%H%M%S).log"
log_file_F_wo="logs/Fwo_$(date +%Y%m%d%H%M%S).log"

# 运行 bin/simon 命令，捕获其标准输出和标准错误输出，并将输出保存到日志文件
Rw_output=$(bin/simon apply --extended-resources "gpu" -f example/Random-with-deschedule-config/test-cluster-config.yaml -s example/Random-with-deschedule-config/test-scheduler-config.yaml -p example/Random-with-deschedule-config/test-pod-distribution-config.yaml 2>&1 | tee "$log_file_R_w")
if [ $? -ne 0 ]; then
    echo "Error occurred while running bin/simon: $Rw_output"
    exit 1
fi

Rwo_output=$(bin/simon apply --extended-resources "gpu" -f example/Random-without-deschedule-config/test-cluster-config.yaml -s example/Random-without-deschedule-config/test-scheduler-config.yaml -p example/Random-without-deschedule-config/test-pod-distribution-config.yaml 2>&1 | tee "$log_file_R_wo")
if [ $? -ne 0 ]; then
    echo "Error occurred while running bin/simon: $Rwo_output"
    exit 1
fi

Fw_output=$(bin/simon apply --extended-resources "gpu" -f  example/FGD-with-deschedule-config/test-cluster-config.yaml -s example/FGD-with-deschedule-config/test-scheduler-config.yaml -p example/FGD-with-deschedule-config/test-pod-distribution-config.yaml 2>&1 | tee "$log_file_F_w")
if [ $? -ne 0 ]; then
    echo "Error occurred while running bin/simon: $Fw_output"
    exit 1
fi

Fwo_output=$(bin/simon apply --extended-resources "gpu" -f example/FGD-without-deschedule-config/test-cluster-config.yaml -s example/FGD-without-deschedule-config/test-scheduler-config.yaml -p example/FGD-without-deschedule-config/test-pod-distribution-config.yaml 2>&1 | tee "$log_file_F_wo")
if [ $? -ne 0 ]; then
    echo "Error occurred while running bin/simon: $Fwo_output"
    exit 1
fi


# 定义 Python 脚本路径，需替换为实际路径
python_script_path="scripts/analy-plot.py"

# 检查 Python 脚本是否存在
if [ ! -f "$python_script_path" ]; then
    echo "Python script $python_script_path not found."
    exit 1
fi

# 将 bin/simon 的输出传递给 Python 脚本
echo "$simon_output" | python3 "$python_script_path"

# 检查 Python 脚本执行是否成功
if [ $? -ne 0 ]; then
    echo "Error occurred while running Python script."
    exit 1
fi


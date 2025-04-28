#!/bin/bash

go mod vendor
make

# 创建 logs 文件夹（如果不存在）
mkdir -p logs

# 定义日志文件路径
log_file="logs/simon_$(date +%Y%m%d%H%M%S).log"

# 运行 bin/simon 命令，捕获其标准输出和标准错误输出，并将输出保存到日志文件
simon_output=$(bin/simon apply --extended-resources "gpu" -f example/test-cluster-config.yaml -s example/test-scheduler-config.yaml -p example/test-pod-distribution-config.yaml 2>&1 | tee "$log_file")

# 检查命令执行是否成功
if [ $? -ne 0 ]; then
    echo "Error occurred while running bin/simon: $simon_output"
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


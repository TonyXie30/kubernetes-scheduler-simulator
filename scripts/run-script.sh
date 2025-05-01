#!/bin/bash

go mod vendor
make

node_generate_script_path="scripts/generate_node_config.py"  
node_target_path="example/test-cluster/node"
node_cnt=500

# 检查 Python 脚本是否存在
if [ ! -f "$node_generate_script_path" ]; then
    echo "Python script $node_generate_script_path not found."
    exit 1
fi

# 调用Python脚本并传递目标路径作为参数
python3 $node_generate_script_path "$node_target_path" "$node_cnt"

# 检查 Python 脚本执行是否成功
if [ $? -ne 0 ]; then
    echo "Error occurred while running node generation script."
    exit 1
fi

# 直接定义一个JSON格式，代表了每个pod种类的replicas数目
json_data='{
    "1":10,
    "2":10,
    "3":10,
    "4":10,
    "5":10,
    "6":10,
    "7":10,
    "8":10
}'

pod_generate_script_path="scripts/generate_pod_config.py"  
pod_target_path="example/test-cluster/pod"

# 检查 Python 脚本是否存在
if [ ! -f "$pod_generate_script_path" ]; then
    echo "Python script $pod_generate_script_path not found."
    exit 1
fi

# 调用Python脚本并传递JSON字符串和目标路径作为参数
python3 $pod_generate_script_path "$pod_target_path" "$json_data"

# 检查 Python 脚本执行是否成功
if [ $? -ne 0 ]; then
    echo "Error occurred while running pod generation script."
    exit 1
fi

# 多次采样实验
running_script_path="scripts/running_experiments.py"
# 检查 Python 脚本是否存在
if [ ! -f "$running_script_path" ]; then
    echo "Python script $running_script_path not found."
    exit 1
fi


# 使用数组来存储任务
tasks=()

# 初始化 j
j=1

# 开启空匹配模式
shopt -s nullglob

while [ -d "datas/test_group_$j" ]; do
    json_files=("datas/test_group_$j"/*.json)
    if [ ${#json_files[@]} -ne 0 ]; then
        ((j++))
    else
        break
    fi
done

# 关闭空匹配模式
shopt -u nullglob
# 循环 10 次
for i in {1..10}
do
    echo "No. $i Experiments"
    # 创建新的文件夹
    mkdir -p "datas/test_group_$j"

    # 生成目标路径
    running_target_path="datas/test_group_$j/$i.json"

    # 将每个任务添加到数组中
    tasks+=("python3 $running_script_path $running_target_path")
done

# 使用 GNU Parallel 并行执行任务，-j 表示并行任务数量，这里设置为 4，可按需调整
parallel -j 4 ::: "${tasks[@]}"

# 检查是否有任务失败
if [ $? -ne 0 ]; then
    echo "Error occurred while running some running_experiments script."
    exit 1
fi
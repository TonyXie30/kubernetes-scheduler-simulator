import os
import shutil
import sys

def generate_node_configs(target_path, num_nodes, start_ip="192.168.0.100", gpu_card_model="V100", gpu_count=8, cpu=192, memory="1505762Mi", pods=110):

    os.makedirs(target_path,exist_ok=True)

    # 解析起始 IP
    ip_parts = list(map(int, start_ip.split('.')))
    all_yaml_content = ""

    for i in range(num_nodes):
        node_number = i + 100
        hostname = f"pai-node-{node_number - 100:02d}"
        node_ip = '.'.join(map(str, ip_parts))

        # 生成 YAML 内容
        yaml_content = f"""apiVersion: v1
kind: Node
metadata:
  labels:
    beta.kubernetes.io/arch: amd64
    beta.kubernetes.io/os: linux
    kubernetes.io/arch: amd64
    kubernetes.io/hostname: {hostname}
    kubernetes.io/os: linux
    node-role.kubernetes.io/master: ''
    alibabacloud.com/gpu-card-model: {gpu_card_model}
    node-ip: {node_ip}
  name: {hostname}
status:
  allocatable:
    alibabacloud.com/gpu-count: '{gpu_count}'
    alibabacloud.com/gpu-milli: '1000'
    cpu: {cpu}
    memory: {memory}
    pods: '{pods}'
  capacity:
    alibabacloud.com/gpu-count: '{gpu_count}'
    alibabacloud.com/gpu-milli: '1000'
    cpu: {cpu}
    memory: {memory}
    pods: '{pods}'
"""

        # 添加分隔符和当前节点的 YAML 内容
        if all_yaml_content:
            all_yaml_content += "---\n"
        all_yaml_content += yaml_content

        # 递增 IP
        ip_parts[3] += 1
        if ip_parts[3] > 255:
            ip_parts[3] = 0
            ip_parts[2] += 1
            if ip_parts[2] > 255:
                ip_parts[2] = 0
                ip_parts[1] += 1
                if ip_parts[1] > 255:
                    ip_parts[1] = 0
                    ip_parts[0] += 1

    # 合并后的文件路径
    merged_filename = os.path.join(target_path, "merged_nodes.yaml")
    # 写入合并后的 YAML 内容
    with open(merged_filename, 'w') as f:
        f.write(all_yaml_content)

    print(f"Generated {merged_filename}")

if __name__ == "__main__":
    # 自定义参数
    if len(sys.argv)!= 3:
        print("请提供目标路径和节点数量作为参数")
        sys.exit(1)

    target_path = sys.argv[1]
    num_nodes = sys.argv[2]
    generate_node_configs(target_path, int(num_nodes))
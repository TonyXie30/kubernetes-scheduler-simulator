import os

def generate_node_configs(target_path, num_nodes, start_ip="192.168.0.100", gpu_card_model="V100", gpu_count=8, cpu=192, memory="1505762Mi", pods=110):
    # 确保目标路径存在
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # 解析起始 IP
    ip_parts = list(map(int, start_ip.split('.')))

    for i in range(num_nodes):
        node_number = i + 100
        hostname = f"pai-node-{node_number - 100:02d}"
        node_ip = '.'.join(map(str, ip_parts))
        filename = os.path.join(target_path, f"{hostname}.yaml")

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

        # 写入文件
        with open(filename, 'w') as f:
            f.write(yaml_content)

        print(f"Generated {filename}")

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

if __name__ == "__main__":
    # 自定义参数
    target_path = "example/test-cluster/node"
    num_nodes = 500
    generate_node_configs(target_path, num_nodes)

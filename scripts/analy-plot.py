import sys
import re
# 读取标准输入的内容
content = sys.stdin.read()


def extract_schedule_data(content):
    # 提取InitSchedule数据
    init_schedule_pattern = r'========== Cluster Analysis Results \(InitSchedule\) ==========(.*?)=============================================='
    init_schedule_match = re.search(init_schedule_pattern, content, re.DOTALL)
    init_schedule_data = {}
    if init_schedule_match:
        init_schedule_section = init_schedule_match.group(1).strip()
        for line in init_schedule_section.split('\n'):
            if line.startswith('Allocation Ratio:'):
                continue
            parts = line.strip().split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                init_schedule_data[key] = value

    # 提取PostDeschedule数据
    post_schedule_pattern = r'========== Cluster Analysis Results \(PostDeschedule\) ==========(.*?)=============================================='
    post_schedule_match = re.search(post_schedule_pattern, content, re.DOTALL)
    post_schedule_data = {}
    if post_schedule_match:
        post_schedule_section = post_schedule_match.group(1).strip()
        for line in post_schedule_section.split('\n'):
            if line.startswith('Allocation Ratio:'):
                continue
            parts = line.strip().split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                post_schedule_data[key] = value

    return init_schedule_data, post_schedule_data


init_data, post_data = extract_schedule_data(content)
print("InitSchedule数据:")
for key, value in init_data.items():
    print(f"{key}: {value}")

print("\nPostDeschedule数据:")
for key, value in post_data.items():
    print(f"{key}: {value}")


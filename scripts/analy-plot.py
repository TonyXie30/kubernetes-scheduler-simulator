import sys
import re
# 读取标准输入的内容

content = sys.stdin.read()

ALLO_KEYS = ['MilliCpu','Memory','Gpu','MilliGpu']
QUAD_KEYS = ["q1_lack_both", 'q2_lack_gpu', 'q3_satisfied', 'q4_lack_cpu', 'xl_satisfied', 'xr_lack_cpu', 'no_access', "frag_gpu_milli"]

def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


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

print(allo_dict)
print(quad_dict)
print(amnt_dict)
print(totl_dict)


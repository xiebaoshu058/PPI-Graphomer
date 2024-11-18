import os
import subprocess
import numpy as np
from scipy.stats import pearsonr
import re
import pandas as pd


index_file = os.path.join("/public/mxp/xiejun/py_project/PP", "index", "INDEX_general_PP.2020")

# 获取亲和力信息
# PDBbind的获取方式，这里计算的是以10为底的log，在后面需要换底公式换掉
affinity_dict1 = {}
with open(index_file, 'r') as f:
    lines = f.readlines()
    for line in lines[6:]:
        tokens = line.split()
        protein_name = tokens[0].strip()
        # if protein_name=="5nvl":
        #     print("here")
        # 匹配 Kd, Ki, 或 IC50
        match = re.search(r'(Kd|Ki|IC50)([=<>~])([\d\.]+)([munpfM]+)', line)
        if match:
            measure_type = match.group(1)
            operator = match.group(2)
            value = float(match.group(3))
            unit = match.group(4)
            # 单位转换成 M（摩尔）
            unit_multiplier = {
                'mM': 1e-3,
                'uM': 1e-6,
                'nM': 1e-9,
                'pM': 1e-12,
                'fM': 1e-15
            }
            value_in_molar = value * unit_multiplier.get(unit, 1)  # 默认为 Mol

            # 计算以10为底的log值（pKa）
            if operator == '=' or operator == '~' or operator == '>':
                pKa_value = -np.log(value_in_molar)*0.592
            elif operator == '<':
                # 如果是 '<'，则取 "<" 值更保守的一种处理方式
                pKa_value = -np.log(value_in_molar)*0.592

            affinity_dict1[protein_name] = pKa_value

foldx_dict={}
with open("/public/mxp/xiejun/py_project/PPI_affinity/rosetta_result/output_ST.fxout","r") as rf:
    lines=rf.readlines()
    for line in lines:
        line_list=line.split("\t")
        foldx_dict[line_list[0].split("/")[-1]]=float(line_list[1])


# benchmark79的亲和力数据
# 读取CSV文件
csv_file = '/public/mxp/xiejun/py_project/PPI_affinity/elife-07454-supp4-v4.csv'
data = pd.read_csv(csv_file)
# 创建包含 PDB 名称和亲和力数值的字典
affinity_dict3 = dict(zip(data.iloc[:, 0].apply(lambda x: x.replace(".pdb", "")), data.iloc[:, 1]))



# 指定Rosetta的路径和PDB文件夹
rosetta_bin_path = "//public/mxp/shared-space//rosetta.binary.linux.release-315/main/source/bin/score_jd2.static.linuxgccrelease"
# pdb_folder = "/public/mxp/xiejun/py_project/PPI_affinity/data_final/pdb/benchmark79/"
# result_sc_path = "/public/mxp/xiejun/py_project/PPI_affinity/rosetta_result/benchmark79_sc/"
pdb_folder = "/public/mxp/xiejun/py_project/PPI_affinity/data_final/pdb/test/"
result_sc_path = "/public/mxp/xiejun/py_project/PPI_affinity/rosetta_result/test_sc/"


energy_out_list=[]
true_affinity=[]
# for protein in os.listdir(pdb_folder):
#     outfile=result_sc_path+protein.upper().split(".")[0]+".sc"
#     outfile=result_sc_path+protein.split(".pd")[0]+".sc"

#     energy_single_list=[]
#     with open(outfile,"r") as rf:
#         lines=rf.readlines()
#         for index,line in enumerate(lines):
#             # 跳过前1行
#             if index<2:
#                 continue
#             energy_out_list.append(float(re.split(r"[ ]+", line)[1]))
#             true_affinity.append(-affinity_dict1[protein.split(".")[0]])

for protein in os.listdir(pdb_folder):

    energy_out_list.append(foldx_dict[protein])
    true_affinity.append(-affinity_dict1[protein.split(".")[0]])



# 计算皮尔逊相关系数
if len(energy_out_list) > 1:  # 至少需要两个数据点
    correlation, _ = pearsonr(true_affinity, energy_out_list)
    print(f"皮尔逊相关系数: {correlation}")
else:
    print("数据点不足，无法计算皮尔逊相关系数")
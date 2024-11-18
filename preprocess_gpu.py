import os
import re
import numpy as np
from Bio.PDB import PDBParser
from Bio.SeqUtils import seq1
from collections import defaultdict
from tqdm import tqdm
from scipy.spatial.distance import cdist
from multiprocessing import Pool, cpu_count
import multiprocessing
from collections import Counter
import matplotlib.pyplot as plt
import esm
import torch
import esm.inverse_folding
import pandas as pd


# 设置路径
pdb_folder = "/public/mxp/xiejun/py_project/PP_1"
# pdb_folder = "/public/mxp/xiejun/py_project/PPI_affinity/PDBs"
# pdb_folder = "/public/mxp/xiejun/py_project/PPI_affinity/data/pdbs/benchmark79"
# pdb_folder = "/public/mxp/xiejun/py_project/PPI_affinity/PP_1"
pdb_folder = "/public/mxp/xiejun/py_project/PPI_affinity/data_final/pdb/benchmark79"

index_file = os.path.join("/public/mxp/xiejun/py_project/PP", "index", "INDEX_general_PP.2020")

# 常量定义
standard_res =[
        "GLY" , 'G',
        "ALA" , 'A',
        "VAL" , 'V',
        "LEU" , 'L',
        "ILE" , 'I',
        "PRO" , 'P',
        "PHE" , 'F',
        "TYR" , 'Y',
        "TRP" , 'W',
        "SER" , 'S',
        "THR" , 'T',
        "CYS" , 'C',
        "MET" , 'M',
        "ASN" , 'N',
        "GLN" , 'Q',
        "ASP" , 'D',
        "GLU" , 'E',
        "LYS" , 'K',
        "ARG" , 'R',
        "HIS" , 'H'
        ]


atom_types = ['C', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Br', 'else']
degrees = [0, 1, 2, 3, 4, 'else']
hybridizations = ['s', 'sp', 'sp2', 'sp3', 'sp3d', 'sp3d2', 'else']
charges = [-2, -1, 0, 1, 2, 3, 'else']
amino_acids = list("LAGVSETIRDPKQNFYMHW") + ["C", "others"]

from collections import OrderedDict

def list_to_ordered_set(lst):
    # 使用字典来消除重复并保持顺序
    ordered_dict = OrderedDict.fromkeys(lst)
    # 将字典的键转换为集合（按照出现的顺序）
    ordered_set = list(ordered_dict.keys())
    return ordered_set

# 获取亲和力信息
# affinity_dict = {}
# with open(index_file, 'r') as f:
#     lines = f.readlines()
#     for line in lines[6:]:
#         tokens = line.split()
#         protein_name = tokens[0].strip()
#         # if protein_name=="5nvl":
#         #     print("here")
#         # 匹配 Kd, Ki, 或 IC50
#         match = re.search(r'(Kd|Ki|IC50)([=<>~])([\d\.]+)([munpfM]+)', line)
#         if match:
#             measure_type = match.group(1)
#             operator = match.group(2)
#             value = float(match.group(3))
#             unit = match.group(4)
#             # 单位转换成 M（摩尔）
#             unit_multiplier = {
#                 'mM': 1e-3,
#                 'uM': 1e-6,
#                 'nM': 1e-9,
#                 'pM': 1e-12,
#                 'fM': 1e-15
#             }
#             value_in_molar = value * unit_multiplier.get(unit, 1)  # 默认为 Mol
#             # 计算以10为底的log值（pKa）
#             if operator == '=' or operator == '~' or operator == '>':
#                 pKa_value = -np.log10(value_in_molar)
#             elif operator == '<':
#                 # 如果是 '<'，则取 "<" 值更保守的一种处理方式
#                 pKa_value = -np.log10(value_in_molar)
#             affinity_dict[protein_name] = pKa_value



# # skempi的亲和力数据
# csv_file_path="/public/mxp/xiejun/py_project/PPI_affinity/skempi_v2.csv"
# # 读取CSV文件，指定分隔符为分号
# df = pd.read_csv(csv_file_path, delimiter=';')
# df['Affinity_wt (M)'] = pd.to_numeric(df['Affinity_wt (M)'], errors='coerce')
# # 初始化一个空字典
# affinity_dict_temp = {}
# # 遍历每一行，填充字典
# for index, row in df.iterrows():
#     pdb_name = row['#Pdb'].split("_")[0]
#     affinity = -np.log(row['Affinity_wt (M)'])
#     if pdb_name not in affinity_dict_temp:
#         affinity_dict_temp[pdb_name] = []
#     affinity_dict_temp[pdb_name].append(affinity)
# affinity_dict={}
# for pdb_name in list(affinity_dict_temp.keys()):
#     if len(set(affinity_dict_temp[pdb_name]))==1 and affinity_dict_temp[pdb_name][0] is not None:
#         affinity_dict[pdb_name]=affinity_dict_temp[pdb_name][0]

# 论文中的skempi的26个野生型子集
# 读取CSV文件
# csv_file = '/public/mxp/xiejun/py_project/PPI_affinity/SI-File-5-protein-protein-test-set-3.csv'
# data = pd.read_csv(csv_file)
# # 筛选出第二列和第三列为空的行
# no_mutation_data = data[data.iloc[:, 1].isnull() & data.iloc[:, 2].isnull()]
# # 创建包含没有突变信息的PDB名称和亲和力数值的字典
# affinity_dict = dict(zip(no_mutation_data.iloc[:, 0], no_mutation_data.iloc[:, 3]))

# # benchmark79的亲和力数据
# # 读取CSV文件
# csv_file = '/public/mxp/xiejun/py_project/PPI_affinity/elife-07454-supp4-v4.csv'
# data = pd.read_csv(csv_file)

# # 创建包含 PDB 名称和亲和力数值的字典
# affinity_dict = dict(zip(data.iloc[:, 0], data.iloc[:, 1]))



def one_hot_encoding(value, categories):
    vec = [0] * len(categories)
    if value in categories:
        vec[categories.index(value)] = 1
    else:
        vec[-1] = 1
    return vec

def compute_dist(coord1, coord2):
    return np.linalg.norm(coord1 - coord2)

def extract_protein_data(pdb_file, model_esm, alphabet, model_esmif, alphabet_if, device):
    batch_converter = alphabet.get_batch_converter()
    parser = PDBParser(QUIET=True)
    base_name = os.path.basename(pdb_file).split(".")
    structure = parser.get_structure(base_name[0]+'.'+base_name[1], pdb_file)
    protein_name = base_name[0]

    sequence = ""
    sequence_true = ""
    coord_matrix = []
    all_atom_chains = []
    res_index = 0  # 氨基酸全局索引
    all_res_chain = []
    padG_index_list = [] # 所有用Gpad的索引（对应上面的全局索引）

    # standard_res = set("ACDEFGHIKLMNPQRSTVWY") # Assume you have set of standard residues

    for model in structure:
        for chain in model:
            previous_residue_id = None
            for residue in chain:
                res_atoms, res_atom_coords, res_atom_chains = [], [], []
                exist_flag = True   # 判断是否存在三个骨架原子

                # Check backbone atoms
                n_atom, ca_atom, c_atom = None, None, None
                for atom in residue:
                    coord = atom.get_vector().get_array()
                    if atom.get_id() == 'N':
                        n_atom = coord
                    elif atom.get_id() == 'CA':
                        ca_atom = coord
                    elif atom.get_id() == 'C':
                        c_atom = coord
                    res_atoms.append(atom)
                    res_atom_coords.append(coord)
                    res_atom_chains.append(chain.id)

                if n_atom is None or ca_atom is None or c_atom is None:
                    exist_flag = False
                # 对于水分子和非标准氨基酸，不做处理
                if residue.get_resname() == 'HOH' or residue.get_resname() not in standard_res:
                    res_name = 'HOH'
                # 如果四个骨架原子都存在
                elif exist_flag:
                    res_name = seq1(residue.get_resname())
                    residue_id = residue.id[1]
                    # 判断两者相等是为了把插入残基也纳入
                    # if residue_id == previous_residue_id:
                    #     print("jere")
                    # 需要插入G的地方，氨基酸序号不连续且不相等，且前一个序号大于0（因为有些序号小于0的氨基酸作为补充实际上连续）
                    if previous_residue_id and residue_id != previous_residue_id + 1 and previous_residue_id > 0 and residue_id != previous_residue_id :
                        gap_size = residue_id - previous_residue_id - 1
                        gap_seq = 'G' * gap_size
                        sequence += gap_seq
                        padG_index_list.extend([res_index + i for i in range(gap_size)])
                        all_res_chain.extend([chain.id] * gap_size)
                        res_index += gap_size
                    sequence += res_name
                    # 真实序号，不加入G
                    sequence_true += res_name
                    all_res_chain.append(chain.id)
                    coord_matrix.append([n_atom, ca_atom, c_atom])
                    res_index += 1
                    previous_residue_id = residue_id
                else:
                    # 没有骨架原子的残缺氨基酸
                    res_name = 'canque'
    # 坐标信息
    coord_matrix = np.array(coord_matrix, dtype=object)

    # Filter out unwanted amino acids
    indices_to_delete = [i for i, char in enumerate(sequence) if char in 'XZ']
    sequence = sequence.replace("X", "").replace("Z", "")
    chain_id_res = [elem for i, elem in enumerate(all_res_chain) if i not in indices_to_delete]
    # 按链分割序列
    seq_single_chain = [
        ''.join(sequence[j] for j in range(len(sequence)) if chain_id_res[j] == x)
        for x in list_to_ordered_set(chain_id_res)
    ]
    # 链接不同链的linker
    separator = "GGGGGGGGGGGGGGGGGGGG"
    full_sequence = ""
    separator_indices = []
    length = 0

    current_length = 0  # 用于记录当前序列长度
    linker_offsets = []  # 用于记录每个链的开始位置，以供以后更新padG索引

    padG_index_list_delete=padG_index_list.copy()
    updated_padG_index_list = []
    for seq in seq_single_chain[:-1]:  
        full_sequence += seq
        current_length += len(seq)

        # 更新padG_index_list
        # 使用索引删除原来的index_list，如果小于curindex说明在当前序列，直接加入，否则索引加上linker长度，暂不处理
        count=0
        for it in range(len(padG_index_list_delete)):
            if padG_index_list_delete[it-count] >= current_length:
                padG_index_list_delete[it-count]+= len(separator)
            else:
                updated_padG_index_list.append(padG_index_list_delete[it-count])
                del padG_index_list_delete[it-count]
                count+=1

        # 插入分隔符linker
        full_sequence += separator

        separators_start = current_length
        separator_indices.extend(range(separators_start, separators_start + len(separator)))

        current_length += len(separator)

    full_sequence += seq_single_chain[-1]
    current_length += len(seq_single_chain[-1])
    # 确保最后一部分的索引也包含在updated_padG_index_list中
    count=0
    for it in range(len(padG_index_list_delete)):
        if padG_index_list_delete[it-count] >= current_length:
            padG_index_list_delete[it-count]+= len(separator)
        else:
            updated_padG_index_list.append(padG_index_list_delete[it-count])
            del padG_index_list_delete[it-count]
            count+=1

    # 理应处理完索引index
    assert padG_index_list_delete==[]
    # 名字无所谓
    concatenated_name = "_".join([f"{protein_name}{i}" for i in range(len(seq_single_chain))])
    # 形成tokens，注意这里包含开始和结尾token
    enc_inputs_labels, enc_inputs_strs, enc_tokens = batch_converter([(concatenated_name, full_sequence)])
    # 获取特征，不包括开始和结尾token
    with torch.no_grad():
        results = model_esm(enc_tokens.to(device), repr_layers=[33], return_contacts=False)
        concatenated_representations = results["representations"][33][:, 1:-1, :].cpu()
    # 包括起始和结尾的token为all
    enc_tokens_all=enc_tokens
    # 不包括起始和结尾token
    enc_tokens = enc_tokens[:, 1:-1]

    # Combine padG_index_list and separator_indices
    combined_index_list = sorted(updated_padG_index_list + separator_indices)

    # Create mask
    mask = torch.ones(concatenated_representations.size(1), dtype=torch.bool)
    # 总的mask，包括两个pad——index
    mask[combined_index_list] = False

    # mask中有效值应该等于真实序列长度
    assert sum(mask).item()==len(sequence_true)

    # 获取真实token_representation
    token_representations = concatenated_representations[:, mask, :]
    masked_enc_tokens = enc_tokens[:, mask]

    # 更新 chain_id_res，padG_index_list是加入linker之前的，chain_id_res也是加入linker之前的,去掉对应索引，变成和sequence_true一样
    mask_padG = np.ones(len(chain_id_res), dtype=bool)
    mask_padG[padG_index_list] = False
    chain_id_res = [element for i, element in enumerate(chain_id_res) if mask_padG[i]]


    # indices_to_delete = [i for i, char in enumerate(sequence_true) if char in 'XZ']
    # sequence_true = sequence_true.replace("X", "").replace("Z", "")

    seq_single_chain = [
        ''.join(sequence_true[j] for j in range(len(sequence_true)) if chain_id_res[j] == x)
        for x in list_to_ordered_set(chain_id_res)
    ]

    coord_matrix = np.delete(coord_matrix, indices_to_delete, axis=0)
    # 拆分token_representation和tokens
    token_representations_list, enc_tokens_list = [], []
    curr_pos = 0
    for seq in seq_single_chain:
        seq_len = len(seq)
        single_representations = token_representations[:, curr_pos:curr_pos + seq_len, :]
        token_representations_list.append(single_representations)
        enc_tokens_list.append(masked_enc_tokens[0, curr_pos:curr_pos + seq_len])
        curr_pos += seq_len

    coor_dict = {
        chain: coord_matrix[np.array(chain_id_res) == chain].reshape(-1, 3, 3).astype('float32')
        for chain in list_to_ordered_set(chain_id_res)
    }

    torch.cuda.empty_cache()

    coor_feature_list = []

    for chain_id in list_to_ordered_set(chain_id_res):
        with torch.no_grad():
            coor_feature_list.append(
                esm.inverse_folding.multichain_util.get_encoder_output_for_complex(
                    model_esmif, alphabet_if, coor_dict, chain_id
                ).cpu()
            )
    # 每个链的长度应该相等
    for i in range(len(token_representations_list)):
        assert token_representations_list[i].shape[1] == coor_feature_list[i].shape[0] == enc_tokens_list[i].shape[0]

    
    addition = [token_representations_list, coor_feature_list, enc_tokens_list,enc_tokens_all,mask,seq_single_chain]

    protein_data = {
        protein_name: addition
    }

    return protein_data



import ssl
ssl._create_default_https_context = ssl._create_unverified_context

def single_worker(pdb_sub_dir_list, p_number):
    print("模型建立：")
    save_dir="/public/mxp/xiejun/py_project/PPI_affinity/data_final/preprocess/gpu_enc_token/benchmark79/"

    # save_dir="/public/mxp/xiejun/py_project/PPI_affinity/data_final/preprocess/gpu_pretrain2/test/"
    # save_dir="/public/mxp/xiejun/py_project/PPI_affinity/data/preprocessed/gpu/addition_gpu_pretrain_contrastive3/"

    os.makedirs(save_dir, exist_ok=True)
    try:
        device = torch.device('cuda:'+str(p_number%4) if torch.cuda.is_available() else 'cpu')
        # device = torch.device('cuda:0')
        model_esm, alphabet = esm.pretrained.esm2_t33_650M_UR50D()
        # model_esm, alphabet = esm.pretrained.esm2_t36_3B_UR50D()

        # model_esm=torch.load("/public/mxp/xiejun/py_project/esm_finetune/myresult/attempt1/model_esm_8.pth")
        model_esm=model_esm.eval().to(device)
        model_esmif, alphabet_if = esm.pretrained.esm_if1_gvp4_t16_142M_UR50()
        model_esmif = model_esmif.eval().to(device)
        result_list=[]
        for pdb_file in tqdm(pdb_sub_dir_list):
            # if pdb_file!="4bpk.ent.pdb":
            #     continue
            full_pdb_path = os.path.join(pdb_folder, pdb_file)
            try:
                result_list.append(extract_protein_data(full_pdb_path,model_esm,alphabet,model_esmif,alphabet_if,device))
            except:
                print("pdb_file")
            torch.cuda.empty_cache()
            print("processed: ",pdb_file)
        np.save(save_dir+"pdbbind"+str(p_number)+".npy", result_list,allow_pickle=True)
        print("saved!")
    except Exception as e:
        with open(save_dir+'error{}.txt'.format(p_number),'w+') as f:
            print("in No.{} process, exception occurred".format(p_number))
            print("in {}".format(pdb_file))
            print("line:{}".format(e.__traceback__.tb_lineno))
            print(str(e))
            f.write("in No.{} process, exception occurred:\n".format(p_number))
            f.write("in {}\n".format(pdb_file))
            f.write("line:{}".format(e.__traceback__.tb_lineno))
            f.write(str(e))


if __name__ == '__main__':
    # multiprocessing.set_start_method("spawn")
    processor=12
    # pdb_dir_list_all=np.load("./pdb_list.npy",allow_pickle=True)
    # pdb_dir_list=os.listdir(pdb_folder)
    # skempi需要在affinity_dict和pdb交集中确定列表
    # pdb_exist_list=[i+".pdb" for i in list(affinity_dict.keys())]
    # pdb_dir_list=list(set(pdb_exist_list)&set(os.listdir(pdb_folder)))
    # pdb_exist_list=list(affinity_dict.keys())

    # pdb_dir_list=list(set(pdb_exist_list)&set(os.listdir(pdb_folder)))
    pdb_dir_list=os.listdir(pdb_folder)

    # pdb_dir_list=[i.split("_")[0] for i in list(affinity_dict.keys())]
    # single_worker(pdb_dir_list, 0)
    # pdb_dir_list=pdb_dir_list_all[0:4]
    # 2 3 5 1 2 4 //gpu11和computer4没跑，放到2,3跑完了跑
    # pdb_dir_list=pdb_dir_list_all[0:len(pdb_dir_list_all)//6]
    # pdb_dir_list=pdb_dir_list_all[0:len(pdb_dir_list_all)//6]
    # # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6:len(pdb_dir_list_all)//6*2]
    # # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*2:len(pdb_dir_list_all)//6*3]
    # # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*3:len(pdb_dir_list_all)//6*4]
    # # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*4:len(pdb_dir_list_all)//6*5]
    # # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*5:len(pdb_dir_list_all)]

    p = Pool(processor)
    num_pdb = len(pdb_dir_list)
    n = num_pdb // processor
    print(num_pdb)
    for i in range(processor):
        start = n * i
        end = num_pdb if i == processor - 1 else n * (i + 1)
        pdb_sub_dir_list = pdb_dir_list[start:end]
        print(pdb_sub_dir_list)
    print(num_pdb)
    # input("确认信息：")
    for i in range(processor):
        start = n * i
        end = num_pdb if i == processor - 1 else n * (i + 1)
        pdb_sub_dir_list = pdb_dir_list[start:end]
        # pdb_sub_dir_list = ['nz']
        p.apply_async(single_worker, args=(pdb_sub_dir_list, i))
    p.close()
    p.join()



    # pdb_dir_list_true=[]
    # # 2 3 5 1 2 4 //gpu11和computer4没跑，放到2,3跑完了跑
    # # pdb_dir_list=pdb_dir_list_all[0:len(pdb_dir_list_all)//6]
    # pdb_dir_list=pdb_dir_list_all[0:len(pdb_dir_list_all)//6]
    # To_process_index=[]
    # num_pdb = len(pdb_dir_list)
    # processor=19
    # n = num_pdb // processor
    # for i in range(processor):
    #     if not os.path.exists("/public/mxp/xiejun/py_project/PPI_affinity/gpu2/pdbbind"+str(i)+".npy"):
    #         To_process_index.append(i)
    # for i in To_process_index:
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_dir_list_true.extend(pdb_dir_list[start:end])


    # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6:len(pdb_dir_list_all)//6*2]
    # To_process_index=[]
    # processor=25
    # num_pdb = len(pdb_dir_list)
    # n = num_pdb // processor
    # for i in range(processor):
    #     if not os.path.exists("/public/mxp/xiejun/py_project/PPI_affinity/gpu3/pdbbind"+str(i)+".npy"):
    #         To_process_index.append(i)
    # for i in To_process_index:
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_dir_list_true.extend(pdb_dir_list[start:end])



    # # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*2:len(pdb_dir_list_all)//6*3]

    # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*3:len(pdb_dir_list_all)//6*4]
    # To_process_index=[]
    # processor=25
    # num_pdb = len(pdb_dir_list)
    # n = num_pdb // processor
    # for i in range(processor):
    #     if not os.path.exists("/public/mxp/xiejun/py_project/PPI_affinity/computer1/pdbbind"+str(i)+".npy"):
    #         To_process_index.append(i)
    # for i in To_process_index:
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_dir_list_true.extend(pdb_dir_list[start:end])


    # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*4:len(pdb_dir_list_all)//6*5]
    # To_process_index=[]
    # processor=25
    # num_pdb = len(pdb_dir_list)
    # n = num_pdb // processor
    # for i in range(processor):
    #     if not os.path.exists("/public/mxp/xiejun/py_project/PPI_affinity/computer2/pdbbind"+str(i)+".npy"):
    #         To_process_index.append(i)
    # for i in To_process_index:
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_dir_list_true.extend(pdb_dir_list[start:end])

    # pdb_dir_list=pdb_dir_list_all[len(pdb_dir_list_all)//6*5:len(pdb_dir_list_all)]
    # To_process_index=[]
    # processor=25
    # num_pdb = len(pdb_dir_list)
    # n = num_pdb // processor
    # for i in range(processor):
    #     if not os.path.exists("/public/mxp/xiejun/py_project/PPI_affinity/computer4/pdbbind"+str(i)+".npy"):
    #         To_process_index.append(i)
    # for i in To_process_index:
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_dir_list_true.extend(pdb_dir_list[start:end])


    # pdb_dir_list=pdb_dir_list_true
    # processor=26
    # p = Pool(processor)
    # num_pdb = len(pdb_dir_list)
    # n = num_pdb // processor
    # print(num_pdb)
    # for i in range(processor):
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_sub_dir_list = pdb_dir_list[start:end]
    #     print(pdb_sub_dir_list)
    # print(num_pdb)
    # input("确认信息：")
    # for i in range(processor):
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_sub_dir_list = pdb_dir_list[start:end]
    #     # pdb_sub_dir_list = ['nz']
    #     p.apply_async(single_worker, args=(pdb_sub_dir_list, i))
    # p.close()
    # p.join()



    # atom_length_list=[]
    # for i in protein_dicts:
    #     atom_length_list.append(i["interface_atoms"])
    # dict_all=Counter(atom_length_list)
    # print("max:",max(dict_all.keys()))
    # print("min:",min(dict_all.keys()))
    # plt.bar(dict_all.keys(), height=dict_all.values())
    # plt.savefig("./atom_length.png")



    # processor=16
    # # pdb_dir_list = [f for f in os.listdir(pdb_folder) if f.endswith(".pdb")]
    # pdb_dir_list_all=np.load("./pdb_list.npy",allow_pickle=True)
    # pdb_dir_list=pdb_dir_list_all[0:len(pdb_dir_list_all)//6]
    # # single_worker(['MX'],input_dir,output_dir,if_N)
    # # single_worker(['fj'],input_dir,1)
    # p = Pool(processor)
    # # 重复的就不再跑一次了
    # # processed_dir='./output_pdb_pepl9/'
    # # processed_pdb_list=os.listdir(processed_dir)
    # # To_process_dir=[]
    # # for i in pdb_dir_list:
    # #     if i not in processed_pdb_list:
    # #         To_process_dir.append(i)
    # num_pdb = len(pdb_dir_list)
    # # num_pdb = len(pdb_dir_list)
    # print(num_pdb)
    # n = num_pdb // processor



    # # 中途报错，将没写入的汇总起来
    # # To_process_index=[]
    # # for i in range(100):
    # #     if not os.path.exists("/public/mxp/xiejun/py_project/PPI_affinity/pdbbind"+str(i)+".npy"):
    # #         To_process_index.append(i)
    # # To_process_dir=[]
    # # for i in To_process_index:
    # #     start = (num_pdb // 100) * i
    # #     end = num_pdb if i == 100 - 1 else (num_pdb // 100) * (i + 1)
    # #     To_process_dir.extend(pdb_dir_list[start:end])
    # # pdb_dir_list=To_process_dir
    # # num_pdb=len(To_process_dir)
    # # n = num_pdb // processor
    # # 以上注意删除


    # for i in range(processor):
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_sub_dir_list = pdb_dir_list[start:end]
    #     print(pdb_sub_dir_list)


    # print(len(pdb_dir_list))
    # input("确认信息：")


    # print("确认无误")
    # for i in range(processor):
    #     start = n * i
    #     end = num_pdb if i == processor - 1 else n * (i + 1)
    #     pdb_sub_dir_list = pdb_dir_list[start:end]
    #     # pdb_sub_dir_list = ['nz']
    #     p.apply_async(single_worker, args=(pdb_sub_dir_list, i))

    # # atom_length_list=[]
    # # for i in protein_dicts:
    # #     atom_length_list.append(i["interface_atoms"])
    # # dict_all=Counter(atom_length_list)
    # # print("max:",max(dict_all.keys()))
    # # print("min:",min(dict_all.keys()))
    # # plt.bar(dict_all.keys(), height=dict_all.values())
    # # plt.savefig("./atom_length.png")
    # p.close()
    # p.join()
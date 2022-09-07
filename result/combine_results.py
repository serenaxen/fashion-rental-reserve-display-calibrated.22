import os
import sys
import pandas as pd

file_prefix = 'DEBUG_CALIBRATED_all1'
dirpath = sys.path[0]
save_file = 'DEBUG_LOGNORMAL_CYCLES_all1_results.csv'

res_df_list = []
for f in os.listdir(dirpath):
    if f.startswith(file_prefix):
        res_df = pd.read_csv(f, index_col=0)
        res_df_list.append(res_df)
res_all_df = pd.concat(res_df_list)

res_all_df.to_csv(save_file)
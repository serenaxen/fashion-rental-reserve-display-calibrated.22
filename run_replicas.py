# Run simulation replicas for specified multiple configurations
# Xuening Wang
# 2022/05/04

from simulator_main import MainSimulator
from paras_debug import *

import sys, os
import argparse
import pandas as pd

parser = argparse.ArgumentParser(add_help=False)
# parser.add_argument('--rseed', type=int)
parser.add_argument('--allconfig', type=int)
parser.add_argument('--stage', type=str)
args = parser.parse_args()
# rand_seed = args.rseed

disp_pol = ['current', 'future', 'future_cstp']
adm_pol = ['IT0', 'ITInf']
alloc_pol = ['FOFS', 'EDD']

# (8/18) test schedule method
# disp_pol = ['NomiSchCpl']
# adm_pol = ['NomiSchCpl']
# alloc_pol = ["NomiSch"]
EDD_leadtime = [1, 2, 3, 4, 5, 6]
rseeds = list(range(1, 31))

exp_stage = args.stage
parameters_config.update({'exp_stage': exp_stage})
is_all_config = args.allconfig

for rand_seed in rseeds:
    parameters_main.update({'rand_seed': rand_seed})

    file_name = '_'.join([exp_stage, 'all'+str(is_all_config), 'rseed'+str(rand_seed)])
    stdout_file_name = file_name + '.txt'
    stdout_file_name = os.path.join("output", stdout_file_name)
    sys.stdout = open(stdout_file_name, 'w')

    res_list = []
    res_index_list = []
    res_cols = ['rseed', 'num_req', 'adm_rate', 'succ_order_rate', 'service_rate']

    for disp in disp_pol:
        for adm in adm_pol:
            for alloc in alloc_pol:
                parameters_config.update({'display_policy_wrt': disp, 'admission_policy': adm, 'allocation_policy': alloc})
                if alloc == 'FOFS' or alloc == 'NomiSch':
                    simul = MainSimulator(parameters_config, parameters_main, parameters_dist)
                    simul.initialize()
                    num_req, adm_rate, succ_order_rate, service_rate = simul.run_and_report(debug_truncate_time=None)

                    index = '-'.join([alloc, adm, disp])
                    res_index_list.append(index)
                    res_list.append({'rseed': rand_seed, 'num_req': num_req, 'adm_rate': round(adm_rate,4),
                                     'succ_order_rate': round(succ_order_rate,4), 'service_rate': round(service_rate, 4)})

                elif alloc == 'EDD':
                    for lt in EDD_leadtime:
                        parameters_config.update({'EDD_lead_time': lt})
                        simul = MainSimulator(parameters_config, parameters_main, parameters_dist)
                        simul.initialize()
                        num_req, adm_rate, succ_order_rate, service_rate = simul.run_and_report(debug_truncate_time=None)

                        index = '-'.join([alloc, str(lt), adm, disp])
                        res_index_list.append(index)
                        res_list.append({'rseed': rand_seed, 'num_req': num_req, 'adm_rate': round(adm_rate,4),
                                         'succ_order_rate': round(succ_order_rate,4), 'service_rate': round(service_rate,4)})

    sys.stdout.close()

    #save result file
    res_file_name = file_name + '.csv'
    res_file_name = os.path.join("result", res_file_name)
    res_df = pd.DataFrame(res_list, index=res_index_list)
    res_df.to_csv(res_file_name)
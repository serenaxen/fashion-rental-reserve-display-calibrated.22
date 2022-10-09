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

# disp_pol = ['current', 'future', 'future_cstp']
# adm_pol = ['IT0', 'ITInf']
# alloc_pol = ['FOFS', 'EDD']
# EDD_leadtime = [1, 2, 3, 4, 5, 6]
# diagnosis_story = 0

# # (9/7) test diagnosis (req stories)
# disp_pol = ['current'] #['current', 'future', 'future_cstp']
# adm_pol = ['IT0'] #['IT0', 'ITInf']
# alloc_pol = ['FOFS'] #['FOFS', 'EDD']
# EDD_leadtime = [1] #[1, 2, 3, 4, 5, 6]
# diagnosis_story = 1

# # (8/18) test schedule method
# disp_pol = ['NomiSchCpl']
# adm_pol = ['NomiSchCpl']
# alloc_pol = ["NomiSch"]
# EDD_leadtime = [1]
# diagnosis_story = 0

# (10/6) compare policies under prediction quantile
cycle_duration_lognormal_percentile_list = [37, 38, 40, 41, 42, 44, 45, 47, 48, 50, 52, 55, 57, 60, 63, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86]
## rescheduling (without dealing with realtime delays)
policy_comp = "NomiSch"
disp_pol = ['NomiSchCpl']
adm_pol = ['NomiSchCpl'] #TODO: end of horizon effect? any trouble?
alloc_pol = ["NomiSch"]
EDD_leadtime = [1] #redundant
# ## EDD with delay prediction
# policy_comp = "EDDPred"
# disp_pol = ['future_cstp']
# adm_pol = ['IT0']
# alloc_pol = ['EDD']
# EDD_leadtime = [1]
## FOFS with instant commitment
# policy_comp = "FOFS"
# disp_pol = ['current']
# adm_pol = ['IT0']
# alloc_pol = ['FOFS']
# EDD_leadtime = [1] #redundant

diagnosis_story = 0
enable_output_file = 0




rseeds = list(range(1, 51)) #50 replications in simulation

exp_stage = args.stage
parameters_config.update({'exp_stage': exp_stage})
is_all_config = args.allconfig

res_pct_list = []
for pct in cycle_duration_lognormal_percentile_list:
    parameters_dist.update({'cycle_duration_lognormal_percentile': pct})
    for rand_seed in rseeds:
        parameters_main.update({'rand_seed': rand_seed})
        parameters_main.update({'diagnosis_story_output': diagnosis_story})
        parameters_config.update({'enable_output_file': enable_output_file})

        file_name = '_'.join([exp_stage, 'all'+str(is_all_config), 'rseed'+str(rand_seed)])
        stdout_file_name = file_name + '.txt'
        stdout_file_name = os.path.join("output", stdout_file_name)
        if enable_output_file:
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
                        num_req, adm_rate, succ_order_rate, service_rate, req_stories = simul.run_and_report()

                        index = '-'.join([alloc, adm, disp])
                        res_index_list.append(index)
                        res = {'rseed': rand_seed, 'num_req': num_req, 'adm_rate': round(adm_rate,4),
                                         'succ_order_rate': round(succ_order_rate,4), 'service_rate': round(service_rate, 4)}
                        res_list.append(res)

                    elif alloc == 'EDD':
                        for lt in EDD_leadtime:
                            parameters_config.update({'EDD_lead_time': lt})
                            simul = MainSimulator(parameters_config, parameters_main, parameters_dist)
                            simul.initialize()
                            num_req, adm_rate, succ_order_rate, service_rate, req_stories = simul.run_and_report()

                            index = '-'.join([alloc, str(lt), adm, disp])
                            res_index_list.append(index)
                            res = {'rseed': rand_seed, 'num_req': num_req, 'adm_rate': round(adm_rate, 4),
                                   'succ_order_rate': round(succ_order_rate, 4), 'service_rate': round(service_rate, 4)}
                            res_list.append(res)

                    # save stories for each rseed, policy combination (one case)
                    if diagnosis_story == 1:
                        story_file_name = index + "_" + file_name + ".csv"
                        story_file_name = os.path.join("diagnosis", story_file_name)
                        req_stories.to_csv(story_file_name)
        if enable_output_file:
            sys.stdout.close()

        # #save result file (for each rseed, all policy in a run)
        # res_file_name = file_name + '.csv'
        # res_file_name = os.path.join("result", res_file_name)
        # res_df = pd.DataFrame(res_list, index=res_index_list)
        # res_df.to_csv(res_file_name)

        res.update({"policy": policy_comp, "pct": pct})
        res_pct_list.append(res)

# save all file (for each policy)
policy_res_file = os.path.join("result" , "policy_comp", exp_stage + "_" + policy_comp + ".csv")
res_pct_df = pd.DataFrame(res_pct_list)
res_pct_df.to_csv(policy_res_file)
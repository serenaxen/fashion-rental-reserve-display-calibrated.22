# Compute and compare multiple bounds for the numerical cases
# Xuening Wang
# 2022/05/29

import pandas as pd
import numpy as np
import sys
import os

from UB_models import knapsack_prob, jobshop_sch, jobshop_sch_time_constrs, schedule_compat_time_constr

def load_data(item_filename, req_filename):
    item_info = pd.read_csv(item_filename, index_col=0)
    item_info.sort_values(by=['item_id'])
    item_release_time = item_info['release_time'].to_list() #list index is item id by default
    n_num_items = len(item_release_time)

    req_info = pd.read_csv(req_filename, index_col=0)
    req_info.sort_values(by=['req_id'])
    req_order_time = req_info['order_time'].to_list()
    req_desired_time = req_info['desired_time'].to_list()
    req_rental_length = req_info['rental_length'].to_list()
    m_num_reqs = len(req_rental_length)

    return n_num_items, m_num_reqs, item_release_time, req_order_time, req_desired_time, req_rental_length

# UB 0 (estimation): item-time resources
def calc_itemtime_resource_UB_approx(n_num_items, T, item_release_time, req_rental_length):
    total_avai_time = T*n_num_items - sum(item_release_time)
    total_req_time = sum(req_rental_length)
    return total_avai_time/total_req_time

# UB 1: 0-1 knapsack and its LP relaxation
def calc_knapsack_UB(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol):
    obj_val, total_slack = knapsack_prob(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol)
    return obj_val

    # # slack regularization
    # print("Using slack regl!!!")
    # obj_val = knapsack_prob_slack_regl(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol)
    # return obj_val

# UB 2: jobshop scheduling
def calc_jobshop_sch_UB(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, Q, printsol):
    obj_val, item_slack_cnt = jobshop_sch(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol)
    return obj_val

    # # slack regularization
    # print("Using slack regl!!!")
    # obj_val = jobshop_sch_slack_regl(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, Q, printsol)
    # return obj_val

# UB 3: jobshop scheduling with desired time constraints
def calc_jobshop_sch_time_constraints_UB(n_num_items, m_num_reqs, T, item_release_time, req_order_time, req_desired_time, req_rental_length, Q, LPrelax, printsol):
    obj_val = jobshop_sch_time_constrs(n_num_items, m_num_reqs, T, item_release_time, req_order_time, req_desired_time, req_rental_length, Q, LPrelax, printsol)
    return obj_val

# UB 4: schedule compatibility with time constr (no release time constr)
def calc_schedule_compat_UB(n_num_items, m_num_reqs, T, req_order_time, req_desired_time, req_rental_length, Q, printsol=0):
    obj_val = schedule_compat_time_constr(n_num_items, m_num_reqs, T, req_order_time, req_desired_time, req_rental_length, Q, printsol=printsol, LPrelax=0)
    return obj_val

def scale_down_data(scale, n_num_items, m_num_reqs, item_release_time, req_desired_time, req_rental_length):
    n_num_items_scale = int(n_num_items * scale)
    item_release_time_scale = item_release_time[:n_num_items_scale]

    req_desired_time_scale = []
    req_rental_length_scale = []
    m_num_reqs_scale = 0
    for i in range(m_num_reqs):
        rand = np.random.rand()
        if rand <= scale:  # maintain w.p. scale
            m_num_reqs_scale += 1
            req_desired_time_scale.append(req_desired_time[i])
            req_rental_length_scale.append(req_rental_length[i])

    return n_num_items_scale, m_num_reqs_scale, item_release_time_scale, req_desired_time_scale, req_rental_length_scale


item_data_prefix = "data/itemdata_rseed"
req_data_prefix = "data/reqdata_rseed"
rseeds = list(range(1, 51)) #All results: range(1, 31)
printsol = 1

T = 182

Q = 5*T

m_num_reqs_list = []
ub0_list = []
ub1_list = []
ub2_list = []
for rs in rseeds:
    item_filename = item_data_prefix + str(rs) + '.csv'
    req_filename = req_data_prefix + str(rs) + '.csv'
    n_num_items, m_num_reqs, item_release_time, req_order_time, req_desired_time, req_rental_length = load_data(item_filename, req_filename)
    m_num_reqs_list.append(m_num_reqs)

    ub0 = calc_itemtime_resource_UB_approx(n_num_items, T, item_release_time, req_rental_length)
    ub0_list.append(round(ub0,4))

    ub1 = calc_knapsack_UB(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol=0)
    ub1_list.append(round(ub1, 4))

    ub2 = calc_jobshop_sch_UB(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, Q, printsol=0)
    ub2_list.append(round(ub2, 4))


ub_LPrelax = 0
ub3_scale = 1
ub3_replica = 1

ub3_list = []
ub3_m_scale_list = []
ub4_list = []
m_num_reqs_list = []
for rs in rseeds:
    print("\nRunning ub3 & ub4 on rseed %d..."%rs)
    item_filename = item_data_prefix + str(rs) + '.csv'
    req_filename = req_data_prefix + str(rs) + '.csv'
    n_num_items, m_num_reqs, item_release_time, req_order_time, req_desired_time, req_rental_length = load_data(item_filename, req_filename)
    m_num_reqs_list.append(m_num_reqs)

    # # UB3 - jobshop with time constr
    # for r in range(ub3_replica):
    #     if ub3_scale < 1:
    #         n_num_items, m_num_reqs, item_release_time, req_desired_time, req_rental_length \
    #             = scale_down_data(ub3_scale, n_num_items, m_num_reqs, item_release_time, req_desired_time, req_rental_length)
    #     ub3 = calc_jobshop_sch_time_constraints_UB(n_num_items, m_num_reqs, T, item_release_time, req_order_time, req_desired_time, req_rental_length, Q, ub_LPrelax, printsol)
    #
    #     ub3_list.append(ub3)
    #     ub3_m_scale_list.append(m_num_reqs)

    # UB4 - schedule compatibility double time constr
    ub4 = calc_schedule_compat_UB(n_num_items, m_num_reqs, T, req_order_time, req_desired_time, req_rental_length, Q, printsol=printsol)
    ub4_list.append(ub4)


# REPORT
avg_m_num_reqs = np.mean(m_num_reqs_list)
print("Avg num reqs: ", avg_m_num_reqs)

print("\nEstimation in terms of resources")
print(round(np.mean(ub0_list), 4))

print("\nUB1 - Knapsack")
srate1 = [ub1_list[i]/m_num_reqs_list[i] for i in range(len(ub1_list))]
print(round(np.mean(srate1), 4))

print("\nUB2 - Jobshop")
srate2 = [ub2_list[i]/m_num_reqs_list[i] for i in range(len(ub2_list))]
print(round(np.mean(srate2), 4))

# print("\nUB3 - Jobshop Time Constrs, Scale %.2f, Replica %d" %(ub3_scale, ub3_replica))
# srate3 = [ub3_list[i]/ub3_m_scale_list[i] for i in range(len(ub3_list))]
# print(round(np.mean(srate3), 4))

print("\nUB4 - Jobshop Time Constrs - One Item")
srate4 = [ub4_list[i]/m_num_reqs_list[i] for i in range(len(ub4_list))]
print(round(np.mean(srate4), 4))
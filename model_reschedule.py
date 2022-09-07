# Stores every schedule/reschedule model for the nominal schedule approach
# XN Wang
# 2022/08/17

import gurobipy as grb
from gurobipy import GRB

def model_complete_reschedule(req_index_list, ns_start, ns_length, num_items, item_exp_release_time, t, T):
    # config
    Q = 5 * T

    item_list = list(range(num_items))
    L_mat_delivery_window_dict = {}
    R_mat_return_window_dict = {}
    for j in req_index_list:
        for k in req_index_list:
            L_mat_delivery_window_dict[j, k] = 1 if ns_start[j] <= ns_start[k] else 0
            R_mat_return_window_dict[j, k] = 1 if ns_start[j] + ns_length[j] <= ns_start[k] + ns_length[k] else 0

    model = grb.Model("complete reschedule")

    y = model.addVars(req_index_list, vtype=GRB.BINARY, name='yj')
    x = model.addVars(item_list, req_index_list, vtype=GRB.BINARY, name='xij')

    model.setObjective(sum(y[j] for j in req_index_list), GRB.MAXIMIZE)
    model.addConstrs(sum(x[i,j] for i in item_list) == y[j] for j in req_index_list)
    model.addConstrs((ns_length[j] - (1 - L_mat_delivery_window_dict[j,k])*Q - (2-x[i,j]-x[i,k])*Q <= ns_start[k] - ns_start[j])\
                     for i in item_list for j in req_index_list for k in req_index_list if j!= k)
    model.addConstrs((ns_length[j] - (1 - R_mat_return_window_dict[j,k])*Q - (2-x[i,j]-x[i,k])*Q <= ns_start[k] - ns_start[j])\
                     for i in item_list for j in req_index_list for k in req_index_list if j != k)
    model.addConstrs((item_exp_release_time[i]-(1-x[i,j])*Q <= ns_start[j]) for i in item_list for j in req_index_list)

    # auxiliary constr: every nominal schedule should start after current time
    model.addConstrs(y[j] == 0 for j in req_index_list if ns_start[j] < t)

    model.setParam('OutputFlag', 0)
    model.optimize()
    # print("Model runtime: ", model.Runtime)
    if model.status == GRB.OPTIMAL:
        updated_assign = {j:i for j in req_index_list for i in item_list if model.getVarByName("xij[%d,%d]"%(i,j)).X == 1}
        return model.objVal, updated_assign
    else:
        print("Model is either infeasible or unbounded. DEBUG!")
        return 0, {}


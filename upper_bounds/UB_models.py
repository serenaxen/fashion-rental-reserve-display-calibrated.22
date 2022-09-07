# Clairvoyant optimal scheduling
# Xuening Wang
# 2022/05/28

import gurobipy as grb
import numpy as np
from gurobipy import GRB

def knapsack_prob(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol=0):
    reqs = list(range(m_num_reqs))

    model = grb.Model("knapsack")

    y = model.addVars(reqs, name='yj', vtype=GRB.BINARY)

    model.setObjective(sum(y[j] for j in reqs), GRB.MAXIMIZE)

    model.addConstr(grb.quicksum(y[j]*req_rental_length[j] for j in reqs) <= n_num_items*T - sum(item_release_time), name='cpcty')

    model.optimize()
    obj_val = print_solution(model)

    if obj_val:
        # Slack variables
        cap_constr = model.getConstrByName('cpcty')
        total_slack = cap_constr.Slack

        if printsol:
            for j in reqs:
                y_val = y[j].x
                if y_val == 0:
                    print('Req %d NOT fulfilled, length %d' % (j, req_rental_length[j]))

        return obj_val, total_slack

def jobshop_sch(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol=0):
    items = list(range(n_num_items))
    reqs = list(range(m_num_reqs))

    model = grb.Model("jobshop sch")

    y = model.addVars(reqs, name='yj', vtype=GRB.BINARY)
    x = model.addVars(items, reqs, name='xij', vtype=GRB.BINARY)

    model.setObjective(sum(y[j] for j in reqs), GRB.MAXIMIZE)

    model.addConstrs(grb.quicksum(x[i, j] for i in items) == y[j] for j in reqs)
    model.addConstrs((grb.quicksum(x[i, j]*req_rental_length[j] for j in reqs) <= T - item_release_time[i] for i in items), name='item_cpcty')

    model.optimize()
    obj_val = print_solution(model)

    if obj_val:
        # Slack variables
        item_slack_cnt = 0
        for i in items:
            item_cpcty_constr = model.getConstrByName('item_cpcty[%d]'%i)
            if item_cpcty_constr.Slack > 0:
                item_slack_cnt += 1

        if printsol:
            for i in items:
                for j in reqs:
                    x_val = x[i,j].x
                    if x_val == 1:
                        print('Req %d fulfilled by item %d (release %d), length %d' % (j, i, item_release_time[i], req_rental_length[j]))

        return obj_val, item_slack_cnt

def jobshop_sch_time_constrs(n_num_items, m_num_reqs, T, item_release_time, req_order_time, req_desired_time, req_rental_length, Q, LPrelax = 0, printsol=0):
    # construct model
    items = list(range(n_num_items))
    reqs = list(range(m_num_reqs))

    model = grb.Model("jobshop sch time constrs")

    # variables
    binary_vtype = GRB.CONTINUOUS if LPrelax == 1 else GRB.BINARY
    c_vtype = GRB.CONTINUOUS if LPrelax == 1 else GRB.INTEGER

    y = model.addVars(reqs, name='yj', lb=0, ub=1, vtype=binary_vtype)
    x = model.addVars(items, reqs, name='xij', lb=0, ub=1, vtype=binary_vtype)

    # TODO: 7/6 experiment goes here (remove z and w, replace with only x and theta)
    # z = model.addVars(items, reqs, reqs, name='zijk', lb=0, ub=1, vtype=binary_vtype)
    # w = model.addVars(items, reqs, reqs, name='wijk', lb=0, ub=1, vtype=binary_vtype)
    theta = model.addVars(reqs, reqs, name='theta', vtype=binary_vtype)

    c = model.addVars(reqs, vtype=c_vtype, lb=1)

    model.setObjective(sum(y[j] for j in reqs), GRB.MAXIMIZE)

    # constraints
    model.addConstrs(grb.quicksum(x[i, j] for i in items) == y[j] for j in reqs)

    # TODO: 7/6 experiment goes here (remove z and w, replace with only x and theta)
    # model.addConstrs(z[i, j, k] <= x[i, j] for i in items for j in reqs for k in reqs if j != k)
    # model.addConstrs(z[i, j, k] <= x[i, k] for i in items for j in reqs for k in reqs if j != k)
    # model.addConstrs(z[i, j, k] >= x[i, j] + x[i, k] - 1 for i in items for j in reqs for k in reqs if j != k)
    #
    # model.addConstrs(w[i, j, k] <= z[i, j, k] for i in items for j in reqs for k in reqs if j != k)
    # model.addConstrs(w[i, j, k] + w[i, k, j] == z[i, j, k] for i in items for j in reqs for k in reqs if j != k)
    model.addConstrs(
        c[j] + req_rental_length[j] <= c[k] + (1-theta[j,k]) * Q + (2-x[i,j]-x[i,k])*Q for i in items for j in reqs for k in reqs if j != k)
    model.addConstrs(theta[j,k] + theta[k,j] == 1 for j in reqs for k in reqs if j<k)
    model.addConstrs(theta[j,j] == 0 for j in reqs)


    # model.addConstrs(c[j] + req_rental_length[j] >= c[k] - (1-w[i,j,k])*Q for i in items for j in reqs for k in reqs if j != k)
    # #TODO: <= changed to == as a valid cut
    # model.addConstrs(c[j] + req_rental_length[j] <= T + (1-y[j]) * Q for j in reqs)

    model.addConstrs(item_release_time[i] <= c[j] + (1 - x[i, j]) * Q for i in items for j in reqs)

    model.addConstrs(c[j] <= req_desired_time[j] + (1 - y[j]) * Q for j in reqs)
    model.addConstrs(c[j] <= T + (1 - y[j]) for j in reqs)
    model.addConstrs(c[j] >= (T + 1) * (1 - y[j]) for j in reqs)

    # 07/05 adding to accelarate
    model.addConstrs(c[j] >= req_order_time[j] for j in reqs)


    # TODO: 7/6 experiment goes here (remove z and w, replace with only x and theta)
    # ## auxiliary constrs
    # model.addConstrs(z[i, j, j] == 0 for i in items for j in reqs)
    # model.addConstrs(w[i, j, j] == 0 for i in items for j in reqs)

    # model.setParam("OutputFlag", 0)

    # solve and report
    model.optimize()
    obj_val = print_solution(model)
    if obj_val:
        if printsol:
            for i in items:
                for j in reqs:
                    x_val = x[i,j].x
                    if x_val == 1:
                        print('Req %d fulfilled by item %d' % (j, i))
                        print('order time: %d, desired time: %d, commitment time: %d, length: %d' %(req_order_time[j], req_desired_time[j], c[j].x, req_rental_length[j]))
        return obj_val

def schedule_compat_time_constr(n_num_items, m_num_reqs, T, req_order_time, req_desired_time, req_rental_length, Q, printsol=0, LPrelax=0):
    # prepare data
    L_mat_delivery_window = np.zeros((m_num_reqs, m_num_reqs))
    R_mat_return_window = np.zeros((m_num_reqs, m_num_reqs))
    for j in range(m_num_reqs):
        for k in range(m_num_reqs):
            L_mat_delivery_window[j][k] = 1 if req_desired_time[j] <= req_desired_time[k] else 0
            R_mat_return_window[j][k] = 1 if req_desired_time[j] + req_rental_length[j] <= req_desired_time[k] + req_rental_length[k] else 0

    # construct model
    items = list(range(n_num_items))
    reqs = list(range(m_num_reqs))

    model = grb.Model("schedule compat")

    y = model.addVars(reqs, name='yj', lb=0, ub=1, vtype=GRB.BINARY)
    x = model.addVars(items, reqs, name='xij', lb=0, ub=1, vtype=GRB.BINARY)

    model.setObjective(sum(y[j] for j in reqs), GRB.MAXIMIZE)

    # constraints
    model.addConstrs(grb.quicksum(x[i, j] for i in items) == y[j] for j in reqs)
    model.addConstrs((req_desired_time[k] - req_desired_time[j] >= req_rental_length[j] - (1 - L_mat_delivery_window[j][k]) * Q - (2 - x[i,j] - x[i,k]) * Q) for i in items for j in reqs for k in reqs if j != k)
    model.addConstrs((req_desired_time[k] - req_desired_time[j] >= req_rental_length[j] - (1 - R_mat_return_window[j][k]) * Q - (2 - x[i, j] - x[i, k]) * Q) for i in items for j in reqs for k in reqs if j != k)

    # solve and report
    model.optimize()
    obj_val = print_solution(model)
    if obj_val:
        if printsol:
            for i in items:
                for j in reqs:
                    x_val = x[i, j].x
                    if x_val == 1:
                        print('Req %d fulfilled by item %d' % (j, i))
        return obj_val

def knapsack_prob_slack_regl(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, printsol=0):
    reqs = list(range(m_num_reqs))

    model = grb.Model("knapsack")

    y = model.addVars(reqs, name='yj', vtype=GRB.BINARY)

    z = model.addVar(name='z')
    v = model.addVar(name='v')

    model.setObjective(sum(y[j] for j in reqs) + v, GRB.MAXIMIZE)
    model.addConstr(grb.quicksum(y[j]*req_rental_length[j] for j in reqs) + z == n_num_items*T - sum(item_release_time), name='cpcty')

    model.addConstr(v <= z)
    model.addConstr(v <= n_num_items)

    model.optimize()
    obj_val = print_solution(model)

    if obj_val:
        if printsol:
            for j in reqs:
                y_val = y[j].x
                if y_val == 0:
                    print('Req %d NOT fulfilled, length %d' % (j, req_rental_length[j]))

        return obj_val

def jobshop_sch_slack_regl(n_num_items, m_num_reqs, T, item_release_time, req_rental_length, Q, printsol=0):
    items = list(range(n_num_items))
    reqs = list(range(m_num_reqs))

    model = grb.Model("jobshop sch")

    y = model.addVars(reqs, name='yj', vtype=GRB.BINARY)
    x = model.addVars(items, reqs, name='xij', vtype=GRB.BINARY)

    z = model.addVars(items, name='zi')
    w = model.addVars(items, name='wi', vtype=GRB.BINARY)

    model.setObjective(sum(y[j] for j in reqs) + sum(w[i] for i in items), GRB.MAXIMIZE)

    model.addConstrs(grb.quicksum(x[i, j] for i in items) == y[j] for j in reqs)
    model.addConstrs((grb.quicksum(x[i, j]*req_rental_length[j] for j in reqs) +z[i] == T - item_release_time[i] for i in items), name='item_cpcty')

    model.addConstrs(w[i] <= Q * z[i] for i in items)

    model.optimize()
    obj_val = print_solution(model)

    if obj_val:
        if printsol:
            for i in items:
                for j in reqs:
                    x_val = x[i,j].x
                    if x_val == 1:
                        print('Req %d fulfilled by item %d (release %d), length %d' % (j, i, item_release_time[i], req_rental_length[j]))

        return obj_val

def print_solution(model):
    if model.status == GRB.OPTIMAL:
        obj_val = model.objVal
        print('\nObj (to max): %g' % model.objVal)
        print('Run time: ', model.Runtime)
        return obj_val

    elif model.status == GRB.INFEASIBLE:
        print('Model is infeasible')
    elif model.status == GRB.UNBOUNDED:
        print('Model is unbounded')
    else:
        print('Optimization ended with status %d' % model.status)
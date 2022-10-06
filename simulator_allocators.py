# Implement allocation policies
# Xuening Wang
# 2022/04/14

from simulator_classes import *

def FOFS_alloc(inventory, orders, length_of_delivery, t): #EDIT FOFS CODES, SHOULD EDIT EDD TOO
    print("\nAllocation control with FOFS policy")

    current_inv = inventory.current_inv
    if current_inv <= 0:
        return [], [], []

    orders = [o for o in orders if o.status == 0 and o.desired_time >= t+length_of_delivery] #all the admitted but not commited orders (+extra validity check)
    sorted_orders = sort_order_list_by_t(orders)
    inv_items = inventory.take_inv_items_list()
    print("  current inv: %d"%current_inv)
    for od in sorted_orders:
        print("  uncommited order: %d, order time: %d, desired time: %d"%(od.req_index, od.order_time, od.desired_time))

    commit_cnt = 0
    num_orders = len(orders)

    commited_items = []
    desired_dates = []
    realized_cycle_duration = []
    while current_inv > 0 and commit_cnt < num_orders:
        item_index = inv_items[commit_cnt].index
        sorted_orders[commit_cnt].commit_order(item_index, t)
        commited_items.append(item_index)
        desired_dates.append(sorted_orders[commit_cnt].desired_time)
        realized_cycle_duration.append(sorted_orders[commit_cnt].realized_cycle_duration)

        current_inv -= 1
        commit_cnt += 1

    return commited_items, desired_dates, realized_cycle_duration

def EDD_alloc(inventory, orders, length_of_delivery, t, lead_time):
    print("\nAllocation control with EDD policy, lead time %d" %lead_time)

    current_inv = inventory.current_inv
    if current_inv <= 0:
        return [], [], []

    orders = [o for o in orders if o.status == 0 and o.desired_time >= t+length_of_delivery] #+extra validity check
    orders = [o for o in orders if t >= o.desired_time - lead_time]
    sorted_orders = sort_order_list_by_s(orders)
    inv_items = inventory.take_inv_items_list()
    print("  current inv: %d" % current_inv)
    for od in sorted_orders:
        print("  uncommited eligible order: %d, order time: %d, desired time: %d"%(od.req_index, od.order_time, od.desired_time))
    commit_cnt = 0
    num_orders = len(orders)

    commited_items = []
    desired_dates = []
    realized_cycle_duration = []
    while current_inv > 0 and commit_cnt < num_orders:
        item_index = inv_items[commit_cnt].index
        sorted_orders[commit_cnt].commit_order(item_index, t)
        commited_items.append(item_index)
        desired_dates.append(sorted_orders[commit_cnt].desired_time)
        realized_cycle_duration.append(sorted_orders[commit_cnt].realized_cycle_duration)

        current_inv -= 1
        commit_cnt += 1

    return commited_items, desired_dates, realized_cycle_duration

def sort_order_list_by_t(orders):
    return sorted(orders, key=lambda o: o.order_time)

def sort_order_list_by_s(orders):
    return sorted(orders, key=lambda o: o.desired_time)

def NS_alloc(inventory, orders, schedule, length_of_delivery, median_cycle_duration, t):
    committed_items = []

    committed_orders = []
    failed_orders = []
    due_orders, assign_info = schedule.check_order_to_commit_now(t+length_of_delivery)
    reverse_assign_info = {} # auxiliary for item info updates
    for req_index in due_orders:
        item_index = assign_info[req_index]
        if inventory.report_one_item_status(item_index) == 1: #due + item in stock, commit
            committed_orders.append(req_index)
            committed_items.append(item_index)
            schedule.commit_order_one(req_index, median_cycle_duration, t) # include a release time update in the schedule
            reverse_assign_info.update({item_index: req_index})
        else:
            failed_orders.append(req_index)
            schedule.fail_order_one(req_index)

    # update info for committed/failed orders
    od_desired_dates = {} #auxiliary for item info updates
    od_realized_cycle_duration = {} #auxiliary for item info updates
    for od in orders:
        if od.req_index in committed_orders:
            od.commit_order(assign_info[od.req_index], t)

            od_desired_dates.update({od.req_index: od.desired_time})
            od_realized_cycle_duration.update({od.req_index: od.realized_cycle_duration})

        elif od.req_index in failed_orders:
            od.fail_order(t)

    # update info for committed items
    desired_dates = []
    realized_cycle_duration = []
    for item_index in committed_items:
        assign_req = reverse_assign_info[item_index]
        desired_dates.append(od_desired_dates[assign_req])
        realized_cycle_duration.append(od_realized_cycle_duration[assign_req])

    return committed_items, desired_dates, realized_cycle_duration

# # TEST BELOW
# order1 = CustomerOrder(0, 1, 3)
# order2 = CustomerOrder(1, 3, 7)
# order3 = CustomerOrder(2, 5, 6)
# order4 = CustomerOrder(3, 2, 10)
# orders = [order1, order2, order3, order4]
# new_orders = sort_order_list_by_s(orders)
# print([o.req_index for o in new_orders])
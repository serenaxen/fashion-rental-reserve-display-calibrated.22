# Essential classes for simulator
# Xuening Wang
# 2022/04/14

from random_generators import *
from model_reschedule import *

class ProductItem:
    def __init__(self, index):
        self.index = index
        self.status = 1 #1 for in inventory, 0 for on the way
        self.return_periods = 0
        self.cir_cnt = 0
        self.exp_regular_return_periods = 0

    def init_out(self, rp, errp):
        self.status = 0
        self.return_periods = rp
        self.exp_regular_return_periods = errp
        self.cir_cnt += 1

    def send_out(self, rp, median_cycle_duration):
        if self.status == 1:
            self.status = 0
            self.return_periods = rp
            self.exp_regular_return_periods = median_cycle_duration
            self.cir_cnt += 1

    def update_rp_errp_per_period(self):
        if self.status == 0 and self.return_periods > 0:
           self.return_periods -= 1
           self.exp_regular_return_periods -= 1 #may be negative if delayed

    def check_in(self):
        if self.status == 0 and self.return_periods == 0:
            self.status = 1
            self.exp_regular_return_periods = 0
            return self.index

class Inventory:
    def __init__(self, paras):
        self.paras = paras
        # Create item set(list)
        self.num_items = paras['total_items']
        self.items = [ProductItem(i) for i in range(self.num_items)]

    def initialize(self):
        # starting_inv = self.paras['starting_inv']
        # num_out = self.num_items - starting_inv
        #
        # regular_return_periods = self.paras['regular_return_periods']
        # return_delay_geom_mean = self.paras['return_delay_geom_mean']
        # return_delay_seq = geom_discrete_seq(num_out, return_delay_geom_mean)
        # for j in range(num_out):
        #     errp = uniform_discrete_one(1, regular_return_periods + 1)
        #     self.items[j].init_out(rp = errp + return_delay_seq[j], errp = errp)  # first random number generated here!

        # 9/6 change: no regular_return_periods and delays, replaced with only cycle_duration
        # use only a unif(1, median_cycle_duration+1)
        # and return period (rp) = exp return period (errp), we know exactly when they will come back
        # in the parameters after calibration, num_out should be 0 (so no change essentially)
        starting_inv = self.paras['starting_inv']
        self.current_inv = starting_inv

        num_out = self.num_items - starting_inv
        cycle_duration_lognormal_median = self.paras['cycle_duration_lognormal_median']
        if num_out > 0:
            for j in range(num_out):
                errp = uniform_discrete_one(1, cycle_duration_lognormal_median+1)
                self.items[j].init_out(rp = errp, errp = errp) # first random number generated here!

    def update_rp_errp_per_period(self):
        for it in self.items:
            it.update_rp_errp_per_period()

    def receive_returns(self):
        return_items = []
        for it in self.items:
            id = it.check_in()
            if id:
                return_items.append(id)
        self.current_inv += len(return_items)
        print("Returned items", return_items)
        return return_items

    def take_inv_items_list(self):
        return [it for it in self.items if it.status == 1]

    def sendout_items(self, item_index_list, rp_list):
        median_cycle_duration = self.paras['cycle_duration_lognormal_median']
        for i in range(len(item_index_list)):
            self.items[item_index_list[i]].send_out(rp_list[i], median_cycle_duration)
            self.current_inv -= 1
        print("Send out items: ", item_index_list)
        print("Will be back in: ", rp_list, " (realized), expected to be back in: ", median_cycle_duration)

    def predict_future_inv_median_cycle(self, time, future_time, inv_occup_record, uncmtd_cnt, use_uncmtd=0):
        future_inv = 0
        for it in self.items: # inv + on time now could come back before a future time
            if it.status == 1:
                future_inv += 1
            elif it.status == 0:
                if time + it.exp_regular_return_periods <= future_time: # note: all the overdue items are counted too
                    future_inv += 1

        num_occupied_items = inv_occup_record[future_time]
        future_inv = future_inv - num_occupied_items

        if use_uncmtd == 1:
            future_inv = future_inv - uncmtd_cnt

        return future_inv

    def report_current_inv(self):
        print("Current inv quantity:", self.current_inv)
        return self.current_inv

    def report_current_inv_id(self):
        in_stock_items = [it.index for it in self.items if it.status == 1]
        return in_stock_items

    def report_one_item_status(self, index):
        return self.items[index].status

    def report_return_flow(self):
        return [[it.index, it.exp_regular_return_periods, it.return_periods] for it in self.items if it.status == 0]

    def report_exp_return_flow(self):
        return [[it.index, it.exp_regular_return_periods] for it in self.items if it.status == 0]

    def report_max_item_return_time(self):
        max_time = 0
        for it in self.items:
            if it.status == 0 and it.return_periods > max_time:
                max_time = it.return_periods
        return max_time

    def report_item_cir_stats(self):
        item_cir_cnt = []
        for it in self.items:
            item_cir_cnt.append(it.cir_cnt)
        avg_cir_cnt = sum(item_cir_cnt)/self.num_items
        return avg_cir_cnt, item_cir_cnt

class CustomerRequest:
    def __init__(self, index, order_time, desired_periods, realized_cycle_duration):
        self.index = index
        self.order_time = order_time
        self.desired_periods = desired_periods
        self.desired_time = order_time + desired_periods
        self.status = 0  #0 for new, 1 for admitted/active order, -1 for rejected

        self.realized_cycle_duration = realized_cycle_duration

    def admit(self):
        self.status = 1

    def reject(self):
        self.status = -1


class CustomerOrder: #only for admitted (available & chosen) requests
    def __init__(self, req_index, order_time, desired_periods, realized_cycle_duration):
        self.req_index = req_index
        self.order_time = order_time
        self.desired_periods = desired_periods
        self.desired_time = order_time + desired_periods
        self.status = 0 # 0 for "admit"

        self.realized_cycle_duration = realized_cycle_duration

    def commit_order(self, item_index, commit_time):
        self.status = 1 # 1 for "commit"
        self.commit_item = item_index
        self.commit_time = commit_time
        print("  assign item %d to order %d" % (item_index, self.req_index))

    def finish_order(self):
        self.status = 2 # 2 for "success"
        print("  order %d successful, desired time %s :)" % (self.req_index, self.desired_time))

    def fail_order(self):
        self.status = -2 # -2 for "failure"
        print("  order %d expired and failed, desired time %s :(" %(self.req_index, self.desired_time))

    # def save_later_order(self):
    #     self.status = 5
    #     print("  order saved for later: %d"%self.req_index)

class NominalSchedule:
    def __init__(self):
        self.ns_start = {}
        self.ns_length = {}
        self.ns_assign_item = {}
        self.on_schedule_req_list = []

    def initialize(self, initial_rt_flow):
        self.num_items = len(initial_rt_flow)
        self.item_exp_release_time = {rt[0]: rt[2] for rt in initial_rt_flow} #key-value in form of item_index: errp. see Inventory.report__return_flow for details

    def reschedule_for_one_new_request(self, cr, median_cycle_duration, t, T): #t stands for current time
        new_req_index = cr.index
        new_req_desired_time = cr.desired_time
        new_req_exp_length = median_cycle_duration

        update_assign = self.__model_complete_reschedule_for_new_request(new_req_index, new_req_desired_time, new_req_exp_length, t, T)
        if update_assign: # available YES
            self.on_schedule_req_list.append(new_req_index)
            self.ns_start.update({new_req_index: new_req_desired_time})
            self.ns_length.update({new_req_index: new_req_exp_length})
            # use newly solved schedule as the nominal schedule for all requests
            self.ns_assign_item = update_assign
            return True # can accommodate the new request
        else:
            return False

    def __model_complete_reschedule_for_new_request(self, new_req_index, new_req_desired_time, new_req_exp_length, t, T):
        req_index_list = self.on_schedule_req_list.copy()
        req_index_list.append(new_req_index)

        ns_start = self.ns_start.copy()
        ns_start.update({new_req_index: new_req_desired_time})
        ns_length = self.ns_length.copy()
        ns_length.update({new_req_index: new_req_exp_length})

        obj_val, updated_assign = model_complete_reschedule(req_index_list, ns_start, ns_length,
                                            self.num_items, self.item_exp_release_time.copy(), t, T)

        if obj_val == len(self.on_schedule_req_list) + 1: # can accommodate the new request
            return updated_assign

    def check_order_to_commit_now(self, t):
        due_orders = []
        assign_info = {}
        for req_index, start_time in self.ns_start.items():
            if start_time == t:
                due_orders.append(req_index)
                assign_info.update({req_index: self.ns_assign_item[req_index]}) #assigned item id
        return due_orders, assign_info

    def commit_order_one(self, req_index, median_cycle_duration, t):
        # update release time for the attributed item
        item_index = self.ns_assign_item[req_index]
        self.item_exp_release_time.update({item_index: t+median_cycle_duration})
        self.__remove_nominal_schedule_one(req_index)

    def fail_order_one(self, req_index):
        self.__remove_nominal_schedule_one(req_index)

    def __remove_nominal_schedule_one(self, req_index):
        self.on_schedule_req_list.remove(req_index)
        self.ns_start.pop(req_index)
        self.ns_length.pop(req_index)
        self.ns_assign_item.pop(req_index)

    def extend_release_time_for_delay(self, item_index, t, exp_delay_window):
        self.item_exp_release_time.update({item_index: t+exp_delay_window})
        for req_index, assign_item in self.ns_assign_item.items():
            if assign_item == item_index and self.ns_start[req_index] < self.item_exp_release_time[item_index]:
                affected_req_index = req_index
                return affected_req_index #Note: here we may have a invalid schedule before further processing

    def reschedule_for_one_item_delay(self, affected_req_index):
        updated_assign = self.__model_complete_reschedule_for_delay()
        if updated_assign: #available YES
            self.ns_assign_item = updated_assign
            return True
        else: # have to fail the affected req
            self.fail_order_one(affected_req_index)
            return False

    def __model_complete_reschedule_for_delay(self):
        obj_val, updated_assign = model_complete_reschedule(self.on_schedule_req_list.copy(), self.ns_start.copy(), self.ns_length.copy(),
                                                            self.num_items, self.item_exp_release_time.copy(), t, T)

        if obj_val == len(self.on_schedule_req_list): # can resolve conflict
            return updated_assign

    # def check_schedule_validity(self): # for safety
    # TODO: do a overall debug after one time reporting

# TEST BELOW (outdated)
# initial_rt_flow = [[0, 3, 1], [1, 0, 0], [2, 5, 3]]
# regular_return_period = 2
# exp_delay_window = 2
# T = 5
#
# schedule = NominalSchedule()
# schedule.initialize(initial_rt_flow)
# t=1
# cr_1 = CustomerRequest(index=1, order_time=1, desired_periods=1, realized_return_delay=2) #desired at time 2
# schedule.reschedule_for_one_new_request(cr_1, regular_return_period, exp_delay_window, t, T)
# cr_2 = CustomerRequest(index=2, order_time=1, desired_periods=2, realized_return_delay=2) #desired at time 3
# schedule.reschedule_for_one_new_request(cr_2, regular_return_period, exp_delay_window, t, T)
# cr_3 = CustomerRequest(index=3, order_time=1, desired_periods=4, realized_return_delay=2) #desired at time 4
# schedule.reschedule_for_one_new_request(cr_3, regular_return_period, exp_delay_window, t, T)
#
# cr_4 = CustomerRequest(index=4, order_time=1, desired_periods=0, realized_return_delay=2)
# schedule.reschedule_for_one_new_request(cr_4, regular_return_period, exp_delay_window, t, T)
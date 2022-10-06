# Main timeline simulator
# Xuening Wang
# 2022/04/14

import os
import pandas as pd

from simulator_classes import *
from simulator_allocators import *
from random_generators import *

# What happened in one period:
## 1. count beginning inv
## 2. receive returns
## 3. show availability and process requests (admission/rejection for now)
## 4. allocation/commit orders
## 5. remove committed items

class MainSimulator:

    # Load configurations
    def __init__(self, paras_config, paras_main, paras_dist):
        self.paras = {}
        self.paras.update(paras_config)
        self.paras.update(paras_main)
        self.paras.update(paras_dist)

        self.is_seed = self.paras["is_seed"]
        self.rand_seed = self.paras['rand_seed'] if self.is_seed else None
        np.random.seed(self.rand_seed)

        # LOG
        print("\n\n-----Parameters initialized-----: \n", self.paras)

    # Initialize inventory and requests; contains all random number generators
    def initialize(self):
        self.time_horizon = self.paras['time_horizon']

        self.inventory = Inventory(self.paras)
        self.inventory.initialize()

        req_arr_lmbd = self.paras['customer_request_poisson_rate']
        req_arr_seq = poisson_arr_discrete_seq(self.time_horizon, req_arr_lmbd)
        num_req_base = len(req_arr_seq)
        req_des_time_n, req_des_time_p = self.paras['customer_request_desired_time_binomial_n'], self.paras['customer_request_desired_time_binomial_p']
        req_des_time_seq = binomial_discrete_seq(num_req_base, req_des_time_n, req_des_time_p)
        self.median_cycle_duration = self.paras["cycle_duration_lognormal_median"]
        self.cycle_duration_lognormal_mu = self.paras['cycle_duration_lognormal_mu']
        self.cycle_duration_lognormal_sigma = self.paras['cycle_duration_lognormal_sigma']
        req_realized_cycle_seq = lognormal_rounded_up_seq(num_req_base, self.cycle_duration_lognormal_mu, self.cycle_duration_lognormal_sigma)
        self.requests = [CustomerRequest(i, req_arr_seq[i], req_des_time_seq[i], req_realized_cycle_seq[i]) for i in range(num_req_base)]

        self.remove_req_overtime()
        self.remove_req_desired_periods_0() #to fix FOFS <100% succ order rate. only valid when length_of_delivery>0
        self.num_req = len(self.requests)
        self.req_scan_index = 0

        self.length_of_delivery = self.paras['length_of_delivery']

        self.orders = []

        # REPORT
        print("\n-----Initialization Phase-----\n")
        print("Total inv: %d, In stock inv: %d" %(self.inventory.num_items, self.inventory.report_current_inv()))
        self.cr_full_list = [[cr.index, cr.order_time, cr.order_time+cr.desired_periods, cr.realized_cycle_duration] for cr in self.requests]
        print("Customer request full list: ")
        for cr in self.cr_full_list:
            print("  index: %d, will order at time: %d, desired arrival at time: %d; realized cycle duration: %d" %(cr[0], cr[1], cr[2], cr[3]))
        self.initial_instock_items = self.inventory.report_current_inv_id()
        self.initial_rt_flow = self.inventory.report_return_flow()
        print("Item returning flow: ")
        for rt in self.initial_rt_flow:
            print("  index: %d, exp return: %d, will return: %d" %(rt[0], rt[1], rt[2]))


    def run_and_report(self, debug_truncate_time = None):
        time_horizon = self.time_horizon
        if debug_truncate_time: # FOR DEBUGGING
            time_horizon = debug_truncate_time

        # Policy search and experiment
        disp_policy = self.paras['display_policy_wrt']
        admit_policy = self.paras['admission_policy']
        alloc_policy = self.paras['allocation_policy']

        # (8/17) create and initial a NominalSchedule class for the nominal schedule approach
        if alloc_policy == "NomiSch":
            self.nominal_schedule = NominalSchedule()
            self.nominal_schedule.initialize(self.inventory.num_items, self.initial_rt_flow)

        for t in range(time_horizon):
            self.update_one_period(t, disp_policy, admit_policy, alloc_policy)

        EDD_lead_time = self.paras['EDD_lead_time']
        self.report_config(disp_policy, admit_policy, alloc_policy, EDD_lead_time)
        num_req, adm_rate = self.report_admission_rate()
        succ_order_rate, service_rate = self.report_succ_order_rate()
        self.report_item_cir_stats()

        # EXPORT case static data to files
        self.export_case_info()

        # # REPORT req stories
        req_stories = []
        if self.paras["diagnosis_story_output"] == 1:
            req_stories = self.report_req_story()

        return num_req, adm_rate, succ_order_rate, service_rate, req_stories

    def update_one_period(self, t, disp_policy, admit_policy, alloc_policy):
        # REPORT
        print("\n----Period %d----" % t)
        # receive returning items
        self.inventory.receive_returns()

        # # (8/16) deal with return delays on the fly
        # if alloc_policy == "NomiSch":
        #     exp_delay_window = self.paras["return_delay_geom_mean"]*(1-self.paras["return_no_delay_proportion"]) #TODO: experiment goes here
        #     exp_rt_flow = self.inventory.report_exp_return_flow()
        #     for it in exp_rt_flow:
        #         if it[1] <= 0: #it[0]: item_index, it[1] exp_return_periods
        #             affected_req_index = self.nominal_schedule.extend_release_time_for_delay(it[0], t, exp_delay_window)
        #             if affected_req_index:
        #                 resolve = self.nominal_schedule.reschedule_for_one_item_delay(affected_req_index)
        #                 if not resolve: # have to fail this affected order
        #                     for od in self.orders:
        #                         if od.req_index == affected_req_index:
        #                             od.fail_order(t)

        # sort out current inventory
        if disp_policy == "current":
            avai_inv = self.inventory.report_current_inv()

            # REPORT
            print("\nAdmission control using CURRENT inv, avai_inv: ", avai_inv)

            # process and admit requests
            if admit_policy == "IT0":
                self.req_scan_index = self.scan_admit_requests_IT0(t, self.req_scan_index, avai_inv)
            elif admit_policy == "ITInf":
                self.req_scan_index = self.scan_admit_requests_ITInf(t, self.req_scan_index)
        # predict inventory
        elif disp_policy == "future":

            # REPORT
            print("\nAdmission control using FUTURE inv")

            if admit_policy == "IT0":
                self.req_scan_index = self.scan_admit_requests_IT0_future(t, self.req_scan_index)
            elif admit_policy == "ITInf":
                self.req_scan_index = self.scan_admit_requests_ITInf(t, self.req_scan_index)

        elif disp_policy == "future_cstp":

            # REPORT
            print("\nAdmission control using FUTURE_CSTP inv")

            if admit_policy == "IT0":
                self.req_scan_index = self.scan_admit_requests_IT0_future(t, self.req_scan_index, use_uncmtd=1)
            elif admit_policy == "ITInf":
                self.req_scan_index = self.scan_admit_requests_ITInf(t, self.req_scan_index)

        # allocate/commit orders
        if alloc_policy == "FOFS":
            commited_items_id, desired_dates, realized_cycle_duration = FOFS_alloc(self.inventory, self.orders, self.length_of_delivery, t)
        elif alloc_policy == "EDD":
            commited_items_id, desired_dates, realized_cycle_duration = EDD_alloc(self.inventory, self.orders, self.length_of_delivery, t, lead_time=self.paras['EDD_lead_time'])

        # (8/17) display and commit orders by nominal schedule approach
        if admit_policy == "NomiSchCpl":
            self.req_scan_index = self.scan_admit_requests_NS_complete_reschedule(t, self.req_scan_index)
        if alloc_policy == "NomiSch":
            commited_items_id, desired_dates, realized_cycle_duration = NS_alloc(self.inventory, self.orders, self.nominal_schedule,
                                                                                self.length_of_delivery, self.median_cycle_duration, t)

        # remove committed items
        if len(commited_items_id) > 0:
            early_periods = [desired_dates[i] - t for i in range(len(commited_items_id))] #may be negative if short delays allowed
            commited_items_errps = [early_periods[i] + self.median_cycle_duration for i in range(len(commited_items_id))]
            commited_items_rps = [early_periods[i] + realized_cycle_duration[i] for i in range(len(commited_items_id))]
            self.inventory.sendout_items(item_index_list=commited_items_id, errp_list=commited_items_errps, rp_list=commited_items_rps)

        # info updates
        self.update_order_per_period(t)
        self.inventory.update_rp_errp_per_period()

        # #REPORT
        # print("Future item returning flow: ")
        # rt_flow = self.inventory.report_return_flow()
        # for rt in rt_flow:
        #     print("  index: %d, will return at time: %d" % (rt[0], rt[1]))

    def remove_req_overtime(self):
        for cr in self.requests[:]:
            if cr.order_time + cr.desired_periods > self.time_horizon:
                self.requests.remove(cr)

    def remove_req_desired_periods_0(self):
        for cr in self.requests[:]:
            if cr.desired_periods == 0:
                self.requests.remove(cr)

    def scan_admit_requests_IT0(self, t, start_index, avai_inv):
        print("Threshold 0 policy")

        req_cnt = 0
        for cr in self.requests[start_index:]:
            if cr.order_time == t:

                # record story info for diagnosis
                cr.write_story_when_admit_by_current(avai_inv)

                if avai_inv > 0:
                    cr.admit()
                    self.create_order(cr.index, cr.order_time, cr.desired_periods, cr.realized_cycle_duration)
                    avai_inv -= 1
                    print("  admit req: %d, " % cr.index)
                else:
                    cr.reject()
                    print("  reject req: %d, " % cr.index)
                req_cnt += 1
            else: break
        start_index_new = start_index + req_cnt #next period scans from here
        return start_index_new

    def scan_admit_requests_IT0_future(self, t, start_index, use_uncmtd = 0):
        print("Threshold 0 policy")

        inv_occup_record = {} # consider competing orders for the same future date
        for future_t in range(t-1, self.time_horizon+1): #all future times
            inv_occup_record[future_t] = 0

        req_cnt = 0
        for cr in self.requests[start_index:]:
            if cr.order_time == t:
                desired_time = cr.order_time + cr.desired_periods
                uncmtd_cnt = self.count_uncommited_order_due_by_future_time(desired_time)
                avai_inv, current_inv, future_exp_return, num_occupied_items = self.inventory.predict_future_inv_median_cycle(t, desired_time, inv_occup_record) # predict: current_inv + future_exp_return - occupied by other predictions
                if use_uncmtd == 1:
                    avai_inv -= uncmtd_cnt # predict: - uncommitted_cnt (by future time)

                # record story info for diagnosis
                cr.write_story_when_admit_by_predict(avai_inv, current_inv, future_exp_return, num_occupied_items, use_uncmtd, uncmtd_cnt)

                if avai_inv > 0:
                    cr.admit()
                    print("  admit req: %d, " %cr.index, "predicted inv at time: %d is %d"%(desired_time, avai_inv))
                    self.create_order(cr.index, cr.order_time, cr.desired_periods, cr.realized_cycle_duration)
                    inv_occup_record[desired_time] += 1
                else:
                    cr.reject()
                    print("  reject req: %d, " %cr.index, "predicted inv at time: %d is %d"%(desired_time, avai_inv))
                req_cnt += 1
            else: break
        start_index_new = start_index + req_cnt #next period scans from here
        return start_index_new

    def scan_admit_requests_ITInf(self, t, start_index):
        print("Threshold Inf policy")

        req_cnt = 0
        for cr in self.requests[start_index:]:
            if cr.order_time == t:
                cr.admit()
                print("  admit req: %d, " % cr.index)
                self.create_order(cr.index, cr.order_time, cr.desired_periods, cr.realized_cycle_duration)
                req_cnt += 1
            else: break
        start_index_new = start_index + req_cnt
        return start_index_new

    def scan_admit_requests_NS_complete_reschedule(self, t, start_index):
        print("Nominal schedule admission - complete reschedule")

        req_cnt = 0
        for cr in self.requests[start_index:]:
            if cr.order_time == t:
                admit = self.nominal_schedule.reschedule_for_one_new_request(cr, self.median_cycle_duration, t, self.time_horizon)
                if admit:
                    cr.admit()
                    print("  admit req: %d, " % cr.index)
                    self.create_order(cr.index, cr.order_time, cr.desired_periods, cr.realized_cycle_duration)
                else:
                    cr.reject()
                    print("  reject req: %d, " % cr.index)
                req_cnt += 1
            else: break
        start_index_new = start_index + req_cnt
        return start_index_new

    def create_order(self, req_id, order_time, delivery_periods, realized_cycle_duration):
        self.orders.append(CustomerOrder(req_id, order_time, delivery_periods, realized_cycle_duration))

    def count_uncommited_order_due_by_future_time(self, future_time):
        cnt = 0
        for od in self.orders:
            if od.status == 0 and od.desired_time < future_time:
                cnt += 1
        return cnt

    def update_order_per_period(self, t):
        print("\nUpdate order info")

        for od in self.orders:
            if od.status == 0 and od.desired_time <= t + self.length_of_delivery: #expired and failed
                od.fail_order(t)
            if od.status == 1:
                #committed, and could return on time
                od.finish_order(t)


    def report_config(self, disp_policy, admit_policy, alloc_policy, EDD_leadtime):
        print("\nRunning with disp policy: ", disp_policy, ", admit: ", admit_policy, ", alloc: ", alloc_policy)
        if alloc_policy == 'EDD':
            print(" with EDD lead time: ", EDD_leadtime)

    def report_admission_rate(self):
        print("\n1st service rate (admission):")
        num_req = len(self.requests)
        adm_req = [req.index for req in self.requests if req.status == 1]
        adm_rate = len(adm_req)/num_req*100
        print("  %d out of %d: %.2f %%" %(len(adm_req), num_req, adm_rate))
        return num_req, adm_rate

    def report_succ_order_rate(self):
        print("2nd service rate (on-time arrival):")
        num_orders = len(self.orders)
        succ_orders = [od.req_index for od in self.orders if od.status == 2]
        succ_order_rate = len(succ_orders) / num_orders * 100
        print("  %d out of %d: %.2f %%" % (len(succ_orders), num_orders, succ_order_rate))

        num_req = len(self.requests)
        service_rate = len(succ_orders) / num_req * 100
        print("Entire service rate (succ service/all req):")
        print("  %d out of %d: %.2f %%" % (len(succ_orders), num_req, service_rate))
        return succ_order_rate, service_rate

    def report_item_cir_stats(self):
        print("Item circulation:")
        avg_cnt, cnt_list = self.inventory.report_item_cir_stats()
        print("  average cnt: ", avg_cnt)
        print("  cnt for all items: ", cnt_list)

    def export_case_info(self):
        # item-wise info
        item_info = []
        for rt in self.initial_rt_flow:
            item_info.append({"item_id": rt[0], "release_time": rt[2]})
        for id in self.initial_instock_items:
            item_info.append({"item_id": id, "release_time": 0})

        # req-wise info
        req_info = []
        for cr in self.cr_full_list:
            req_info.append({"req_id": cr[0], "order_time": cr[1], "desired_time": cr[2], "rental_length": cr[3]})

        save_dir = self.paras["export_data_dir"]
        item_datafile = os.path.join(save_dir, "itemdata_rseed" + str(self.rand_seed) + '.csv')
        req_datafile = os.path.join(save_dir, "reqdata_rseed" + str(self.rand_seed) + '.csv')
        item_df = pd.DataFrame(item_info)
        item_df.to_csv(item_datafile)
        req_df = pd.DataFrame(req_info)
        req_df.to_csv(req_datafile)

    def report_req_story(self):
        # only for FOFS policy and EDD-cstp policy for comparison
        cr_stories = []
        for cr in self.requests:
            cr_story = {}
            cr_story["req_index"] = cr.index
            cr_story["order_time"] = cr.order_time
            cr_story["desired_time"] = cr.desired_time
            cr_story["admit_outcome"] = cr.status # admit (1) or reject (-1) outcome

            # current inv (for FOFS-current policy only)
            if self.paras['display_policy_wrt'] == "current":
                cr_story["toa_current_inv"] = cr.toa_current_inv

            # future inv pred (for EDD-cstp policy only)
            if self.paras['display_policy_wrt'] == "future_cstp":
                cr_story["predict_with_uncmtd"] = cr.predict_with_uncmtd
                cr_story["toa_current_inv"] = cr.toa_current_inv
                cr_story["toa_future_exp_return"] = cr.toa_future_exp_return
                cr_story["toa_uncmtd_cnt"] = cr.toa_uncmtd_cnt
                cr_story["toa_occupied_by_pred_same_period"] = cr.toa_occupied_by_pred_same_period
                cr_story["toa_inv_ref"] = cr.toa_inv_ref

            cr_stories.append(cr_story)

        od_stories = []
        for od in self.orders:
            od_story = {}
            od_story["req_index"] = od.req_index
            od_story["commit_outcome"] = od.status
            od_story["realized_cycle_duration"] = od.realized_cycle_duration
            if od.status == 2: #finished order
                od_story["commit_time"] = od.commit_time
                od_story["finish_time"] = od.finish_time
                od_story["commit_item"] = od.commit_item
            elif od.status == -2: #failed order
                od_story["fail_time"] = od.fail_time
            od_stories.append(od_story)

        # merge by req_index
        cr_df = pd.DataFrame(cr_stories)
        od_df = pd.DataFrame(od_stories)
        cr_df = cr_df.merge(od_df, how='left', on='req_index')
        return cr_df

# TEST BELOW
# The script below is for one single case
# from paras_debug import *
# import sys, os
#
# rand_seed = parameters_main['rand_seed']
# disp_pol, adm_pol, alloc_pol = parameters_config['display_policy_wrt'], parameters_config['admission_policy'], parameters_config['allocation_policy']
# exp_stage = parameters_config['exp_stage']
# stdout_file_name = '_'.join([exp_stage, disp_pol, adm_pol, alloc_pol, str(rand_seed)]) + '.txt'
# stdout_file_name = os.path.join("output", stdout_file_name)
#
# sys.stdout = open(stdout_file_name, 'w')
#
# simul = MainSimulator(parameters_config, parameters_main, parameters_dist)
# simul.initialize()
# simul.run_and_report(debug_truncate_time=None)
#
# sys.stdout.close()

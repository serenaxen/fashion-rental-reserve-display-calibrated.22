
# TODO: (notes 8/29) this version removes all the discarded configs (length_of_delivery changed to 0, inv buffer policy, end-of-horizon config)

parameters_config = {
    "display_policy_wrt": 'current', #current or future; i.e. A/B mode in 2022/4/14 doc
    "admission_policy": 'IT0', #IT0 (zero) or ITInf; i.e. X/Y mode in 2022/4/14 doc
    "allocation_policy": 'FOFS', #FOFS or EDD
    "EDD_lead_time": 2,

    "exp_stage": "DEFAULT_DEBUG",

    "export_data_dir": "upper_bounds/data/"
}

parameters_main = {
    "time_horizon": 182,
    "total_items": 5,

    "starting_inv": 5,
    "inf_inv": 100,

    "is_seed": 1,
    "rand_seed": 8,
}

parameters_dist = {
    "customer_request_poisson_rate": 1,

    "cycle_duration_lognormal_median": 38,
    "cycle_duration_lognormal_mu": 3.615,
    "cycle_duration_lognormal_sigma": 0.5073,

    # "regular_return_periods": 37,
    # "return_no_delay_proportion": 0.5,
    # "return_delay_geom_mean": 32,

    "customer_request_desired_time_ondmd_fixed": 3,

    "customer_request_desired_time_binomial_n": 56,
    "customer_request_desired_time_binomial_p": 0.25,

    "length_of_delivery": 0,
}


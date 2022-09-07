# Generate random variables for parameters or stochastic processes
# Xuening Wang
# 2022/04/14
import math

import numpy as np
import matplotlib.pyplot as plot

def uniform_discrete_one(lb, ub): #note, ub cant be attained!
    return np.random.randint(low=lb, high=ub)

def poisson_arr_discrete_seq(time_limits, lmbd):
    arr_seq = []
    sum = (-np.log(np.random.rand())/lmbd)
    while round(sum) < time_limits:
        arr_seq.append(round(sum))
        exp_var = (-np.log(np.random.rand())/lmbd)
        sum = sum + exp_var
    return arr_seq

def binomial_discrete_seq(length, n, p):
    return np.random.binomial(n, p, length)

# (9/6)
def lognormal_rounded_up_seq(length, mu, sigma):
    arr_seq = np.random.lognormal(mean=mu, sigma=sigma, size=length)
    return np.ceil(arr_seq)

def geom_discrete_seq(length, mean):
    p = 1/(mean+1)
    return np.random.geometric(p, length)-1

def mixed_geom_discrete_seq(length, mean, no_delay_proportion):
    seq = geom_discrete_seq(length, mean)
    unif_seq = np.random.rand(length)
    for i in range(length):
        if unif_seq[i] <= no_delay_proportion:
            seq[i] = 0
    return seq

# # TEST BELOW
# print(uniform_discrete_one(1, 4))
# print(poisson_arr_discrete_seq(15, 0.5))

# seq = binomial_discrete_seq(1000, 10, 0.4)
# plot.hist(seq, bins=10)
# print(seq)
# plot.show()

# geom_seq = geom_discrete_seq(1000, 2)
# print(geom_seq)
# plot.hist(geom_seq, bins=list(range(11)))
# plot.show()
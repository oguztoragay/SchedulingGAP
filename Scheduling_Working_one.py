import pyomo.environ
from pyomo.environ import *
import numpy as np
from numpy import random
from pyomo.opt import SolverFactory
from pyomo.core import Var
import string
import pandas as pd
import gurobipy as gp
from gurobipy import GRB

df = pd.DataFrame()


def loader(number_machines, number_jobs):
    jobs = list(range(number_jobs))
    machines = []
    if number_machines <= 24:
        letters = list(string.ascii_letters)[26:52]
    elif (24 < number_machines) and (number_machines <= 52):
        letters = list(string.ascii_letters)
    else:
        print('Too many machines!!!')
        quit()
    
    for mach in range(number_machines):
        random.shuffle(letters)
        poper = letters.pop(0)
        machines.append(poper)
    
    orders = [x+1 for x in list(range(len(machines)))]
    order_job_set = []
    work_order = {}
    machine_job_set = []
    process_time = {}

    for job in jobs:
        temp_machines = list(machines)
        for order in orders:
            random.shuffle(temp_machines)
            node = tuple([order, job])
            order_job_set.append(node)
            work_order[node] = temp_machines.pop(0)
            node_p = tuple([machines[(order - 1)], job])
            machine_job_set.append(node_p)
            process_time[node_p] = random.randint(1,10)

    mym = ConcreteModel()

    mym.m = Param(initialize=number_machines)
    mym.n = Param(initialize=number_jobs)
    mym.jobs = Set(initialize=jobs)
    mym.machines = Set(initialize=machines)
    mym.orders = Set(initialize=orders)
    mym.order_job = Set(initialize=order_job_set)
    mym.machine_job = Set(initialize=machine_job_set)

    mym.order_m = Param(mym.order_job, initialize=work_order, within=Any)
    mym.p = Param(mym.machine_job, initialize=process_time)
    mym.BigM = Param(initialize=1000)

    mym.t = Var(mym.machines, mym.jobs, within=NonNegativeIntegers)
    mym.s = Var(mym.machines, mym.jobs, within=NonNegativeIntegers)
    mym.y = Var(mym.machines, mym.jobs, mym.jobs, within=Binary)

    def object_(mym):
        obj = 0.0
        for j in mym.jobs:
            obj += mym.t[(mym.order_m[mym.m, j]), j]
        return obj

    mym.obj = Objective(rule=object_)

    def StartAfterFinish(mym, j, k):
        if k >= 2:
            return mym.s[mym.order_m[k, j], j] >= mym.t[mym.order_m[k-1, j], j]
        else:
            return Constraint.Skip
    mym.StartAfterFinish = Constraint(mym.jobs, mym.orders, rule=StartAfterFinish)

    def StartFinish(mym, machine_, job_):
        return mym.s[machine_, job_] == mym.t[machine_, job_] - mym.p[machine_, job_]
    mym.StartFinish = Constraint(mym.machines, mym.jobs, rule=StartFinish)

    def BigM1(mym, machine_, job_j, job_k):
        return mym.s[machine_, job_k] >= mym.t[machine_, job_j] - mym.y[machine_, job_j, job_k]*mym.BigM
    mym.BigM1 = Constraint(mym.machines, mym.jobs, mym.jobs, rule=BigM1)

    def BigM2(mym, machine_, job_j, job_k):
        if job_k >= job_j + 1:
            return mym.s[machine_, job_j] >= mym.t[machine_, job_k] - (1 - mym.y[machine_, job_j, job_k])*mym.BigM
        else:
            return Constraint.Skip
    mym.BigM2 = Constraint(mym.machines, mym.jobs, mym.jobs, rule=BigM2)
    return mym

opt = SolverFactory('gurobi')

def solver(mym,gap=0):
    opt.options['mipgap'] = gap
    results = opt.solve(mym, tee=True)
    time = np.round(results.solver[0]['Time'], 3)

    return time


number_machines = 6
number_jobs = 8
gaps = [0.2, 0.1, 0.05, 0]
itterations = 1
mym = loader(number_machines, number_jobs)

def my_callback(mym, cb_where):
    if cb_where == GRB.Callback.MIP:
        runtime = mym.cbGet(GRB.Callback.RUNTIME)
        # print(':::::::::::::::::::::::::',runtime)
        objbst = mym.cbGet(GRB.Callback.MIP_OBJBST)
        objbnd = mym.cbGet(GRB.Callback.MIP_OBJBND)
        gap = abs((objbst - objbnd) / objbst)
        if gap == 0.5:
            # m.terminate()
            print('GAP ::::::::::::::::::::::', gap * 100)



opt.set_callback(my_callback)
opt.solve(mym, tee=True)







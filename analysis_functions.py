"""
analysis_functions.py

Functions to modify forest.lp for the MetaModels example.
"""
import csv

import gurobipy as gp
import pygurobi as pg

from meta_model import MetaModel


def solve(mm):
    """
    Optimize a model object.

    Take a snapshot of the model.

    Optional - log solution to file.
    """
    model = mm.model
    model.optimize()


    mm.optimal = model.status
    mm.take_snapshot()
    print "\nSnapshot saved as {}".format(mm.filename)
    mm.solve_count += 1
    mm.update_filename()

    if model.status == gp.GRB.OPTIMAL:
        # Write a csv of the solution data
        write_solution(mm)


    return True


def remove_last_period(mm):
    """
    Shorten the planning horizon of the model by one period.
    """
    
    m = mm.model
    variables = ["harv", "age"]
    constraints = ["harv", "age", "env"]

    harv_vars = pg.get_variables(m, "harv")
    max_period = max([float(i.varName.split(",")[-1][:-1]) for i in harv_vars])

    for v in variables:
        all_vars =  pg.get_variables(m, v, filter_values={-1: max_period})
        for v in all_vars:
            m.remove(v)
    for c in constraints:
        all_cons = pg.get_constraints(m, c, filter_values={-1: max_period})
        for a in all_cons:
            m.remove(a)
    m.update()


def zero_objective_coeffs(mm):
    pg.zero_all_objective_coeffs(mm.model)
    mm.model.update()


def set_variables_attr(mm, attr, val, name):
    pg.set_variables_attr(attr, val, model=mm.model, name=name)
    mm.model.update()


def write_solution(mm):
    """
    Write solution values for harv and age variables
    to a csv file.
    """

    m = mm.model

    solution_file = "{0}_sol.csv".format(mm.filename)

    harv_data = []
    harv_data.append(["Harvest data"])
    harv_data.append(["Species", "Region", "Period", "Value"])
    # write harv variable solution values
    harv = pg.get_variables(m, "harv")
    for h in harv:
        name = h.varName.split(",")
        species = name[0].split("[")[1]
        region = name[1]
        period = name[-1][:-1]
        harv_data.append(
                [species, region, period, h.X])

    age_data = []
    age_data.append(["Age data"])
    age_data.append(["Region", "Period", "Value"])
    age = pg.get_variables(m, "age")
    for a in age:
        name = a.varName.split(",")
        region = name[0].split("[")[1]
        period = name[-1][:-1]
        age_data.append(
                [region, period, a.X])

    with open(solution_file, "w+") as wrf:
        wf = csv.writer(wrf)
        wf.writerows(harv_data)
        wf.writerows(age_data)




def test_tutorial():

    mm = MetaModel("forest.lp")
    mm.add_module("analysis_functions")
    mm.meta_function("analysis_functions.solve")

    mm.meta_function("analysis_functions.remove_last_period")
    mm.meta_function("analysis_functions.solve")

    mm.meta_function("analysis_functions.zero_objective_coeffs")
    mm.meta_function("analysis_functions.set_variables_attr",
            args=("obj", 1, "age"))
    mm.meta_function("analysis_functions.solve")

    location = mm.snapshot

    mm = MetaModel(snapshot=location)
    mm.meta_function("analysis_functions.solve")

    return mm





        




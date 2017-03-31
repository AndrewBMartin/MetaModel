"""
analysis_functions.py

Functions to modify forest.lp for the MetaModels example.
"""

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

    if model.status == gp.GRB.OPTIMAL:
        # Could have a function here to log solution data
        pass

    mm.optimal = model.status
    mm.take_snapshot()
    print "\nSnapshot saved as {}".format(mm.filename)
    mm.solve_count += 1
    mm.update_filename()

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

    mm = MetaModel(snapshot="forest_2017331_2.json")
    return mm





        




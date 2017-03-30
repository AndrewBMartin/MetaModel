"""
16 March 2017

Splitting the meta model into something more generic.
"""

import os
import importlib
import json
from datetime import datetime

import pygurobi as pg


class MetaModel(object):
    """
    A functional wrapper for Gurobi models.

    A MetaModel's primary method is the meta_function, used to dynamically track 
    and store Gurobi model states.

    Keep track of modifications made to a model and provide functionality to
    take snapshots of the model state.

    If you want to call functions on a MetaModel that belong to a separate
    module, the module must be added explicitly with the
    "add_module" or "add_modules" functions.
    """

    def __init__(self, model_name="", model="", json_file="", module_names=[]):
        """
        Constructor that can take either a model_name (including file extension)
        or a json_file location to a create MetaModel object.

        If model_name provided then can also pass a model object to save the
        MetaModel from having to read in the model. 

        If you will be using functions from an external library than these
        modules can be passed to the constructor as a list of strings using the
        module_names argument.

        If a json_file is specified then a MetaModel is recreated from an earlier
        snapshot.
        """

        if json_file:
            self.load_from_json()
            return

        if not model_name:
            raise AttributeError('A model file name must be supplied')
        self.model_name = model_name
        self.model = model
        if not model:
            self.model = pg.read_model(model_name)
        self.date_created = datetime.now()
        self.model_description = ""
        self.solve_count = 0
        self.optimal = False

        # Store an ordered list of tuples of the functions and their arguments
        # that have been applied to the model
        self.function_list = []

        self.json_file = ""
        filename, file_extension = os.path.splitext(self.model_name)
        self.filename = "{0}_{1}_{2}".format(
                filename,
                "{0}{1}{2}".format(self.date_created.year, self.date_created.month,
                    self.date_created.day), 
                self.solve_count)
        self.module_names = module_names
        self.modules = []
        if self.module_names:
            self.add_modules(self.module_names)


    def meta_function(self, func_name, args="", kwargs={}, no_record=False):
        """
        Call the supplied function given by func_name on the meta_model object.

        Provide args as a tuple the function should take the arguments in 
        the order they're provided (named arguments might be better).

        Pass no_record = True if you don't want the operation recorded in 
        the meta models' function list. 

        Note that functions supplied to meta_function must follow a strict
        format. Namely, their first argument must be a Gurobi model object.
        The arguments given by args must be in the order that they should
        be passed to the function being called.

        Arguments to functions must be json serializable.
        """

        func = ""

        if not func_name:
            raise ValueError("A function name must be provided")


        # module_name.func_name is the preferred method as this prevents
        # namespace collisions. It's expected that users will know
        # their libraries well however, so they may prefer to simply pass
        # function names.
        if "." in func_name and func_name.split(".")[0] != "self":
            module, func_name = func_name.split(".")

            for mod in self.modules:
                if mod.__name__ == module:
                    try:
                        func = getattr(mod, func_name)
                    except KeyError:
                        continue
            if not func:
                raise KeyError(
                        "Function {0} was not found in module {1}".format(
                            func_name, module))


            
        elif "." in func_name and func_name.split(".")[0] == "self":
            module, func_name = func_name.split(".")
            try:
                func = getattr(self, func_name)
            except KeyError:
                raise KeyError(
                        "Function {0} was not found on the object {1}".format(
                            func_name, self))
        else:

            # No module identifier provided. 
            # Check to see if the function belongs to one of the added modules.
            # This form is discouraged unless you know the modules that
            # you're working with well enough to avoid accidentally calling
            # a function with the same name from the wrong module.
            for module in self.modules:
                try:
                    func = getattr(module, func_name)
                except KeyError:
                    continue

            if not func:
                try:
                    func = getattr(self, func_name)
                except KeyError:
                    raise KeyError('Function "{0}" was not found'.format(func_name))

        try:
            return_value = func(self, *args, **kwargs)
            return return_value
        except ValueError:
            # This is probably because the number of arguments given to func is wrong
            raise
        
        # When recreating a MetaModel from json we want to be able to
        # call meta_function without having those calls recorded on the object.
        if not no_record:
            self.function_list.append((func_name, args, kwargs))
    

    def add_module(self, module_name):
        """
        Add a module to the meta model to access it's functions
        from meta functions.

        A module is passed as a string representing the name of the module.
        """

        module = ""
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # Module doesn't exist
            raise
        except ValueError:
            # module_name likely empty string
            raise

        if module:
            self.modules.append(module)
            self.module_names.append(module_name)


    def add_modules(self, modules):
        """
        Add multiple modules by passing a list of strings representing modules.
        """

        for module_name in modules:
            self.add_module(module_name)

            
    def load_json(self, json_file): 
        """
        Read in a json file representing a MetaModel.
        """
        
        data = ""
        try:
            data = json.load(open(json_file))
        except IOError:
            raise IOError('File "{}" not found'.format(json_file))

        return data


    def load_from_json(self):
        """
        Load MetaModel from json file. Then add any modules that MetaModel
        requires and apply functions given by the MetaModel's function_list.
        """

        data = self.load_json(json_file)
        for key in data:
            setattr(self, key.lower(), data[key])
        self.model = pg.read_model(self.model_name)
        
        self.add_modules(self.module_names)
     
        for function, args, kwargs in self.function_list:
            self.meta_function(function, args, kwargs, no_record=True)



    def update_filename(self):
        """
        Update the MetaModel filename based on the current date and the number
        of times that the model has attempted to be solved.
        """
        
        filename, file_extension = os.path.splitext(self.model_name)
        cur_date = datetime.now()
        self.filename = "{0}_{1}_{2}".format(
                filename,
                "{0}{1}{2}".format(cur_date.year, cur_date.month,cur_date.day), 
                self.solve_count)


    def write_json(self):
        """
        Serialize a MetaModel as a json object located at self.filename.

        Only elements of the MetaModel that can be serialized will be
        serialized. Namely the Gurobi model object and the modules list
        will not be serialized.
        """

        data = {}
        for key in self.__dict__:

            # The following keys are not json serializable
            if key == "model":
                continue
            if key == "date_created":
                data[key] = str(getattr(self, key))
                continue
            if key == "modules":
                continue

            data[key] = getattr(self, key)

        self.json_file = "{0}.json".format(self.filename)
        data["json_file"] = self.json_file

        json.dump(data, open(self.json_file, "w+"))


    def solve(self):
        """
        Example of how to take a model snapshot when solving a Gurobi model.
        """
        m = self.model
        pg.reoptimize(m)
        if m.status == gp.GRB.status.OPTIMAL:
            self.solve_count += 1
            self.optimal = True

            # May want to have a script here to save useful information.

            self.write_json()
            self.update_filename()
        else:
            self.optimal = False
            self.solve_count += 1
            self.write_json()




    def set_attr(self, attr, value):
        """
        Providing MetaModel access to the Gurobi setAttr method.
        """

        try:
            setattr(self.model, attr, value)
        except AttributeError:
            raise AttributeError('Attribute "{0}" does not exist'.format(attr))

        self.function_list.append("self.set_attr", (attr, value))


    def get_attr(self, attr):
        """
        Providing MetaModel access ot the Gurobi getAttr method.
        
        This function does not modify the model object so is not recorded
        by meta_function
        """

        try:
            val = getattr(self.model, attr)
            return val
        except AttributeError:
            raise AttributeError('Attribute "{0}" does not exist'.format(attr))


    def set_param(self, param, value):
        """
        Providing MetaModel access to the Gurobi setParam method.
        """
        try:
            self.model.setParam(param, value)
        except AttributeError:
            raise AttributeError('Parameter "{0}" does not exist'.format(attr))

        self.function_list.append("self.set_param", (param, value))


    def get_param(self, param):
        """
        Providing MetaModel access ot the Gurobi getParam method.
        
        This function does not modify the model object so is not recorded
        by meta_function
        """
        
        try:
            self.model.getParam(param, value)
        except AttributeError:
            raise AttributeError('Parameter "{0}" does not exist'.format(attr))

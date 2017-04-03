"""
16 March 2017

MetaModel design pattern.
A wrapper on a Gurobi model that allows you to automate
taking snapshots of the state of the model and logging results.
"""

import os
import importlib
import json
from datetime import datetime

import gurobipy as gp

class MetaModel(object):
    """
    A functional wrapper for Gurobi models.

    A MetaModel's primary method is the meta_function, used to dynamically track 
    and store Gurobi model states.

    Keep track of modifications made to a model and provide functionality to
    take snapshots of the model state.
    """

    def __init__(self, model_name="", model="", snapshot="", module_names=[]):
        """
        Constructor that can take either a model_name (including file extension)
        or a snapshot json location to a create MetaModel object.

        If model_name provided then can also pass a model object to save the
        MetaModel from having to read in the model. 

        If you will be using functions from an external library than these
        modules can be passed to the constructor as a list of strings using the
        module_names argument.

        If a snapshot is specified then a MetaModel is recreated from 
        the supplied json file.
        """

        if snapshot:
            self.load_from_snapshot(snapshot)
            return

        if not model_name:
            raise AttributeError('A model file name or a snap shot must be supplied')
        self.model_name = model_name
        self.model = model
        if not model:
            self.model = gp.read(model_name)
        self.date_created = datetime.now()
        self.model_description = ""
        self.solve_count = 0
        self.optimal = False

        # Store an list of tuples of the functions, their args, and their kwargs
        # that have been applied to the model
        self.function_list = []

        self.snapshot = ""
        self.update_filename()
        self.module_names = module_names
        self.modules = {}
        if self.module_names:
            self.add_modules(self.module_names)


    def meta_function(self, func_name, args="", kwargs={}, no_record=False):
        """
        Call the supplied function given by func_name on the meta_model object.

        Provide args as a tuple the function should take the arguments in 
        the order they're provided (named arguments might be better). Can
        also specify a dictionary of kwargs.

        Pass no_record = True if you don't want the operation recorded in 
        the meta models' function list. 

        Note that functions supplied to meta_function must follow a strict
        format. Namely, their first argument must be a MetaModel. Arguments
        and kwargs follow.

        Arguments to functions must be json serializable.

        3 April 2017 - meta_functions are not perpared for calling methods
        contained in modules of modules. That is, if you have a module, 
        called top_level, containing a module, called mid_level, then you
        can't call top_level.mid_level.function.
        """

        func = ""

        if not func_name:
            raise ValueError("A function name must be provided")


        # module_name.func_name is the preferred method as this prevents
        # namespace collisions. It's expected that users will know
        # their libraries well however, so they may prefer to simply pass
        # function names.
        if "." in func_name:
            module, func_name = func_name.split(".")

            if module not in self.module_names:
                raise ValueError("Module {0} has not been added".format(
                    module))

            for name, mod in self.modules.iteritems():
                if name == module:
                    try:
                        func = getattr(mod, func_name)
                    except KeyError:
                        continue
            if not func:
                raise KeyError(
                        "Function {0} was not found in module {1}".format(
                            func_name, module))
        else:

            # No module identifier provided. 
            # Check to see if the function belongs to one of the added modules.
            # This form is discouraged unless you know the modules that
            # you're working with well enough to avoid accidentally calling
            # a function with the same name from the wrong module.
            for module in self.modules.values():
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
            func(self, *args, **kwargs)
        except ValueError:
            # This is probably because the number of arguments given to func is wrong
            raise
        
        # When recreating a MetaModel from json we want to be able to
        # call meta_function without having those calls recorded on the object.
        if not no_record and "solve" not in func_name:
            self.function_list.append((func_name, args, kwargs))


    def get_module(self, module_name):
        module = ""
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # Module doesn't exist
            raise
        except ValueError:
            # module_name likely empty string
            raise

        return module

    

    def add_module(self, module_name):
        """
        Add a module to the meta model to access it's functions
        from meta functions.

        A module is passed as a string representing the name of the module.
        """

        module = self.get_module(module_name)

        if module:
            self.modules[module_name] = module
            self.module_names.append(module_name)


    def add_modules(self, modules):
        """
        Add multiple modules by passing a list of strings representing modules.
        """

        # 31 March 2017 - this is very strange.
        # If I iterate over modules then this loop will go
        # on forever even though above len(modules) returns 
        # the accurate length of the modules list which should
        # be very tractable. This work around achieves the desired
        # behaviour for now.
        for i in range(len(modules)):
            self.add_module(modules[i])


    def reload_module(self, module_name):
        """
        Reload a module that has already been added to the MetaModel.
        If the module has not been added, then add it.
        """
        
        if module_name not in self.module_names:
            self.add_module(module_name)
        else:
            reload(self.modules[module_name])

    
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


    def load_from_snapshot(self, snapshot):
        """
        Load MetaModel from a json of a snapshot.
        """

        data = self.load_json(snapshot)
        for key in data:
            setattr(self, key.lower(), data[key])

        # This is a Gurobi specific step.
        # If reading a model from another service, please replace this line.
        self.model = gp.read(self.model_name)
        
        self.add_modules(self.module_names)

        # Increment the solve count and update the filename
        # so we don't overwrite the current snapshot.
        self.solve_count += 1
        self.update_filename()
     
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


    def take_snapshot(self):
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
                data[key] = ""
                continue
            if key == "date_created":
                data[key] = str(getattr(self, key))
                continue
            if key == "modules":
                data[key] = {}
                continue

            data[key] = getattr(self, key)

        self.snapshot = "{0}.json".format(self.filename)
        data["json_file"] = self.snapshot

        json.dump(data, open(self.snapshot, "w+"))


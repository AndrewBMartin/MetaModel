# MetaModel



MetaModel is a powerful design pattern that allows Operational Researchers to analyze models without worrying about manually logging progress and results.

  - Easily take snapshots of the state of your model at any time
  - Recreate any state of your model without having to store multiple versions of the  model
  - Works with any optimization solver that exposes an API

## What is a MetaModel?

MetaModels came out of years working interactively with very large optimization models. These models were so large that it was prohibitively expensive to store multiple versions of the model anywhere. At the same time, these models took a very long time to generate. That is, it was much more efficient to generate a base model and then make changes to it interactively than it was to generate different models for each experiment. 

A MetaModel is a thin object wrapper around an optimization model. It has a constructor that takes an optimization model as it's main argument, and a few simple methods. It works as follows. First you add modules to the MetaModel using *add modules*, you then can call functions contained in those modules by calling *meta function* on your MetaModel and passing the function name. A *meta function* allows you to perform operations on your model before or after applying a function to it. Namely, the function can be logged on the MetaModel, or a snapshot can be taken of the current model state and the functions that have been applied to it. These snapshots can then be used to recreate the current model state quickly and inexpensively.

### Example
The example I'm going to show you is in Python using a Gurobi model. Find it in the meta_model directory as [forest.lp](https://github.com/AndrewBMartin/pygurobi/blob/master/pygurobi/forest.lp). 

[forest.lp](https://github.com/AndrewBMartin/pygurobi/blob/master/pygurobi/forest.lp) is a harvest scheduling model that seeks the optimal assignment of harvest schedules to cut-blocks. Our forest management model will run for 10 periods with each period representing 10 years. 

The objective is to **maximize the total volume of timber harvested**.

The variables are: 

* **x[i,j]** - the number of hectares of cut-block, *i*, to be managed under schedule *j*, where *j* is a sequence of harvests. Each cut-block, *i*, has both hardwood and softwood timber species, belongs to either the north or south region, and has an initial age.

* **harv[s,r,t]** - the volume of timber harvested from cut-blocks of species *s* (softwood or hardwood), in region, *r* (north or south), in period *t*. 

* **age[r,t]** - the area of the forest that is at least 60 years old in region, *r*, and period, *t*.

The constraints are:

* **gub(i)** - assignment problem constraints that say that no more than the area of each cut-block can be assigned to harvest schedules.
* **harv(s,r,t)** - inventory constraints that say that the **harv[s,r,t]** variables equal the volume harvested from cut-blocks of species, *s*, belonging to region, *r*, in period, *t*.
* **age(r,t)** - inventory constraints that say that the **age[r,t]** variables equal the sum of cut-blocks that are at least age 60 in period, *t*, and belong to region, *r*.
* **env(r, t)** - environmental constraints that say that at least 20% of the forest in each region, *r* has to be age 60 or greater after period 5.

```python
# We'll create a MetaModel by passing the constructor 
# the filename of an optimization model. 
# The constructor opens the model using the Gurobi API and attaches
# it as an attribute of the MetaModel.
>>> from meta_model import MetaModel
>>> mm = MetaModel("forest.lp")
```

Now there are some simple modifications that we want to perform on *forest.lp* so I've created a small Python module containing functions to perform those modifications. This modules is *analysis_functions.py*.

```python
>>> # We'll add the analysis_functions module to the MetaModel
>>> mm.add_module("analysis_functions")
>>>
>>> # adding a description to a MetaModel makes it easy 
>>> # to organize snapshots down the line.
>>> mm.description = "Baseline model"
>>>
>>> # We call a function from the analysis_functions module by passing
>>> # the module name and function name to the meta_function.
>>> # First we solve the model to establish a baseline.
>>> mm.meta_function("analysis_functions.solve")
Optimize a model with 160 rows, 1945 columns and 10172 nonzeros
Coefficient statistics:
  Matrix range    [1e+00, 2e+02]
  Objective range [1e+00, 1e+00]
  Bounds range    [0e+00, 0e+00]
  RHS range       [1e+00, 1e+01]
Presolve removed 50 rows and 1102 columns
Presolve time: 0.06s
Presolved: 110 rows, 843 columns, 2770 nonzeros

Iteration    Objective       Primal Inf.    Dual Inf.      Time
       0    4.1153473e+04   1.100000e+01   0.000000e+00      0s
      20    4.0724706e+04   0.000000e+00   0.000000e+00      0s

Solved in 20 iterations and 0.08 seconds
Optimal objective  4.072470571e+04

Snapshot saved as forest_30032017_0.json
```

When we called ```meta_function("analysis_functions.solve")``` a few things happened. First the MetaModel looked to see that *analysis_functions* is one of its modules, and that *solve* is a function of *analysis_functions*. Then it passes the MetaModel to *analysis_functions.solve*, and *solve* operates on the MetaModel.

You'll notice that at the end of the optimization ```Snapshot saved as forest_30032017_0.json``` was printed to screen. This just means that *analysis_functions.solve* calls the MetaModel's *snapshot* method, which serializes the current state of the model for easy recreating in the future. The serialized model state is stored at *forest_30032017_0.json*. This name isn't as intimidating as it looks. It's just the name of the model, concatenated with today's date, and the version of the model that's being serialized, in this case 0.

Now we'll make changes to the model and solve it again.

```python
>>> # Shorten the length of the 
>>> # planning horizon by one period.
>>> mm.description = "Reduce length of planning horizon to 9"
>>> mm.meta_function("analysis_functions.remove_last_period")
>>> mm.meta_function("analysis_functions.solve")
Optimize a model with 152 rows, 1939 columns and 8706 nonzeros
Coefficient statistics:
  Matrix range     [1e+00, 2e+02]
  Objective range  [1e+00, 1e+00]
  Bounds range     [0e+00, 0e+00]
  RHS range        [1e+00, 1e+01]
Presolve removed 44 rows and 1370 columns
Presolve time: 0.00s
Presolved: 108 rows, 569 columns, 1682 nonzeros

Iteration    Objective       Primal Inf.    Dual Inf.      Time
       0    3.8129707e+04   5.000000e+00   0.000000e+00      0s
       7    3.8025779e+04   0.000000e+00   0.000000e+00      0s

Solved in 7 iterations and 0.00 seconds
Optimal objective  3.802577891e+04

Snapshot saved as forest_30032017_1.json
```

Here when we passed *analysis_functions.remove_last_period* to the MetaModel, the function was applied to the MetaModel, reducing the length of the planning horizon from 10 periods to 9 periods, and then a record of the function being applied was stored to the MetaModel. This means that when we called *solve* and a snapshot was taken, a record of *analysis_functions.remove_last_period* was stored in *forest_30032017_1.json*.

Now we'll show how to call a function that takes arguments.

```python
>>> # Change the objective function of the model so that
>>> # it maximizes ecosystem condition instead
>>> # of harvest volume.
>>> mm.description = "Maximize Ecosystem condition"
>>>
>>> # Set harvet variable objective coefficients to zero
>>> mm.meta_function("analysis_functions.zero_objective_coeffs")
>>> # Set age variable objective coeffs to 1
>>> mm.meta_function("analysis_functions.set_variables_attr, 
                           args=("obj", 1, "age"))
>>> mm.meta_function("analysis_functions.solve")





Snapshot saved as forest_30032017_2.json
```

This example shows how to call a function that requires arguments. Note that keyword arguments could be passed in a similar fashion.

Let's say that we come back tomorrow and want to pick up where we left off.

```python
>>> from meta_model import MetaModel
>>> mm = MetaModel(json_file="forest30032017_2.json")
>>> print mm.description
Maximize Ecosystem condition
>>> mm.meta_function("analysis_functions.solve")


Snapshot saved as forest_31032017_0.json
```

And you see that we're exactly where we left off. WHen we passed the snapshot location to the MetaModel constructor, the original Gurobi model was loaded into the MetaModel, and the functions that we had applied to the model were applied again in the proper order, so that we've recovered exactly the model state from yesterday.



```sh
$ npm install --production
$ npm run predeploy
$ NODE_ENV=production node app
```

### Plugins

Dillinger is currently extended with the following plugins. Instructions on how to use them in your own application are linked below.

| Plugin | README |
| ------ | ------ |
| Dropbox | [plugins/dropbox/README.md] [PlDb] |
| Github | [plugins/github/README.md] [PlGh] |
| Google Drive | [plugins/googledrive/README.md] [PlGd] |
| OneDrive | [plugins/onedrive/README.md] [PlOd] |
| Medium | [plugins/medium/README.md] [PlMe] |
| Google Analytics | [plugins/googleanalytics/README.md] [PlGa] |


### Development

Want to contribute? Great!

Dillinger uses Gulp + Webpack for fast developing.
Make a change in your file and instantanously see your updates!

Open your favorite Terminal and run these commands.

First Tab:
```sh
$ node app
```

Second Tab:
```sh
$ gulp watch
```

(optional) Third:
```sh
$ karma test
```
#### Building for source
For production release:
```sh
$ gulp build --prod
```
Generating pre-built zip archives for distribution:
```sh
$ gulp build dist --prod
```
### Docker
Dillinger is very easy to install and deploy in a Docker container.

By default, the Docker will expose port 80, so change this within the Dockerfile if necessary. When ready, simply use the Dockerfile to build the image.

```sh
cd dillinger
docker build -t joemccann/dillinger:${package.json.version}
```
This will create the dillinger image and pull in the necessary dependencies. Be sure to swap out `${package.json.version}` with the actual version of Dillinger.

Once done, run the Docker image and map the port to whatever you wish on your host. In this example, we simply map port 8000 of the host to port 80 of the Docker (or whatever port was exposed in the Dockerfile):

```sh
docker run -d -p 8000:8080 --restart="always" <youruser>/dillinger:${package.json.version}
```

Verify the deployment by navigating to your server address in your preferred browser.

```sh
127.0.0.1:8000
```

#### Kubernetes + Google Cloud

See [KUBERNETES.md](https://github.com/joemccann/dillinger/blob/master/KUBERNETES.md)


### Todos

 - Write MOAR Tests
 - Add Night Mode

License
----

MIT


**Free Software, Hell Yeah!**

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)


   [dill]: <https://github.com/joemccann/dillinger>
   [git-repo-url]: <https://github.com/joemccann/dillinger.git>
   [john gruber]: <http://daringfireball.net>
   [df1]: <http://daringfireball.net/projects/markdown/>
   [markdown-it]: <https://github.com/markdown-it/markdown-it>
   [Ace Editor]: <http://ace.ajax.org>
   [node.js]: <http://nodejs.org>
   [Twitter Bootstrap]: <http://twitter.github.com/bootstrap/>
   [jQuery]: <http://jquery.com>
   [@tjholowaychuk]: <http://twitter.com/tjholowaychuk>
   [express]: <http://expressjs.com>
   [AngularJS]: <http://angularjs.org>
   [Gulp]: <http://gulpjs.com>

   [PlDb]: <https://github.com/joemccann/dillinger/tree/master/plugins/dropbox/README.md>
   [PlGh]: <https://github.com/joemccann/dillinger/tree/master/plugins/github/README.md>
   [PlGd]: <https://github.com/joemccann/dillinger/tree/master/plugins/googledrive/README.md>
   [PlOd]: <https://github.com/joemccann/dillinger/tree/master/plugins/onedrive/README.md>
   [PlMe]: <https://github.com/joemccann/dillinger/tree/master/plugins/medium/README.md>
   [PlGa]: <https://github.com/RahulHP/dillinger/blob/master/plugins/googleanalytics/README.md>
#!/usr/bin/env python
# coding: utf-8

# # Aiida

# ## Define workflow with aiida

# In[1]:


from python_workflow_definition.aiida import write_workflow_json

from aiida_workgraph import WorkGraph, task
from aiida import orm, load_profile
load_profile()

workflow_json_filename =  "aiida_simple.json"


# In[2]:


from workflow import (
    get_sum as _get_sum,
    get_prod_and_div as _get_prod_and_div,
    get_square as _get_square,
)


# In[3]:


wg = WorkGraph("arithmetic")


# In[4]:


get_prod_and_div_task = wg.add_task(
    task(outputs=['prod', 'div'])(_get_prod_and_div),
    x=orm.Float(1),
    y=orm.Float(2),
)


# In[5]:


get_sum_task = wg.add_task(
    _get_sum,
    x=get_prod_and_div_task.outputs.prod,
    y=get_prod_and_div_task.outputs.div,
)


# In[6]:


get_square_task = wg.add_task(
    _get_square,
    x=get_sum_task.outputs.result,
)


# In[7]:


write_workflow_json(wg=wg, file_name=workflow_json_filename)


# In[8]:


get_ipython().system('cat {workflow_json_filename}')


# ## Load Workflow with jobflow

# In[9]:


from python_workflow_definition.jobflow import load_workflow_json


# In[10]:


from jobflow.managers.local import run_locally


# In[11]:


flow = load_workflow_json(file_name=workflow_json_filename)


# In[12]:


result = run_locally(flow)
result


# ## Load Workflow with pyiron_base

# In[13]:


from python_workflow_definition.pyiron_base import load_workflow_json


# In[14]:


delayed_object_lst = load_workflow_json(file_name=workflow_json_filename)
delayed_object_lst[-1].draw()


# In[15]:


delayed_object_lst[-1].pull()


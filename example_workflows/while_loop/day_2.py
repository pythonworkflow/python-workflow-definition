# coding: utf-8

# # Python

# ## Basic while loop

# In[1]:


x=0
limit = 5

while x < limit:
    x +=1

print(x)


# ## Recursive 

# In[2]:


def while_loop(x, limit):
    if not (x < limit):
        return x
    x += 1
    return while_loop(x=x, limit=limit)

while_loop(limit=5, x=0)


# ## Functional 

# In[3]:


def condition(x, limit):
    return limit > x


# In[4]:


def function_body(x):
    return x + 1


# In[5]:


def abstract_while(x, limit):
    if not condition(x=x, limit=limit):
        return x
    x = function_body(x=x)
    return abstract_while(x=x, limit=limit)


# In[6]:


abstract_while(x=0, limit=5)


# # Workflow Manager

# ## Aiida workgraph

# In[7]:


from aiida_workgraph import task
from aiida import load_profile
load_profile()


# In[8]:


def condition(x, limit):
    return limit > x


# In[9]:

@task
def function_body(x):
    return x + 1


# In[10]:


@task.graph()
def abstract_while_aiida(x, limit):
    if not condition(x=x, limit=limit):
        # if not limit > x:
        return x
    x = function_body(x=x).result
    return abstract_while_aiida(x=x, limit=limit)


# In[11]:


wg = abstract_while_aiida.build(x=0, limit=5)
# wg.run()


from python_workflow_definition.aiida import load_workflow_json, write_workflow_json

write_workflow_json(wg=wg, file_name='write_while_loop.json')

# ## jobflow 

# In[12]:


from jobflow import job, Flow, Response
from jobflow.managers.local import run_locally


# In[13]:


def condition(x, limit):
    return limit > x


# In[14]:


def function_body(x):
    return x + 1


# In[15]:


@job
def abstract_while_jobflow(x, limit):
    if not condition(x, limit): 
        return x
    x = function_body(x)
    job_obj = abstract_while_jobflow(x=x, limit=limit)
    return Response(replace=job_obj, output=job_obj.output)


# In[16]:


flow = Flow([abstract_while_jobflow(limit=5, x=0)])
run_locally(flow)


# ## pyiron_base

# In[17]:


from pyiron_base import job, Project


# In[18]:


def condition(x, limit):
    return limit > x


# In[19]:


@job
def function_body(x):
    return x + 1


# In[20]:


# internal function
def while_generator(condition, function_body):
    def abstract_while_pyiron(x, limit, pyiron_project=Project(".")):
        if not condition(x=x, limit=limit):
            return x
        x = function_body(x=x, pyiron_project=pyiron_project).pull()
        return abstract_while_pyiron(x=x, limit=limit, pyiron_project=pyiron_project)

    return abstract_while_pyiron


# In[21]:


pr = Project("test")
pr.remove_jobs(recursive=True, silently=True)


# In[22]:


while_generator(condition=condition, function_body=function_body)(x=0, limit=5, pyiron_project=pr)


# # Abstract Syntax Tree

# In[23]:


from ast import dump, parse


# In[24]:


while_code = """\
x = 0 
while x < 5:
    x += 1
"""


# In[25]:


print(dump(parse(while_code), indent=4))


# In[ ]:





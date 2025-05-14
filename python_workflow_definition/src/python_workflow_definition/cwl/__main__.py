import sys
import pickle
from ast import literal_eval
import importlib.util


def load_function(file_name, funct):
    spec = importlib.util.spec_from_file_location("workflow", file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow"] = module
    spec.loader.exec_module(module)
    return getattr(module, funct.split(".")[-1])


def convert_argument(arg):
    if ".pickle" in arg:
        with open(arg, "rb") as f:
            return pickle.load(f)
    else:
        return literal_eval(arg)


if __name__ == "__main__":
    # load input
    argument_lst = sys.argv[1:]
    funct_lst = [arg.split("=")[-1] for arg in argument_lst if "--function=" in arg]
    file_lst = [arg.split("=")[-1] for arg in argument_lst if "--workflowfile=" in arg]
    if len(file_lst) > 0:
        workflow_function = load_function(file_name=file_lst[0], funct=funct_lst[0])
        internal_function = False
    else:
        m, p = funct_lst[0].rsplit(".", 1)
        workflow_function = getattr(importlib.import_module(m), p)
        internal_function = True
    kwargs = {
        arg.split("=")[0][6:]: convert_argument(arg=arg.split("=")[-1])
        for arg in argument_lst
        if "--arg_" in arg
    }

    # evaluate function
    result = workflow_function(**kwargs)

    # store output
    if isinstance(result, dict) and not internal_function:
        for k, v in result.items():
            with open(k + ".pickle", "wb") as f:
                pickle.dump(v, f)
    else:
        with open("result.pickle", "wb") as f:
            pickle.dump(result, f)

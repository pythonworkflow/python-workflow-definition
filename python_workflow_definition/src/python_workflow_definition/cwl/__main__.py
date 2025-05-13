import sys
import pickle
from ast import literal_eval
import importlib.util


def load_function(file_name, funct):
    spec = importlib.util.spec_from_file_location("workflow", file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules["workflow"] = module
    spec.loader.exec_module(module)
    return getattr(module, funct)


def convert_argument(arg):
    if ".pickle" in arg:
        with open(arg, "rb") as f:
            return pickle.load(f)
    else:
        return literal_eval(arg)


if __name__ == "__main__":
    # load input
    argument_lst = sys.argv[1:]
    funct = [arg.split("=")[-1] for arg in argument_lst if "--function=" in arg][0]
    file = [arg.split("=")[-1] for arg in argument_lst if "--workflowfile=" in arg][0]
    workflow_function = load_function(file_name=file, funct=funct)
    kwargs = {
        arg.split("=")[0][6:]: convert_argument(arg=arg.split("=")[-1])
        for arg in argument_lst
        if "--arg_" in arg
    }

    # evaluate function
    result = workflow_function(**kwargs)

    # store output
    if isinstance(result, dict):
        for k, v in result.items():
            with open(k + ".pickle", "wb") as f:
                pickle.dump(v, f)
    else:
        with open("result.pickle", "wb") as f:
            pickle.dump(result, f)

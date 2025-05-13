import sys
import pickle
from ast import literal_eval
import importlib.util


def load_function(funct):
    p, m = funct.rsplit(".", 1)
    spec = importlib.util.spec_from_file_location(p, p + ".py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[p] = module
    spec.loader.exec_module(module)
    return getattr(module, m)


def convert_argument(arg):
    if ".pickle" in arg:
        with open(arg, "rb") as f:
            return pickle.load(f)
    else:
        return literal_eval(arg)


if __name__ == "__main__":
    # load input
    argument_lst = sys.argv[1:]
    funct = [
        load_function(funct=arg.split("=")[-1])
        for arg in argument_lst
        if "--function=" in arg
    ][0]
    kwargs = {
        arg.split("=")[0][6:]: convert_argument(arg=arg.split("=")[-1])
        for arg in argument_lst
        if "--arg_" in arg
    }

    # evaluate function
    result = funct(**kwargs)

    # store output
    if isinstance(result, dict):
        for k, v in result.items():
            with open(k + ".pickle", "wb") as f:
                pickle.dump(v, f)
    else:
        with open("result.pickle", "wb") as f:
            pickle.dump(result, f)

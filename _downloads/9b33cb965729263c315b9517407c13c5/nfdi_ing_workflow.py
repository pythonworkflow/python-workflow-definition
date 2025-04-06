import os
from conda_subprocess import check_output
import shutil

source_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source")


def generate_mesh(domain_size: float = 2.0) -> str:
    stage_name = "preprocessing"
    gmsh_output_file_name = "square.msh"
    source_file_name ="unit_square.geo"
    os.makedirs(stage_name, exist_ok=True)
    _copy_file_from_source(stage_name=stage_name, source_file_name=source_file_name)
    _ = check_output(
        [
            "gmsh", "-2", "-setnumber", "domain_size", str(domain_size),
            source_file_name, "-o", gmsh_output_file_name
        ],
        prefix_name=stage_name,
        cwd=stage_name,
        universal_newlines=True,
    ).split("\n")
    return os.path.abspath(os.path.join(stage_name, gmsh_output_file_name))


def convert_to_xdmf(gmsh_output_file : str) -> dict:
    stage_name = "preprocessing"
    meshio_output_file_name = "square.xdmf"
    os.makedirs(stage_name, exist_ok=True)
    _copy_file(stage_name=stage_name, source_file=gmsh_output_file)
    _ = check_output(
        ["meshio", "convert", os.path.basename(gmsh_output_file), meshio_output_file_name],
        prefix_name=stage_name,
        cwd=stage_name,
        universal_newlines=True,
    ).split("\n")
    return {
        "xdmf_file": os.path.abspath(os.path.join(stage_name, meshio_output_file_name)),
        "h5_file": os.path.join(os.path.abspath(stage_name), "square.h5"),
    }


def poisson(meshio_output_xdmf: str, meshio_output_h5: str) -> dict:
    stage_name = "processing"
    poisson_output_pvd_file_name = "poisson.pvd"
    poisson_output_numdofs_file_name = "numdofs.txt"
    source_file_name = "poisson.py"
    os.makedirs(stage_name, exist_ok=True)
    _copy_file_from_source(stage_name=stage_name, source_file_name=source_file_name)
    _copy_file(stage_name=stage_name, source_file=meshio_output_xdmf)
    _copy_file(stage_name=stage_name, source_file=meshio_output_h5)
    _ = check_output(
        [
            "python", "poisson.py", "--mesh", os.path.basename(meshio_output_xdmf), "--degree", "2",
            "--outputfile", poisson_output_pvd_file_name, "--num-dofs", poisson_output_numdofs_file_name
        ],
        prefix_name=stage_name,
        cwd=stage_name,
        universal_newlines=True,
    ).split("\n")
    return {
        "numdofs": _poisson_collect_output(numdofs_file=os.path.join(stage_name, poisson_output_numdofs_file_name)),
        "pvd_file": os.path.abspath(os.path.join(stage_name, poisson_output_pvd_file_name)),
        "vtu_file": os.path.abspath(os.path.join(stage_name, "poisson000000.vtu")),
    }


def plot_over_line(poisson_output_pvd_file: str, poisson_output_vtu_file: str) -> str:
    stage_name = "postprocessing"
    pvbatch_output_file_name = "plotoverline.csv"
    source_file_name = "postprocessing.py"
    os.makedirs(stage_name, exist_ok=True)
    _copy_file_from_source(stage_name=stage_name, source_file_name=source_file_name)
    _copy_file(stage_name=stage_name, source_file=poisson_output_pvd_file)
    _copy_file(stage_name=stage_name, source_file=poisson_output_vtu_file)
    _ = check_output(
        ["pvbatch", source_file_name, os.path.basename(poisson_output_pvd_file), pvbatch_output_file_name],
        prefix_name=stage_name,
        cwd=stage_name,
        universal_newlines=True,
    ).split("\n")
    return os.path.abspath(os.path.join("postprocessing", pvbatch_output_file_name))


def substitute_macros(pvbatch_output_file: str, ndofs: int, domain_size: float = 2.0) -> str:
    stage_name = "postprocessing"
    source_file_name = "prepare_paper_macros.py"
    template_file_name = "macros.tex.template"
    macros_output_file_name = "macros.tex"
    os.makedirs(stage_name, exist_ok=True)
    _copy_file_from_source(stage_name=stage_name, source_file_name=source_file_name)
    _copy_file_from_source(stage_name=stage_name, source_file_name=template_file_name)
    _copy_file(stage_name=stage_name, source_file=pvbatch_output_file)
    _ = check_output(
        [
            "python", "prepare_paper_macros.py", "--macro-template-file", template_file_name,
            "--plot-data-path", os.path.basename(pvbatch_output_file), "--domain-size", str(domain_size),
            "--num-dofs", str(ndofs), "--output-macro-file", macros_output_file_name,
        ],
        prefix_name=stage_name,
        cwd=stage_name,
        universal_newlines=True,
    ).split("\n")
    return os.path.abspath(os.path.join(stage_name, macros_output_file_name))


def compile_paper(macros_tex: str, plot_file: str) -> str:
    stage_name = "postprocessing"
    paper_output = "paper.pdf"
    source_file_name = "paper.tex"
    os.makedirs(stage_name, exist_ok=True)
    _copy_file_from_source(stage_name=stage_name, source_file_name=source_file_name)
    _copy_file(stage_name=stage_name, source_file=macros_tex)
    _copy_file(stage_name=stage_name, source_file=plot_file)
    _ = check_output(
        ["tectonic", source_file_name],
        prefix_name=stage_name,
        universal_newlines=True,
        cwd=stage_name,
    ).split("\n")
    return os.path.abspath(os.path.join(stage_name, paper_output))


def _poisson_collect_output(numdofs_file: str) -> int:
    with open(os.path.join(numdofs_file), "r") as f:
        return int(f.read())


def _copy_file(stage_name, source_file):
    input_file = os.path.join(os.path.abspath(stage_name), os.path.basename(source_file))
    if input_file != source_file:
        shutil.copyfile(source_file, input_file)


def _copy_file_from_source(stage_name, source_file_name):
    source_file = os.path.join(source_directory, source_file_name)
    shutil.copyfile(source_file, os.path.join(stage_name, source_file_name))
"""Check Binder's notebook generation against the Python-only source tree."""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import PathFinder
from pathlib import Path

import nbformat
import yaml


class TestNotebookGeneration(unittest.TestCase):
    def test_example_sources_do_not_shadow_engine_imports(self):
        """Example directories leave engine imports available to installed packages."""
        root: Path = Path(__file__).resolve().parents[1]
        for directory in (root / "example_workflows").iterdir():
            if not directory.is_dir():
                continue
            for engine in (
                "aiida",
                "cwl",
                "executorlib",
                "jobflow",
                "pyiron_base",
                "pyiron_workflow",
            ):
                with self.subTest(directory=directory.name, engine=engine):
                    self.assertIsNone(PathFinder.find_spec(engine, [str(directory)]))

    def test_notebook_jobs_stop_on_first_execution_failure(self):
        """Every notebook job fails when the first Papermill invocation fails."""
        root: Path = Path(__file__).resolve().parents[1]
        pipeline = yaml.safe_load((root / ".github/workflows/pipeline.yml").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            directory: Path = Path(temporary)
            shutil.copytree(root / ".github", directory / ".github")
            (directory / "example_workflows/quantum_espresso/espresso").mkdir(
                parents=True
            )
            for name in ("nfdi", "arithmetic"):
                (directory / "example_workflows" / name).mkdir()
            log: Path = directory / "executions.log"
            for name, body in {
                "jupytext": "exit 0\n",
                "papermill": 'echo "$1" >> "$EXECUTION_LOG"\n[[ "$1" != aiida.ipynb ]]\n',
            }.items():
                executable: Path = directory / name
                executable.write_text(f"#!/usr/bin/env bash\n{body}")
                executable.chmod(0o755)
            environment: dict[str, str] = {
                **os.environ,
                "PATH": f"{directory}{os.pathsep}{os.environ['PATH']}",
                "EXECUTION_LOG": str(log),
            }
            for job in ("arithmetic", "nfdi4ing", "quantumespresso"):
                with self.subTest(job=job):
                    step = next(
                        step
                        for step in pipeline["jobs"][job]["steps"]
                        if step.get("name") == "Tests"
                    )
                    script: Path = directory / f"{job}.sh"
                    script.write_text(step["run"])
                    result = subprocess.run(
                        # Isolate CI's shell flags from local login profiles.
                        [
                            "bash",
                            "--noprofile",
                            "--norc",
                            *shlex.split(step["shell"].format(script))[1:],
                        ],
                        cwd=directory,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(log.read_text().splitlines(), ["aiida.ipynb"])
                    log.unlink()

    def test_binder_generates_all_examples_without_support_notebooks(self):
        """Binder generates 21 unexecuted notebooks and leaves support modules alone."""
        root: Path = Path(__file__).resolve().parents[1]
        commands: list[str] = [
            line
            for line in (root / "binder/postBuild").read_text().splitlines()
            if line.startswith("bash .github/scripts/generate-notebooks.sh ")
        ]
        self.assertEqual(len(commands), 1)
        engines: set[str] = {
            "aiida",
            "cwl",
            "executorlib",
            "jobflow",
            "pyiron_base",
            "pyiron_workflow",
            "universal_workflow",
        }
        expected: set[str] = {
            f"example_workflows/{directory}/{engine}.ipynb"
            for directory in ("arithmetic", "nfdi", "quantum_espresso")
            for engine in engines
        }
        with tempfile.TemporaryDirectory() as temporary:
            destination: Path = Path(temporary)
            shutil.copytree(root / ".github", destination / ".github")
            for source in (root / "example_workflows").glob("*/*.py"):
                target: Path = destination / source.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            environment: dict[str, str] = {
                **os.environ,
                "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            }
            subprocess.run(
                ["bash", "-euc", commands[0]],
                cwd=destination,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            generated: set[str] = {
                str(path.relative_to(destination))
                for path in destination.rglob("*.ipynb")
            }
            self.assertEqual(generated, expected)
            for name in sorted(expected):
                with self.subTest(notebook=name):
                    notebook = nbformat.read(destination / name, as_version=4)
                    self.assertEqual(notebook.metadata.kernelspec.name, "python3")
                    self.assertTrue(notebook.cells)
                    for cell in notebook.cells:
                        if cell.cell_type == "code":
                            self.assertIsNone(cell.execution_count)
                            self.assertEqual(cell.outputs, [])

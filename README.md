# Open B-Rep CLI

Open B-Rep CLI is a lightweight command-line project for experimenting with B-Rep Boundary Representation modeling. It focuses on a half-edge topology structure, Micro Euler Operators, sample model generation, and STEP export through text-based commands.

<p align="center">
<img src="https://github.com/mac999/open_brep_cli/blob/main/brep.gif" height="500"></img>
</p>

## Purpose

- Provide a lightweight CLI tool for learning and experimenting with CAD kernel structure and B-Rep topology modeling
- Validate topology operations and ID management based on Micro Euler Operators
- Serve as a foundation for testing standard STEP AP214 ADVANCED_BREP export and internal-format save/load workflows

## Features and Tech Stack

### Features

- Execute Micro Euler Operators such as `mvfs`, `mev`, `mef`, `mekr`, and `kemr`
- Generate sample plane and cube models
- Display solid topology in the CLI
- Export models to STEP AP214 ADVANCED_BREP
- Save and reload an internal STEP-like format
- Run unit tests with `unittest`

### Tech Stack

- Python
- NumPy
- Standard library modules: `cmd`, `shlex`, `pathlib`, `unittest`

## Usage

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python -m src.main
```

### CLI Examples

```text
sample cube 10
disp topology
save sample.step
save internal.step --internal
load internal.step
```

The `load` command currently works with files written by `save --internal`.

### Run Tests

```bash
python -m unittest discover tests
```

## License

This repository does not currently include a separate license file. If you plan to distribute or publish the project, add an explicit license that matches your intended use.

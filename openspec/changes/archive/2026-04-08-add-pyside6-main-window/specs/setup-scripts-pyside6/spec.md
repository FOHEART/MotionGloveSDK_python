## ADDED Requirements

### Requirement: PySide6 added to runtime dependencies in setup scripts
Both `[Windows]setup_python_libs.cmd` and `[Linux]setup_python_libs.sh` SHALL install `pyside6` (pinned version compatible with Python 3.10) into `libs/` using `pip install --target libs`. The installation SHALL be part of the existing runtime-dependencies step alongside `vtk`, `numpy`, etc.

#### Scenario: Windows setup installs PySide6 to libs/
- **WHEN** a user runs `[Windows]setup_python_libs.cmd` on Windows with Python 3.10
- **THEN** `pyside6` is installed into `libs/` and the script exits with code 0

#### Scenario: Linux setup installs PySide6 to libs/
- **WHEN** a user runs `bash [Linux]setup_python_libs.sh` on Linux/macOS with Python 3.10
- **THEN** `pyside6` is installed into `libs/` and the script exits with code 0

#### Scenario: Setup script fails loudly on pip error
- **WHEN** pip fails to install any package (e.g., network error)
- **THEN** the script exits with a non-zero exit code and an error message (existing behavior preserved)

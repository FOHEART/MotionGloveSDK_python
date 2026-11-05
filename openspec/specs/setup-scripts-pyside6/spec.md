## ADDED Requirements

### Requirement: PySide6 added to runtime dependencies in setup scripts
The dual-interpreter setup script `scripts/setup_python_libs.bat` (the same file is executed by `cmd.exe` on Windows
and by `sh` on Linux/macOS) SHALL install `pyside6` (pinned version compatible with Python 3.10) into `libs/` using
`pip install --target libs`. The installation SHALL be part of the existing runtime-dependencies step alongside
`vtk`, `numpy`, etc.

#### Scenario: Windows setup installs PySide6 to libs/
- **WHEN** a user runs `scripts\setup_python_libs.bat` on Windows with Python 3.10
- **THEN** `pyside6` is installed into `libs/` and the script exits with code 0

#### Scenario: Linux setup installs PySide6 to libs/
- **WHEN** a user runs `sh scripts/setup_python_libs.bat` on Linux/macOS with Python 3.10
- **THEN** `pyside6` is installed into `libs/` and the script exits with code 0

#### Scenario: Setup script fails loudly on pip error
- **WHEN** pip fails to install any package (e.g., network error)
- **THEN** the script exits with a non-zero exit code and an error message (existing behavior preserved)

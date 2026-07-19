HOW TO BUILD PROBOLISM SUITE AS WINDOWS EXE FILES
=================================================

This guide explains how to package these Python programs:

- ProbolismSearch.py
- ProbolismBrowser.py
- ProbolismSeestar.py
- ProbolismSuiteLauncher.py

The recommended tool is auto-py-to-exe, a graphical interface for
PyInstaller.

IMPORTANT
---------

- Build Windows EXE files on Windows.
- Use a 64-bit Python installation for a 64-bit Windows build.
- Test every Python script before packaging it.
- Use ONE DIRECTORY mode.
- Use CONSOLE BASED mode, especially for ProbolismSearch.
- Do not distribute only the EXE file from a One Directory build. Copy the
  whole generated folder, including the _internal directory.

The console is particularly useful in ProbolismSearch because it displays
catalogue-query progress, downloaded tiles, cache activity, warnings, failed
queries and diagnostic messages.


1. INSTALL PYTHON
=================

Install a current, supported 64-bit Python 3 release from:

https://www.python.org/downloads/windows/

During installation, select "Add python.exe to PATH" if this option is shown.

Verify the installation in PowerShell or Command Prompt:

    python --version

If that command is unavailable, try:

    py --version

Visual Studio Code does not include Python. Python must be installed
separately.


2. INSTALL VISUAL STUDIO CODE
=============================

Download and install Visual Studio Code from:

https://code.visualstudio.com/download

The standard Windows User Installer is suitable for most users.

Visual Studio Code is used to edit, run and test the Python programs. It does
not create the EXE itself. PyInstaller creates the package, while
auto-py-to-exe provides a graphical interface for PyInstaller.

Visual Studio Code is not the same product as the full Microsoft Visual Studio
IDE. The full Visual Studio installation is not normally required.


3. INSTALL THE PYTHON EXTENSION IN VS CODE
==========================================

1. Start Visual Studio Code.
2. Open Extensions with Ctrl+Shift+X.
3. Search for "Python".
4. Install the extension named "Python" published by Microsoft.
5. Open the Probolism Suite source folder with File -> Open Folder.
6. Press Ctrl+Shift+P.
7. Run "Python: Select Interpreter".
8. Select the Python installation used for this project.


4. CREATE A VIRTUAL ENVIRONMENT
===============================

A clean virtual environment is recommended because it prevents unrelated
packages from being included in the EXE files.

Open Terminal -> New Terminal in Visual Studio Code.

Create the environment:

    python -m venv .venv

Activate it in PowerShell:

    .\.venv\Scripts\Activate.ps1

Or activate it in Command Prompt:

    .venv\Scripts\activate.bat

If PowerShell blocks activation, use Command Prompt or run:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Then activate the environment again.

Upgrade the installation tools:

    python -m pip install --upgrade pip setuptools wheel


5. INSTALL ALL REQUIRED PACKAGES
================================

Install the complete dependency set:

    python -m pip install numpy pandas astropy astroquery pyvo pillow requests
    python -m pip install pyinstaller auto-py-to-exe

Important package-name notes:

- Install "pillow", although the Python import name is "PIL".
- pyvo is required by the astronomical query stack used by Search.
- Tkinter is normally included with the standard Windows Python installation.


Dependencies by program
-----------------------

ProbolismSearch.py:

- numpy
- pandas
- astropy
- astroquery
- pyvo

ProbolismBrowser.py:

- pandas
- pillow
- requests
- astropy

ProbolismSeestar.py:

- requests

ProbolismSuiteLauncher.py:

- Python standard library
- Tkinter

Launcher does not normally require an extra runtime package, but PyInstaller
and auto-py-to-exe are still required to create its EXE.


6. TEST THE PYTHON FILES FIRST
==============================

Before creating EXE files, start every program from the VS Code terminal:

    python ProbolismSearch.py
    python ProbolismBrowser.py
    python ProbolismSeestar.py
    python ProbolismSuiteLauncher.py

Adjust the filenames if the files in the repository use different names.

Recommended tests:

- Search: perform a small Gaia/VizieR search and save a CSV. Use default parameters and test field NGC4440.
- Browser: open a real candidate CSV and download one image.
- Seestar: open a candidate CSV and verify that records are displayed.
- Launcher: verify that its window opens correctly.

Fix all source or dependency errors before packaging.


7. INSTALL AND START AUTO-PY-TO-EXE
===================================

Install it in the active virtual environment:

    python -m pip install auto-py-to-exe

Start the graphical interface:

    auto-py-to-exe

If Windows says that the command is not recognized, use:

    python -m auto_py_to_exe


8. GENERAL AUTO-PY-TO-EXE SETTINGS
==================================

For each program, configure the following.


Script Location
---------------

Select the Python file to package.


Onefile or One Directory
------------------------

Select:

    One Directory

This is strongly recommended because scientific Python packages contain many
support files. One Directory builds are easier to test and troubleshoot and
usually start faster.

The generated folder will normally contain:

    ProgramName.exe
    _internal\

There may also be additional files. Keep all of them.


Console Window
--------------

Select:

    Console Based

This is recommended during development for all modules.

For the final release:

- ProbolismSearch should remain Console Based.
- Browser and Seestar are also easier to support as Console Based.
- Launcher may be changed to Window Based after the Console Based build has
  been fully tested.

A Window Based build hides useful error information.


Icon
----

An icon is optional. Use a Windows ICO file if an icon is selected.


Additional Files
----------------

Add files only when the Python code reads them at runtime, for example an
external icon, configuration file, image or sample data file.

Do not add arbitrary source folders.


Output Directory
----------------

Choose an empty output folder. Clean old builds before an important release.


9. SPECIAL BUILD SETTINGS FOR PROBOLISMSEARCH.PY
================================================

ProbolismSearch requires special PyInstaller options because astropy,
astroquery and pyvo contain package data that may not always be detected
automatically.

In auto-py-to-exe, open the Advanced section and find the field for additional
PyInstaller arguments.

Add exactly:

    --collect-data astroquery --collect-data pyvo --collect-data astropy

IMPORTANT:

- pyvo must also be installed in the active Python environment.

Recommended Search configuration:

    Script:
        ProbolismSearch.py

    Mode:
        One Directory

    Console:
        Console Based

    Additional Arguments:
        --name ProbolismSearch --collect-data astroquery --collect-data pyvo --collect-data astropy

The equivalent direct PyInstaller command is:

    python -m PyInstaller --noconfirm --clean --onedir --console --name ProbolismSearch --collect-data astroquery --collect-data pyvo --collect-data astropy ProbolismSearch.py

If the program still reports missing astropy, astroquery or pyvo submodules,
test the larger fallback:

    --collect-all astroquery --collect-all pyvo --collect-all astropy

The collect-all version creates a larger package, so use it only when the
collect-data build does not work.


10. BUILD PROBOLISMSEARCH
=========================

1. Start auto-py-to-exe.
2. Select ProbolismSearch.py.
3. Select One Directory.
4. Select Console Based.
5. Add:

       --name ProbolismSearch --collect-data astroquery --collect-data pyvo --collect-data astropy

6. Select an output directory.
7. Click "Convert .py to .exe".
8. Read the complete build output.
9. Open the generated ProbolismSearch folder.
10. Start ProbolismSearch.exe from that folder.
11. Run a small real search.
12. Confirm that catalogue progress appears in the console.
13. Confirm that CSV files can be written.

Do not move ProbolismSearch.exe away from its _internal folder.


11. BUILD PROBOLISMBROWSER
==========================

Recommended settings:

    Script:
        ProbolismBrowser.py

    Mode:
        One Directory

    Console:
        Console Based

    Additional Arguments:
        --name ProbolismBrowser

Equivalent command:

    python -m PyInstaller --noconfirm --clean --onedir --console --name ProbolismBrowser ProbolismBrowser.py

After building:

- start the EXE,
- open a candidate CSV,
- download and display an image,
- test navigation,
- test the cache,
- test image export.

If the packaged Browser reports missing astropy data, rebuild it with:

    --name ProbolismBrowser --collect-data astropy


12. BUILD PROBOLISMSEESTAR
==========================

Recommended settings:

    Script:
        ProbolismSeestar.py

    Mode:
        One Directory

    Console:
        Console Based

    Additional Arguments:
        --name ProbolismSeestar

Equivalent command:

    python -m PyInstaller --noconfirm --clean --onedir --console --name ProbolismSeestar ProbolismSeestar.py

After building:

- start the EXE,
- open a real candidate CSV,
- verify the displayed coordinates,
- test Alpaca discovery when compatible hardware is available,
- test GoTo only in a safe telescope environment.


13. BUILD PROBOLISMSUITELAUNCHER
================================

Recommended diagnostic settings:

    Script:
        ProbolismSuiteLauncher.py

    Mode:
        One Directory

    Console:
        Console Based

    Additional Arguments:
        --name ProbolismSuiteLauncher

Equivalent command:

    python -m PyInstaller --noconfirm --clean --onedir --console --name ProbolismSuiteLauncher ProbolismSuiteLauncher.py

After all diagnostics work, an optional Window Based Launcher can be built with:

    python -m PyInstaller --noconfirm --clean --onedir --windowed --name ProbolismSuiteLauncher ProbolismSuiteLauncher.py


14. ASSEMBLE THE COMPLETE SUITE
===============================

The Launcher expects exact executable names and relative paths.

Recommended final structure:

    ProbolismSuite\
    |-- ProbolismSuiteLauncher.exe
    |-- _internal\
    `-- modules\
        |-- search\
        |   |-- ProbolismSearch.exe
        |   `-- _internal\
        |-- browser\
        |   |-- ProbolismBrowser.exe
        |   `-- _internal\
        `-- seestar\
            |-- ProbolismSeestar.exe
            `-- _internal\

Other files generated by PyInstaller may also be present. Keep them.

Assembly procedure:

1. Use the generated One Directory Launcher folder as the Suite root.
2. Create:

       modules\search
       modules\browser
       modules\seestar

3. Copy the complete contents of the generated Search folder to:

       modules\search

4. Copy the complete contents of the generated Browser folder to:

       modules\browser

5. Copy the complete contents of the generated Seestar folder to:

       modules\seestar

6. Do not merge the three module _internal folders.
7. Do not copy only the EXE files.
8. Start ProbolismSuiteLauncher.exe.
9. Confirm that all three modules are detected.
10. Open each module from the Launcher.


15. CLEAN REBUILDS
==================

Before a release build:

1. Close all Probolism applications.
2. Delete obsolete build and dist folders.
3. Delete obsolete SPEC files if they are not needed.
4. Use an empty output folder.
5. Build with the clean option.
6. Rebuild all four programs.
7. Test the newly generated files rather than an older copied version.


16. TEST ON ANOTHER COMPUTER
============================

Test the complete package on another compatible Windows computer that does not
have the development environment installed.

Check:

- Launcher startup
- detection of all modules
- Search Gaia queries
- Search VizieR queries
- CSV output
- Browser CSV loading
- Browser image downloads
- Browser cache
- Seestar CSV loading
- Alpaca discovery when hardware is available
- write permissions
- diagnostics and logs
- Windows Defender or antivirus warnings


17. COMMON PROBLEMS
===================

The EXE closes immediately
--------------------------

Rebuild it as Console Based and start it from Command Prompt. Read the error in
the console.
Rub py code in Visula Studio Code, so it will be possible to see console messages because console will not close.


ModuleNotFoundError
-------------------

Verify that the package is installed in the same environment that runs
auto-py-to-exe:

    python -m pip show PACKAGE_NAME

Also confirm the selected VS Code interpreter.


Missing Search package data
---------------------------

Use:

    --collect-data astroquery --collect-data pyvo --collect-data astropy

If necessary, test:

    --collect-all astroquery --collect-all pyvo --collect-all astropy


Launcher cannot find a module
-----------------------------

Confirm these exact paths:

    modules\search\ProbolismSearch.exe
    modules\browser\ProbolismBrowser.exe
    modules\seestar\ProbolismSeestar.exe


Only the EXE was copied
-----------------------

Copy the complete One Directory output, including _internal.


auto-py-to-exe uses the wrong Python
-----------------------------------

Activate the intended environment and start the GUI from the same terminal:

    .\.venv\Scripts\Activate.ps1
    python -m auto_py_to_exe


pip requests a C or C++ compiler
--------------------------------

First upgrade the package tools:

    python -m pip install --upgrade pip setuptools wheel

Common supported Windows versions of numpy, pandas and astropy are normally
installed from prebuilt wheels.

Microsoft Visual C++ Build Tools may be needed only if pip cannot find a
compatible wheel and must build a dependency from source. Visual C++ Build
Tools are different from Visual Studio Code and are not normally required for
a standard supported installation.


18. OPTIONAL BUILD REQUIREMENTS FILE
====================================

A requirements-build.txt file may contain:

    numpy
    pandas
    astropy
    astroquery
    pyvo
    pillow
    requests
    pyinstaller
    auto-py-to-exe

Install it with:

    python -m pip install -r requirements-build.txt


19. RELEASE CHECKLIST
=====================

[ ] All four Python programs run from source.
[ ] A clean virtual environment was used.
[ ] All required dependencies were installed.
[ ] All programs were built in One Directory mode.
[ ] ProbolismSearch was built as Console Based.
[ ] Search includes collect-data for astroquery, pyvo and astropy.
[ ] Browser opens and displays a real candidate.
[ ] Seestar opens and reads a real candidate CSV.
[ ] Launcher finds all three modules.
[ ] Every _internal folder is included.
[ ] The complete Suite was tested outside the source folder.
[ ] The Suite was tested on another computer if possible.
[ ] README.txt is included.
[ ] File names and version numbers are consistent.


20. OFFICIAL DOCUMENTATION
==========================

Visual Studio Code:
https://code.visualstudio.com/download

Python in Visual Studio Code:
https://code.visualstudio.com/docs/languages/python

Python for Windows:
https://www.python.org/downloads/windows/

auto-py-to-exe:
https://pypi.org/project/auto-py-to-exe/

PyInstaller:
https://pyinstaller.org/en/stable/usage.html

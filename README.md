PROBOLISM SUITE
================

Overview
--------

Probolism Suite is a set of four astronomy applications designed to search for,
inspect, and observe candidate sky fields called "Probolisms".

Probolism is a small area of the sky in which a local
concentration or apparent grouping of stars and galaxies is detected. The term
"Probolism" is project-specific and is not an established astronomical term.

The software combines stellar data from the Gaia catalogue with galaxy data
available through VizieR. It searches selected sky regions, assigns scores to
candidate fields, saves the results to CSV files, displays astronomical preview
images, and can send selected coordinates to a Seestar telescope through
ASCOM Alpaca.

Probolism Suite is intended for exploratory astronomy, visual inspection, and
observation planning. It does not claim that stars and galaxies found in the
same field are physically related. In most cases, they are objects at very
different distances that only appear close together from the observer's point
of view.


Suite Components
----------------

Probolism Suite contains four independent programs:

1. Probolism Search
2. Probolism Browser
3. Probolism Seestar
4. Probolism Suite Launcher

The three main applications communicate through CSV files. They do not share
memory and do not need to run at the same time. The Launcher acts as a menu for
starting them.


1. Probolism Search
-------------------

Probolism Search is the analytical part of the suite.
[it can take some time to start, please wait]

It searches a selected region of the sky using:

- Gaia DR3 stellar data
- Galaxy data from the RC3 catalogue through VizieR

The user can search:

- a constellation,
- a field around a Messier object,
- a predefined test field (NGC4440 and its surroundings),
- or a custom rectangular sky area.

The program divides the selected region into small, partially overlapping cells.
For each cell, it counts stars and galaxies that meet the selected magnitude and
size limits.

The user can configure parameters such as:

- cell size,
- grid step,
- stellar magnitude limit,
- galaxy magnitude limit,
- minimum galaxy angular size,
- minimum number of stars,
- minimum number of galaxies,
- and the scoring method.

Available scoring methods include:

- stars x galaxies
- stars x galaxies squared
- stars squared x galaxies squared

Each field receives a raw score and a normalized score. Candidate fields are
classified as A, B, C, or none according to their relative strength within the
currently searched region.

Because neighboring cells overlap, the program also removes duplicate or nearly
duplicate detections and keeps the stronger candidate where appropriate.

The results are saved as CSV files. Typical columns include:

- center_RA
- center_DEC
- center_RA_current
- center_DEC_current
- g_star - numner of detected stars
- g_gal - numner of detected galaxies
- galaxies - names of detected galaxies
- P_raw - probolism scoring 
- P_norm - probolism scoring normalized
- klasa - probolism class (A, B, C, none)

The center_RA and center_DEC columns contain ICRS/J2000 coordinates used for
identification and image retrieval. The center_RA_current and
center_DEC_current columns contain coordinates transformed to the current epoch
for telescope use.


2. Probolism Browser
--------------------

Probolism Browser is used to inspect candidate fields visually.

It opens CSV files created by Probolism Search and downloads astronomical
preview images from the CDS/Aladin HiPS2FITS service.

Available surveys may include:

- DSS2 color
- DSS2 red
- 2MASS
- AllWISE
- Pan-STARRS
- SDSS

For each candidate, the Browser can:

- display the corresponding sky image,
- mark the center of the field,
- show candidate statistics,
- identify the constellation,
- resolve galaxy names,
- mark galaxies on the image,
- calculate which listed galaxy is closest to the field center,
- export selected images and records to jpg and csv files.

Downloaded images are stored in a local cache so that previously viewed fields
can be opened again without downloading the same image.


3. Probolism Seestar
--------------------

Probolism Seestar is a simple GoTo controller for compatible Seestar telescope
setups exposed through ASCOM Alpaca.

It reads a Probolism CSV file, displays the candidate records, and sends the
selected coordinates to a telescope over the local network.

The program can:

- discover ASCOM Alpaca devices on the network,
- list available telescope devices,
- connect to the selected device,
- unpark the telescope when supported,
- enable tracking when supported,
- send an asynchronous GoTo command,
- and abort a slew if needed.

The module also contains a built-in Messier catalogue, allowing the user to send
the telescope to a Messier object without opening a Probolism CSV file.

Important limitations:

- It sends GoTo commands only.
- It does not perform plate solving.
- It does not automatically center the target.
- It does not focus the telescope.
- It does not start imaging or stacking.
- The computer and the telescope interface must be available on the same local
  network.
- A compatible ASCOM Alpaca telescope device must be configured.


4. Probolism Suite Launcher
---------------------------

Probolism Suite Launcher is the main menu for the suite.

It starts the three independent applications:

- Probolism Search
- Probolism Browser
- Probolism Seestar

Each module runs as a separate process. Closing the Launcher does not close
applications that have already been started.

The Launcher also provides:

- module availability checks,
- a user guide,
- a diagnostics report,
- access to the logs folder,
- and basic information about the installation.

When distributed as a Windows application, the expected folder structure is:

ProbolismSuite/
|-- ProbolismSuiteLauncher.exe
|-- _internal/
`-- modules/
    |-- search/
    |   |-- ProbolismSearch.exe
    |   `-- _internal/
    |-- browser/
    |   |-- ProbolismBrowser.exe
    |   `-- _internal/
    `-- seestar/
        |-- ProbolismSeestar.exe
        `-- _internal/

Do not move a packaged executable away from its accompanying _internal folder.


Typical Workflow
----------------

A normal workflow is:

[search]
1. Start Probolism Search.
2. Select a sky region and search parameters.
3. Calculate and save Probolism candidates to a CSV file.

[browse and select]
4. Open the CSV file in Probolism Browser.
6. Inspect candidate images and statistics.
7. Select an interesting probolisms.

[see on real sky]
8. Open the same CSV file in Probolism Seestar.
9. Connect to the ASCOM Alpaca telescope device.
10. Send the candidate coordinates to the telescope.

The CSV files are the data interface between the three main applications.

Requirements
------------

The source-code versions require Python 3 and the following packages.

Probolism Search:
- numpy
- pandas
- astropy
- astroquery

Probolism Browser:
- pandas
- Pillow
- requests
- astropy

Probolism Seestar:
- requests

The graphical interface uses Tkinter, which is included with most standard
Python installations.

Internet access is required for:

- Gaia queries,
- VizieR queries,
- HiPS2FITS image downloads,
- and astronomical name resolution.

The packaged Suite and Launcher are primarily designed for Microsoft Windows.


Data Sources and Online Services
--------------------------------

Probolism Suite may use the following external catalogues and services:

- ESA Gaia Archive / Gaia DR3
- CDS VizieR
- RC3 galaxy catalogue
- CDS Aladin HiPS2FITS
- CDS Sesame name resolver
- ASCOM Alpaca devices on the local network

Availability and response times depend on external services and the user's
network connection.


Interpretation of Results
-------------------------
A high Probolism score means that a field contains a comparatively strong
combination of stars and galaxies according to the selected parameters and
scoring method.

The score is relative to the current search area. A class A candidate from one
search is not necessarily directly comparable with a class A candidate from a
different constellation, field size, magnitude limit, or scoring configuration.

The results should therefore be treated as candidate fields for further visual
inspection, not as proof of a new physical astronomical structure.


Current Design Notes
--------------------
- The programs are independent desktop applications.
- CSV files are selected manually in Browser and Seestar.
- Search results and downloaded images may be cached locally.
- Network errors can affect catalogue completeness.
- Telescope behavior depends on the connected ASCOM Alpaca implementation.
- The software is intended for exploration and observation support rather than
  professional scientific validation or autonomous telescope operation.


Authorship
----------
Probolism Suite was developed by piotrs with the assistance of AI tools,
including ChatGPT, for code creation, review, and improvement.

contact to author: grazyk ?I think at is in this place? wp $here is one dot, I suggest$ pl


# PIQQA
The PI's Quick Quality Assessment

PIQQA is python utility to create a simple Quality Assurance report. Developed by the IRIS DMC, this tool is intended for use by the PASSCAL Instrument Center, meant to generate an easy-to-digest QA report for PIs after their experiment wraps.

The command-line utility retrieves MUSTANG metrics, PDFs, and spectrograms, as well as metadata from the IRIS station service, putting them all together in a report.

The final report has 5 sections: Boxplots, PDFs, Spectrograms, Map, and Stations. 

Boxplots, PDFs, and Spectrograms are displayed for each channel groups (for example, DP or BH) included in the report.

PDFs and Spectrograms are displayed for the stations with the smallest and greatest scaled sample_rms values, and PDFs are also displayed for a composite of all stations within that channel group. 

## Installation

PIQQA is distributed through _GitHub_, via IRIS's public repository (_iris-edu_). You will use a ```git``` 
client command to get a copy of the latest stable release. In addition, you will use the ```miniconda``` 
python package manager to create a customized Python environment designed to run PIQQA properly.

If running macOS, Xcode command line tools should be installed. Check for existence and install if 
missing:
```
xcode-select --install
```

Follow the steps below to begin running PIQQA.

### Download the Source Code

You must first have ```git``` installed your system. This is a commonly used source code management system
and serves well as a mode of software distribution as it is easy to capture updates. See the 
[Git Home Page](https://git-scm.com/) to begin installation of git before proceeding further.

After you have git installed, you will download the PIQQA distribution into a directory of your choosing 
from GitHub by opening a text terminal and typing:

```
git clone https://github.com/iris-edu/piqqa.git
```

This will produce a copy of this code distribution in the directory you have chosen. When new piqqa versions 
become available, you can update PIQQA by typing:

```
cd piqqa
git pull origin main
```

### Install the Anaconda Environment

[Anaconda](https://www.anaconda.com) is a package manager for 
scientific applications written python or R. [Miniconda](http://conda.pydata.org/miniconda.html) is a trimmed 
down version of Anaconda that contains the bare necessities without loading a large list of data science packages 
up front. With miniconda, you can set up a custom python environment with just the packages you need to run PIQQA.

If you do not already have Anaconda or Miniconda set up on your computer, proceed to the [Miniconda](http://conda.pydata.org/miniconda.html) web site to find the installer for your
operating system before proceeding with the instructions below. If you can run ```conda``` from the command 
line, then you know you have it successfully installed.

By setting up a [conda virtual environment](https://conda.io/projects/conda/en/latest/user-guide/concepts.html#conda-environments), we assure that our 
PIQQA installation is entirely separate from any other installed software.


### Creating the piqqa environment for macOS or Linux 

You will go into the piqqa directory that you created with git, update miniconda, then create an 
environment specially for piqqa. You have to ```activate``` the PIQQA environment whenever you 
perform installs, updates, or run PIQQA.

```
cd piqqa
conda update conda
conda create --name piqqa -c conda-forge --file piqqa-conda-install.txt
conda activate piqqa
```

See what is installed in our (piqqa) environment with:

```
conda list
```
<br /> 
Every time you use PIQQA, make sure that you `conda activate piqqa` to ensure that it will run smoothly. 

<br /> 

## Using PIQQA 

Every time you use PIQQA you must ensure that you are running in the proper Anaconda
environment. If you followed the instructions above you only need to type:

```
cd piqqa
conda activate piqqa
```

after which your prompt should begin with ```(piqqa)```. To run PIQQA, you use the ```PIQQA.py``` 
python script that lives in the piqqa directory. 


Then to run:
```
python PIQQA.py
```

Running PIQQA.py without any arguments, or with the -h/--h flags, will produce some helpful information.

```
(piqqa)$ python PIQQA.py

    PIQQA USAGE:  python PIQQA.py --network=NET --start=YYYY-mm-dd --end=YYYY-mm-dd

    Required Fields:
        --network=: network code
        --start=: start date, YYYY-mm-dd
        --end=: end date, YYYY-mm-dd; time defaults to 00:00:00, so to include all of 2020 the end date would be 2021-01-01
    Optional Fields
        --stations=: comma-separated list of station codes; defaults to "*"
        --locations=: comma-separated list of location codes; defaults to "*"
        --channels=: comma-sparated list of channel groups (HH, BH); defaults to "*"
        --metrics=: comma-separated list of metrics to run for the boxplots; defaults: ts_channel_up_time,sample_rms,num_gaps
        --maxplot=: number of stations to include in the boxplots; defaults to 30
        --colorpalette=: color palette for spectrograms; defaults to 'RdYlBu'
            options available at http://service.iris.edu/mustang/noise-spectrogram/1/
        --includeoutliers=: whether to include outliers in the boxplots, True/False; defaults to False
        --spectralrange=: power range to use in the PDFs and spectrograms, comma separated values:  min, max; defaults depend on channel type
        --basemap=: the name of the basemap to be used for the map; defaults to 'open-street-map'

    If PIQQA is not working as expected, ensure that the conda environment is activated
```

The only required fields are:

`network` is the 2-letter network code that should be included in the report.

`start` is the first day of the report.

`end` is the day _after_ the final day of the report

Just like in MUSTANG, the day rounds to 00:00:00. This means that the end date is non-inclusive, so to include the entirety of 2020, say, then the dates should be --start=2020-01-01 and --end=2021-01-01.


In addition to those fields, there are a number of optional fields. 

`stations`, `locations`, and `channels` are all ways to narrow down the report by limiting the targets included.  `channels` should be a two-letter code, or list of two-letter codes, such as DP, BH.

`metrics` can be used to limit or expand the metrics included in the report. No matter what, percent_availability and sample_rms will always be included in the metric list, as they are special metrics used throughout the report.

`maxplot` is how you can limit the number of stations displayed in the boxplots.

`colorpalette` determines the color palette used in the PDFs and spectrograms, and a list of all options can be found in the service interface page for the [noise-spectrgram](http://service.iris.edu/mustang/noise-spectrogram/1/) service

`includeoutliers` toggles the outliers on/off in the boxplots. Generally, it is easier to view the boxplots with the outliers turned off, but there may be cases where they should be displayed.

`spectralrange` determines the displayed power range for both the PDFs and spectrograms. There are built-in defaults that are dependent on the channel type, and therefore inferred instrumentation.
```
    [-175,-75]: BH, EH, HH, MH, SH
    [-175,-20]: EN, BN
    [-175,-60]: EP, DP, GP
```
`basemap` specifies the basemap to be used in the Map section. Current options include: "open-street-map", "carto-positron", "carto-darkmatter", "stamen-terrain", "stamen-toner" or "stamen-watercolor".






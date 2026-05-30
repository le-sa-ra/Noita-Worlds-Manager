# Windows "smart app control"
If windows prevents you from opening the exe you can either try to disable it for the exe specifically, or you will have to do a little bit of work to get it working on your machine.

If you decide to create the exe locally you may continue reading this page.
## Pre-requisites:
In order to get started you will need:
* the **Source code** zip of this repository
* the **[python](https://www.python.org/)** programming language

### Source code:
The zip that needs to be extracted on your machine can be found as ```Source code (zip)``` on the release page of NWM. <br>
Alternatively the zip can be downloaded by following the numbered steps in the image below :
<br><img src="README_ASSETS\download_zip.png"/><br>
(Located on the homepage of Noita-Worlds-Manager on GitHub)

### Python
This program was written in python and requires the [python](https://www.python.org/) programming language to run.

You can download the [python version 3.13.*](https://www.python.org/downloads/release/python-31313/) which this project runs on (you may try more [up-to-date versions](https://www.python.org/downloads/) of python, however I cannot promise the following steps will work).

## Making the exe
Once you have the zip of the source code and python installed you can proceed with the next steps:
1. extract the zip containing the source code and open the extracted folder
2. you will need to open a terminal in the folder containing the: readme, license, assets folder and whatnot
3. once you have a terminal opened in this directory you should be able to just paste the following code:
    ```
    py -m pip install -r requirements.txt
    py -m PyInstaller --clean -F -w -i assets/image/ico.ico --hidden-import=psutil --collect-all psutil --add-data "assets:assets" nwm.py

    ```
    If all went well you should see a new folder named ```dist/```. within this folder, a file named "nwm.exe".<br>

    The lines of code above execute two steps:
    1. Installing the required Python libraries:
        ```
        py -m pip install -r requirements.txt
        ```
    2. Making the exe with all assets needed:
        ```
        py -m PyInstaller --clean -F -w -i assets/image/ico.ico --hidden-import=psutil --collect-all psutil --add-data "assets:assets" nwm.py
        ```
# Corona Hakab Simulator

## Install and run the simulator from PyCharm (recommended):
- Install Python 3.8.x for Win64
    - Download Windows x86-64 executable installer from **https://www.python.org/downloads/windows/**
    - Install it (i.e. to C:\Python38)
- Install GIT
    - Download and install 64-bit Git for Windows Setup from **https://git-scm.com/**
- Install PyCharm (Community edition is good enough)
    - **https://www.jetbrains.com/pycharm/download/#section=windows**
- VCS -> Checkout from version control -> git
    - **https://github.com/CoronaHakab/CoronaHakabModel.git**
    - choose directory as you please
- File -> Settings -> Project Interpreter ->
    - Click on the plus sign on the right
        - add pipenv
    - Right click on the cog on the top right -> add
        - Pipenv environment ->
            - Base Interpreter Python 3.8 (C:\Python38)
            - Check install packages from pipfile
            - Pipenv executable (C:\Python38\Scripts\pipenv.exe)
            - OK
- In order to make PyCharm recognize the project modules:
    - right click src folder -> Mark directory as -> Source Root
    - right click src/corona_hakab_model folder -> Mark directory as -> Source Root
- double click src/corona_hakab_model folder/main.py and run it (Run -> Run)

## Install and run the simulator from cmd (also possible):
- Install Python 3.8
- pip install pipenv
- run **git clone https://github.com/CoronaHakab/CoronaHakabModel.git** from your dev directory (i.e. c:\dev)
- Create a pipenv environment and install the dependencies
    - full dependencies (for developers): **pipenv install --dev**
    - minimal dependencies (for researches): **pipenv install**
- go to src/corona_hakab_model folder
    - run: **python main.py**
    
## Creating a Constants JSON
You can modify the constants for the models including the total execution steps, infection rates, medical state machine,
detection test parameters and policy changes via a JSON file. An example can be found at 
`tests/simulation_sanity_test/default_consts.json`.

You can test your JSON file against the JSON schema for the
constants, this file is found at `src/corona_hakab_model/consts-schema.json`.

To do so, for those without PyCharm:
1. Open `https://www.jsonschemavalidator.net` in your web browser.
2. Copy the contents of `src/corona_hakab_model/consts-schema.json` to the left-hand side panel where it says select
schema.
3. Copy the contents of your JSON file to the right-hand side panel.
4. See the "Found x error(s)" messages, the messages are also shown with a notice beside the lines that are invalid.
5. Once you see " No errors found. JSON validates against the schema", you are good to go!
 

## Optional - Export/Import matrices!
- Export: **python main.py -o <PATH>**
- Import: **python main.py -i <PATH>**

## Workflow -
- When working, **work on a new git branch**.
- When done, **push changes to your branch, and create a pull request**.
- **Always run the simulator after making changes and before merging**, to make sure you didn't break anything.
- Especially if not sure, **try to get at least 1 person's review before merging**.

## New to git/github?
See the **"How to set up a git environment"** guide in the docs folder.

For Pull-Requests, look at this guide, from step 7 -
[https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners](https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners).


# iRule-Alteon-Tester

## Description ##
The following script is used to test F5 iRule as an AppShape++ in an Alteon device, 
Script expects to find each iRule in seprate text file under "Original" directory

## How To Use ##
* Download `Tester.py`
* Provide Alteon Management IP and credentials (inside the script)
* Create follwoing folders inside "workdir":
  * Original - should hold iRules we want to test
  * Successful - the script will place all AppShapes that passed apply in the Alteon (after all required modifications)
  * Errors - the script will create a seprate log file for each failed iRule (including the apply result)
* Place iRules (including the command including iRule name) or full configuration file (bigip.conf) in "Original" directory
* Run `Tester.py`

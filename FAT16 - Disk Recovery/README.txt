HOW TO RUN THE SCRIPT:
Simply enter the Programs folder and run the main.py script.
$ python3 main.py

It will output all the necessary information in the terminal and the recovered files will be saved in the RecoveredFiles directory.

- Evidence folder contains the forensically relevant artifacts with their hash (2 files + checksum.md5)
- RecoveredFiles folder contains 55 files retrieved from the image and their hash (checksum.md5)
- Docs folder contains: the report in pdf (which has the information asked in the brief) and 
the custody document of the disk image as evidence part of the investigation conducted 
by ACME Forensics (that contains the md5 hash of the image).

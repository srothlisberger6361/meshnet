@echo off
set DOWNLOAD_URL=https://github.com/srothlisberger6361/knocker/raw/main/Knock.exe
set EXECUTABLE_NAME=knocker.exe
set PORTS=1293 1500 27039
set IP=[Server IP]

REM Download the executable
curl -o %EXECUTABLE_NAME% %DOWNLOAD_URL%

REM Perform port knocking using the downloaded executable
%EXECUTABLE_NAME% %IP% %PORTS%

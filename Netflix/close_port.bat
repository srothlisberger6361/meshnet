@echo off
set DOWNLOAD_URL=http://github.com/srothlisberger6361/knocker.exe
set EXECUTABLE_NAME=knocker.exe
set PORTS=1234,5678,9012
set IP=[Server IP]

REM Download the executable
curl -o %EXECUTABLE_NAME% %DOWNLOAD_URL%

REM Perform port knocking using the downloaded executable
%EXECUTABLE_NAME% %IP% %PORTS%

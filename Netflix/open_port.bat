@echo off
REM Set the download URL for Ncat
set ncatUrl=https://nmap.org/dist/ncat-portable-7.91.zip
REM Set the directory to store Ncat
set ncatDir=%~dp0\ncat
REM Set the Ncat executable path
set ncatExe=%ncatDir%\ncat.exe
REM Replace 'your_server_ip' with the actual IP address of your Linux server
set serverIP=your_server_ip
REM Define the sequence of ports to knock
set knockPorts=1500 27039 1293
REM Create the Ncat directory if it doesn't exist
if not exist "%ncatDir%" mkdir "%ncatDir%"
REM Download and extract Ncat
powershell -Command "(New-Object Net.WebClient).DownloadFile('%ncatUrl%', '%ncatDir%\ncat.zip')" && \
powershell -Command "Expand-Archive -Path '%ncatDir%\ncat.zip' -DestinationPath '%ncatDir%' -Force"
REM Loop through the sequence and send a UDP packet to each port using Ncat
for %%i in (%knockPorts%) do (
    %ncatExe% -udp -send-only %serverIP% %%i
)
REM Wait for 3 minutes (180 seconds)
timeout /t 180 /nobreak
REM Run close_port.bat
call close_port.bat


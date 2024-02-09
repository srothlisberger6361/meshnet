@echo off
set DOWNLOAD_URL=http://github.com/srothlisberger6361/knocker.exe
set EXECUTABLE_NAME=knocker.exe
set PORTS=1234,5678,9012
set IP=[Server IP]

REM Download the executable
curl -o %EXECUTABLE_NAME% %DOWNLOAD_URL%

REM Perform port knocking using the downloaded executable
%EXECUTABLE_NAME% %PORTS%

REM Start OpenVPN with any client*.ovpn file in the same directory
for %%F in ("%~dp0\client*.ovpn") do (
    start /B openvpn --config "%%~dpF"
)

REM Wait for 3 minutes
timeout /t 180 /nobreak

REM Stop the OpenVPN client connection
taskkill /IM openvpn.exe /F

REM Execute the close_port.bat script
call close_port.bat

REM Clean up - delete the downloaded executable
del %EXECUTABLE_NAME%

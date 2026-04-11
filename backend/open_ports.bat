@echo off
echo Opening Port 8000 in Windows Firewall for Rakshak Mobile App...
netsh advfirewall firewall add rule name="Rakshak Port 8000" dir=in action=allow protocol=TCP localport=8000
echo.
echo Firewall rule added successfully! You can press any key to close this window.
pause >nul

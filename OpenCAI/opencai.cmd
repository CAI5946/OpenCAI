@echo off
pushd "%~dp0.."
python -m OpenCAI %*
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%

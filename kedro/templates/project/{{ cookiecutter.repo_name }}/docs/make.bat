@ECHO OFF

pushd %~dp0

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
if "%SPHINXAPIDOC%" == "" (
	set SPHINXAPIDOC=sphinx-apidoc
)
set SOURCEDIR=source
set BUILDDIR=build
set PACKAGEDIR=..\src\{{ cookiecutter.python_package }}

if "%1" == "" goto help

if "%1" == "html" (
	%SPHINXAPIDOC% -o "%SOURCEDIR%" "%PACKAGEDIR%" --force
	if errorlevel 1 exit /b 1
)

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

%SPHINXBUILD% -M %1 "%SOURCEDIR%" "%BUILDDIR%" %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help "%SOURCEDIR%" "%BUILDDIR%" %SPHINXOPTS% %O%

:end
popd

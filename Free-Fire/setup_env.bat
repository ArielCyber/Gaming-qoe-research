@echo off
:: מעבר אוטומטי לתיקייה שבה הקובץ נמצא
cd /d "%~dp0"
echo [INFO] Checking environment in: %cd%

:: 1. יצירת הסביבה (רק אם חסרה)
if not exist "venv_win\" (
    echo [INFO] Virtual environment not found. Creating 'venv_win'...
    python -m venv venv_win
    echo [SUCCESS] venv_win created.
) else (
    echo [INFO] Virtual environment already exists.
)

:: 2. הפעלה (קורה תמיד, לכן זה מחוץ ל-if)
echo [INFO] Activating environment...
call venv_win\Scripts\activate

:: 3. בדיקת ספריות (קורה תמיד - זה הביטוח שלנו)
echo [INFO] Verifying libraries from requirements.txt...
python -m pip install --upgrade pip
pip install -r requirements.txt --quiet --no-python-version-warning
echo [SUCCESS] All libraries installed and up to date.

echo.
echo ======================================================
echo    ENV ACTIVE: (venv_win) is ready for your commands.
echo    You can now run: python notebook_cleaner.py
echo    Or type: jupyter notebook
echo ======================================================
echo.

:: הפקודה שמשאירה את הטרמינל פתוח ובמצב פעיל
cmd /k

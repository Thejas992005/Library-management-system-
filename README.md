# Library Management System

A local, browser-based Library Management System built with Python, Streamlit, and SQLite.

## Features
- Dashboard with books, copies, members, active loans, and overdue loans
- Book catalogue: add, search, edit, delete (deletion blocked when loan history exists)
- Member registration, search, and profile updates
- Issue and return books with automatic available-copy tracking
- Due dates and late fine calculation
- Loan history, report filtering, top borrowed books chart
- CSV exports for books, members, and loans
- SQLite database backup
- Sample records added on first run

## Requirements
- Python 3.10 or newer
- Internet access once, to install the Python packages

## Windows setup
1. Extract the ZIP to a folder.
2. Open Command Prompt or PowerShell in that folder.
3. (Recommended) Create a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install packages:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```powershell
   python -m streamlit run app.py
   ```
6. Your browser will open the app, normally at `http://localhost:8501`.

If `python` is not recognized, try `py -m pip install -r requirements.txt` and `py -m streamlit run app.py`.

## Data and backup
- Data is stored in `library.db` in the same folder as `app.py`.
- Do not delete `library.db` if you want to keep your data.
- Use Settings → Create database backup to create and download a backup.

## Important notes
- This is a functional starter application suitable for local demos and student projects.
- It does not include user login/roles, cloud hosting, email/SMS notifications, barcode scanning, or multi-user concurrency controls.
- Before production use, add authentication, authorization, input/security review, and a tested backup/restore process.

import sqlite3
from datetime import date, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "library.db"

st.set_page_config(page_title="Library Management System", page_icon="📚", layout="wide")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT UNIQUE,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            publisher TEXT DEFAULT '',
            year INTEGER,
            total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
            available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            joined_on TEXT NOT NULL DEFAULT CURRENT_DATE,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL REFERENCES books(id),
            member_id INTEGER NOT NULL REFERENCES members(id),
            issued_on TEXT NOT NULL,
            due_on TEXT NOT NULL,
            returned_on TEXT,
            fine REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Issued'
        );
        """)
        # Seed a few sample records only when the database is empty.
        if conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            sample_books = [
                ("9780132350884", "Clean Code", "Robert C. Martin", "Programming", "Prentice Hall", 2008, 4, 4),
                ("9780262033848", "Introduction to Algorithms", "Thomas H. Cormen et al.", "Computer Science", "MIT Press", 2009, 3, 3),
                ("9780596009205", "Head First Java", "Kathy Sierra & Bert Bates", "Programming", "O'Reilly", 2005, 2, 2),
            ]
            conn.executemany("""INSERT INTO books
                (isbn,title,author,category,publisher,year,total_copies,available_copies)
                VALUES (?,?,?,?,?,?,?,?)""", sample_books)
        if conn.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
            conn.execute("INSERT INTO members(name,email,phone,address) VALUES (?,?,?,?)",
                         ("Demo Member", "demo.member@example.com", "9000000000", "Sample address"))

def query_df(sql, params=()):
    with get_db() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql, params=()):
    with get_db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid

def get_book(book_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()

def get_member(member_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()

def fmt_date(value):
    return pd.to_datetime(value).date()

init_db()

st.title("📚 Library Management System")
st.caption("Manage books, members, issue/return transactions, overdue loans, and reports.")
pages = ["Dashboard", "Books", "Members", "Issue / Return", "Reports", "Settings"]
page = st.sidebar.radio("Navigation", pages)
st.sidebar.divider()
st.sidebar.caption("Local SQLite database • Streamlit")

if page == "Dashboard":
    books = query_df("SELECT * FROM books")
    members = query_df("SELECT * FROM members WHERE active=1")
    loans = query_df("SELECT * FROM loans")
    active_loans = loans[loans["status"] == "Issued"] if not loans.empty else loans
    today = date.today().isoformat()
    overdue = active_loans[active_loans["due_on"] < today] if not active_loans.empty else active_loans
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Book titles", len(books))
    c2.metric("Total copies", int(books["total_copies"].sum()) if not books.empty else 0)
    c3.metric("Active members", len(members))
    c4.metric("Books currently issued", len(active_loans))
    st.subheader("Overdue loans")
    if overdue.empty:
        st.success("No overdue loans.")
    else:
        overdue_view = overdue.merge(books[["id","title"]], left_on="book_id", right_on="id", suffixes=("","_book"))
        overdue_view = overdue_view.merge(query_df("SELECT id,name,email FROM members"),
                                          left_on="member_id", right_on="id", suffixes=("","_member"))
        st.dataframe(overdue_view[["id","title","name","email","issued_on","due_on"]], use_container_width=True, hide_index=True)
    st.subheader("Recently added books")
    st.dataframe(query_df("SELECT title,author,category,available_copies,total_copies FROM books ORDER BY id DESC LIMIT 5"),
                 use_container_width=True, hide_index=True)

elif page == "Books":
    st.subheader("Book catalogue")
    with st.expander("➕ Add a book", expanded=False):
        with st.form("add_book", clear_on_submit=True):
            c1,c2 = st.columns(2)
            isbn = c1.text_input("ISBN (optional)")
            title = c2.text_input("Title *")
            author = c1.text_input("Author *")
            category = c2.text_input("Category", value="General")
            publisher = c1.text_input("Publisher")
            year = c2.number_input("Publication year", min_value=0, max_value=2100, value=2024, step=1)
            copies = st.number_input("Number of copies", min_value=1, max_value=10000, value=1)
            submitted = st.form_submit_button("Add book", type="primary")
            if submitted:
                if not title.strip() or not author.strip():
                    st.error("Title and author are required.")
                else:
                    try:
                        execute("""INSERT INTO books(isbn,title,author,category,publisher,year,total_copies,available_copies)
                                   VALUES(?,?,?,?,?,?,?,?)""",
                                (isbn.strip() or None,title.strip(),author.strip(),category.strip() or "General",
                                 publisher.strip(),int(year),int(copies),int(copies)))
                        st.success("Book added.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That ISBN already exists. Use a unique ISBN or leave it blank.")

    all_books = query_df("SELECT * FROM books ORDER BY title")
    q = st.text_input("Search by title, author, ISBN, or category")
    if q:
        mask = all_books.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        all_books = all_books[mask]
    st.dataframe(all_books, use_container_width=True, hide_index=True)
    st.download_button("Download book catalogue (CSV)", all_books.to_csv(index=False).encode("utf-8"),
                       "books.csv", "text/csv")
    st.markdown("#### Edit or remove a book")
    if not all_books.empty:
        selected = st.selectbox("Select book", all_books["id"].tolist(),
                                format_func=lambda x: f'#{x} — {all_books.loc[all_books.id == x, "title"].iloc[0]}')
        book = get_book(int(selected))
        with st.form("edit_book"):
            c1,c2 = st.columns(2)
            e_title = c1.text_input("Title", value=book["title"])
            e_author = c2.text_input("Author", value=book["author"])
            e_category = c1.text_input("Category", value=book["category"] or "")
            e_publisher = c2.text_input("Publisher", value=book["publisher"] or "")
            e_year = c1.number_input("Year", min_value=0, max_value=2100, value=int(book["year"] or 0))
            e_total = c2.number_input("Total copies", min_value=0, max_value=10000, value=int(book["total_copies"]))
            save = st.form_submit_button("Save changes")
            if save:
                issued_count = int(book["total_copies"]) - int(book["available_copies"])
                if e_total < issued_count:
                    st.error(f"Total copies cannot be less than {issued_count} currently issued copies.")
                elif not e_title.strip() or not e_author.strip():
                    st.error("Title and author are required.")
                else:
                    execute("""UPDATE books SET title=?,author=?,category=?,publisher=?,year=?,total_copies=?,available_copies=?
                               WHERE id=?""",
                            (e_title.strip(),e_author.strip(),e_category.strip(),e_publisher.strip(),int(e_year),
                             int(e_total),int(e_total)-issued_count,int(selected)))
                    st.success("Book updated.")
                    st.rerun()
        if st.button("Delete selected book", type="secondary"):
            with get_db() as conn:
                count = conn.execute("SELECT COUNT(*) FROM loans WHERE book_id=?", (int(selected),)).fetchone()[0]
                if count:
                    st.error("Cannot delete a book with loan history. Keep it for audit/reporting.")
                else:
                    conn.execute("DELETE FROM books WHERE id=?", (int(selected),))
                    conn.commit()
                    st.success("Book deleted.")
                    st.rerun()

elif page == "Members":
    st.subheader("Library members")
    with st.expander("➕ Register member"):
        with st.form("add_member", clear_on_submit=True):
            name = st.text_input("Full name *")
            email = st.text_input("Email (optional)")
            phone = st.text_input("Phone")
            address = st.text_area("Address")
            submitted = st.form_submit_button("Register member", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Member name is required.")
                else:
                    try:
                        execute("INSERT INTO members(name,email,phone,address) VALUES(?,?,?,?)",
                                (name.strip(),email.strip() or None,phone.strip(),address.strip()))
                        st.success("Member registered.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That email is already registered.")
    members = query_df("SELECT * FROM members ORDER BY name")
    q = st.text_input("Search members by name, email, or phone")
    if q and not members.empty:
        mask = members.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        members = members[mask]
    st.dataframe(members, use_container_width=True, hide_index=True)
    st.download_button("Download members (CSV)", members.to_csv(index=False).encode("utf-8"),
                       "members.csv", "text/csv")
    if not members.empty:
        st.markdown("#### Update member")
        selected = st.selectbox("Select member ID", members["id"].tolist(),
                                format_func=lambda x: f'#{x} — {members.loc[members.id == x, "name"].iloc[0]}')
        member = get_member(int(selected))
        with st.form("edit_member"):
            n = st.text_input("Name", value=member["name"])
            em = st.text_input("Email", value=member["email"] or "")
            ph = st.text_input("Phone", value=member["phone"] or "")
            ad = st.text_area("Address", value=member["address"] or "")
            active = st.checkbox("Active member", value=bool(member["active"]))
            save = st.form_submit_button("Save member")
            if save:
                try:
                    execute("UPDATE members SET name=?,email=?,phone=?,address=?,active=? WHERE id=?",
                            (n.strip(),em.strip() or None,ph.strip(),ad.strip(),int(active),int(selected)))
                    st.success("Member updated.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That email is already used by another member.")

elif page == "Issue / Return":
    st.subheader("Issue a book")
    books = query_df("SELECT id,title,author,available_copies FROM books WHERE available_copies > 0 ORDER BY title")
    members = query_df("SELECT id,name,email FROM members WHERE active=1 ORDER BY name")
    if books.empty:
        st.info("No copies are currently available to issue.")
    elif members.empty:
        st.info("Register an active member before issuing books.")
    else:
        with st.form("issue_form"):
            book_id = st.selectbox("Book", books["id"].tolist(),
                                   format_func=lambda x: f'{books.loc[books.id == x, "title"].iloc[0]} '
                                                        f'— available: {int(books.loc[books.id == x, "available_copies"].iloc[0])}')
            member_id = st.selectbox("Member", members["id"].tolist(),
                                     format_func=lambda x: f'{members.loc[members.id == x, "name"].iloc[0]}'
                                                          f' ({members.loc[members.id == x, "email"].iloc[0] or "no email"})')
            issue_date = st.date_input("Issue date", value=date.today())
            loan_days = st.number_input("Loan period (days)", min_value=1, max_value=365, value=14)
            submit = st.form_submit_button("Issue book", type="primary")
            if submit:
                with get_db() as conn:
                    current = conn.execute("SELECT available_copies FROM books WHERE id=?", (int(book_id),)).fetchone()
                    if not current or current["available_copies"] < 1:
                        st.error("No copies available.")
                    else:
                        conn.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (int(book_id),))
                        conn.execute("""INSERT INTO loans(book_id,member_id,issued_on,due_on,status)
                                        VALUES(?,?,?,?, 'Issued')""",
                                     (int(book_id),int(member_id),issue_date.isoformat(),
                                      (issue_date + timedelta(days=int(loan_days))).isoformat()))
                        conn.commit()
                        st.success("Book issued successfully.")
                        st.rerun()
    st.divider()
    st.subheader("Active loans")
    active = query_df("""SELECT l.id AS loan_id,b.title,m.name,m.email,l.issued_on,l.due_on,
                         CASE WHEN l.due_on < date('now') THEN 'Overdue' ELSE 'Issued' END AS current_status
                         FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
                         WHERE l.status='Issued' ORDER BY l.due_on""")
    st.dataframe(active, use_container_width=True, hide_index=True)
    if not active.empty:
        loan_id = st.selectbox("Select loan to return", active["loan_id"].tolist(),
                               format_func=lambda x: f'Loan #{x} — {active.loc[active.loan_id == x, "title"].iloc[0]} / '
                                                    f'{active.loc[active.loan_id == x, "name"].iloc[0]}')
        return_date = st.date_input("Return date", value=date.today(), key="return_date")
        fine_per_day = st.number_input("Fine per overdue day (₹)", min_value=0.0, max_value=1000.0, value=2.0, step=1.0)
        if st.button("Record return", type="primary"):
            with get_db() as conn:
                loan = conn.execute("SELECT * FROM loans WHERE id=? AND status='Issued'", (int(loan_id),)).fetchone()
                if loan:
                    late_days = max(0, (return_date - fmt_date(loan["due_on"])).days)
                    fine = late_days * float(fine_per_day)
                    conn.execute("UPDATE loans SET returned_on=?,fine=?,status='Returned' WHERE id=?",
                                 (return_date.isoformat(),fine,int(loan_id)))
                    conn.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=?", (loan["book_id"],))
                    conn.commit()
                    st.success(f"Return recorded. Fine: ₹{fine:.2f} ({late_days} overdue day(s)).")
                    st.rerun()

elif page == "Reports":
    st.subheader("Reports and history")
    loans = query_df("""SELECT l.id AS loan_id,b.title,b.author,m.name AS member,m.email,
                        l.issued_on,l.due_on,l.returned_on,l.fine,l.status
                        FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
                        ORDER BY l.id DESC""")
    c1,c2,c3 = st.columns(3)
    c1.metric("Total loan transactions", len(loans))
    c2.metric("Total fines recorded", f"₹{loans['fine'].sum():.2f}" if not loans.empty else "₹0.00")
    c3.metric("Returned loans", int((loans["status"] == "Returned").sum()) if not loans.empty else 0)
    if not loans.empty:
        status = st.selectbox("Filter status", ["All", "Issued", "Returned"])
        view = loans if status == "All" else loans[loans["status"] == status]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("Download loan report (CSV)", view.to_csv(index=False).encode("utf-8"),
                           "loan_report.csv", "text/csv")
        st.subheader("Most borrowed books")
        top = loans.groupby("title").size().sort_values(ascending=False).head(10).rename("loans").reset_index()
        st.bar_chart(top.set_index("title"))
    else:
        st.info("No loan transactions yet.")

elif page == "Settings":
    st.subheader("Settings and database")
    st.info("This app stores data in a local SQLite file named library.db beside app.py.")
    st.write("**Default loan period:** Set individually for each issue transaction.")
    st.write("**Default overdue fine:** ₹2/day, adjustable when recording a return.")
    st.warning("Back up the database file before moving or reinstalling the application.")
    if st.button("Create database backup"):
        backup_path = APP_DIR / f"library_backup_{date.today().isoformat()}.db"
        with get_db() as source, sqlite3.connect(backup_path) as dest:
            source.backup(dest)
        st.success(f"Backup created: {backup_path.name}")
        st.download_button("Download backup", backup_path.read_bytes(), backup_path.name, "application/octet-stream")
    st.markdown("### Included features")
    st.markdown("""
    - Book catalogue: add, search, edit, delete when there is no loan history
    - Member registration and profile updates
    - Issue and return workflow with stock tracking
    - Due dates, overdue detection, and configurable late fines
    - Loan history, summary metrics, CSV exports, and database backup
    """)

import streamlit as st
import sqlite3
import hashlib
import secrets
import hmac

st.set_page_config(
    page_title="BlogSpace",
    page_icon="✍️",
    layout="wide"
)

# ---------- DATABASE ----------
conn = sqlite3.connect("blogspace.db", check_same_thread=False)
conn.row_factory = sqlite3.Row

conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS blogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()


def register(name, email, password):
    salt = secrets.token_hex(16)
    hashed = password_hash(password, salt)

    try:
        conn.execute(
            "INSERT INTO users (name,email,salt,password_hash) "
            "VALUES (?,?,?,?)",
            (name, email.lower(), salt, hashed)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def login(email, password):
    user = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email.lower(),)
    ).fetchone()

    if user:
        entered_hash = password_hash(password, user["salt"])
        if hmac.compare_digest(
            entered_hash, user["password_hash"]
        ):
            return dict(user)

    return None


# ---------- SESSION ----------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------- DESIGN ----------
st.markdown("""
<style>
.stApp {
    background-color: #f5f7fb;
}
h1 {
    color: #283c63;
}
div.stButton > button {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("✍️ BlogSpace")
st.caption("Write your stories. Share your ideas.")

# ---------- LOGIN AND REGISTRATION ----------
if st.session_state.user is None:

    login_tab, register_tab = st.tabs(
        ["Login", "Create Account"]
    )

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input(
                "Password", type="password"
            )
            submitted = st.form_submit_button("Login")

        if submitted:
            user = login(email, password)

            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            password = st.text_input(
                "Create Password", type="password"
            )
            confirm = st.text_input(
                "Confirm Password", type="password"
            )
            submitted = st.form_submit_button(
                "Register"
            )

        if submitted:
            if not name.strip() or not email.strip():
                st.error("Please fill in all fields.")
            elif "@" not in email:
                st.error("Enter a valid email address.")
            elif len(password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif register(name.strip(), email.strip(), password):
                st.success("Account created! Please log in.")
            else:
                st.error("This email is already registered.")

    st.stop()

# ---------- USER DASHBOARD ----------
user = st.session_state.user

with st.sidebar:
    st.title("📚 BlogSpace")
    st.write(f"Welcome, {user['name']}!")

    page = st.radio(
        "Navigation",
        ["Dashboard", "Write Blog", "My Blogs", "Profile"]
    )

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()


def get_blogs(search=""):
    return conn.execute("""
        SELECT * FROM blogs
        WHERE user_id = ?
        AND (title LIKE ? OR content LIKE ?)
        ORDER BY created_at DESC
    """, (
        user["id"],
        f"%{search}%",
        f"%{search}%"
    )).fetchall()


if page == "Dashboard":
    st.header("📊 My Dashboard")

    blogs = get_blogs()

    col1, col2 = st.columns(2)
    col1.metric("Total Blogs", len(blogs))
    col2.metric(
        "Categories",
        len(set(blog["category"] for blog in blogs))
    )

    st.subheader("Recent Blogs")

    for blog in blogs[:5]:
        with st.container(border=True):
            st.subheader(blog["title"])
            st.caption(
                f"{blog['category']} | {blog['created_at']}"
            )
            st.write(blog["content"])


elif page == "Write Blog":
    st.header("📝 Create a Blog")

    with st.form("blog_form"):
        title = st.text_input("Blog Title")

        category = st.selectbox(
            "Category",
            [
                "Technology",
                "Education",
                "Lifestyle",
                "Travel",
                "Personal",
                "Other"
            ]
        )

        content = st.text_area(
            "Blog Content",
            height=200
        )

        submitted = st.form_submit_button("Publish Blog")

    if submitted:
        if title.strip() and content.strip():
            conn.execute("""
                INSERT INTO blogs
                (user_id, title, category, content)
                VALUES (?, ?, ?, ?)
            """, (
                user["id"],
                title.strip(),
                category,
                content.strip()
            ))
            conn.commit()
            st.success("Blog published successfully!")
        else:
            st.error("Enter both title and content.")


elif page == "My Blogs":
    st.header("📚 Manage My Blogs")

    search = st.text_input("Search blogs")
    blogs = get_blogs(search)

    for blog in blogs:
        with st.expander(blog["title"]):
            st.caption(blog["category"])
            st.write(blog["content"])

            with st.form(f"edit_{blog['id']}"):
                new_title = st.text_input(
                    "Title",
                    value=blog["title"]
                )
                new_category = st.selectbox(
                    "Category",
                    [
                        "Technology",
                        "Education",
                        "Lifestyle",
                        "Travel",
                        "Personal",
                        "Other"
                    ],
                    index=[
                        "Technology",
                        "Education",
                        "Lifestyle",
                        "Travel",
                        "Personal",
                        "Other"
                    ].index(blog["category"])
                )
                new_content = st.text_area(
                    "Content",
                    value=blog["content"]
                )

                update = st.form_submit_button("Update Blog")

            if update:
                conn.execute("""
                    UPDATE blogs
                    SET title=?, category=?, content=?
                    WHERE id=? AND user_id=?
                """, (
                    new_title.strip(),
                    new_category,
                    new_content.strip(),
                    blog["id"],
                    user["id"]
                ))
                conn.commit()
                st.success("Blog updated!")
                st.rerun()

            if st.button(
                "Delete Blog",
                key=f"delete_{blog['id']}"
            ):
                conn.execute("""
                    DELETE FROM blogs
                    WHERE id=? AND user_id=?
                """, (blog["id"], user["id"]))
                conn.commit()
                st.success("Blog deleted!")
                st.rerun()


elif page == "Profile":
    st.header("👤 My Profile")
    st.write("Name:", user["name"])
    st.write("Email:", user["email"])

st.divider()
st.caption("BlogSpace | Python • Streamlit • SQLite")
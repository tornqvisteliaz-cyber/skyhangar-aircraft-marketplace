#!/usr/bin/env python3
"""
SkyHangar - Aircraft Marketplace
A complete local web application for browsing & buying aircraft,
watching trailers, newsletters, and full admin control panel.

Run:  python3 app.py
Then open http://localhost:8000
"""

import os
import sqlite3
import hashlib
import secrets
import json
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "skyhangar.db")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
HOST = "127.0.0.1"
PORT = 8000
SECRET_KEY = "skyhangar-local-dev-secret-change-me"

# Simple in-memory session store: session_id -> {"user_id": int, "username": str, "is_admin": bool}
sessions = {}

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS aircrafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        model TEXT,
        description TEXT,
        price REAL NOT NULL,
        year INTEGER,
        seats INTEGER,
        range_km INTEGER,
        image_url TEXT,
        trailer_url TEXT,
        stock INTEGER NOT NULL DEFAULT 1,
        featured INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT,
        aircraft_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        total_price REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (aircraft_id) REFERENCES aircrafts(id)
    );

    CREATE TABLE IF NOT EXISTS newsletters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        published INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Seed admin user if none exists
    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    if cur.fetchone()[0] == 0:
        pw_hash = hash_password("admin123")
        cur.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, 1, ?)",
            ("admin", pw_hash, datetime.utcnow().isoformat())
        )

    # Seed sample aircrafts if empty
    cur.execute("SELECT COUNT(*) FROM aircrafts")
    if cur.fetchone()[0] == 0:
        sample_aircrafts = [
            (
                "Cessna 172 Skyhawk",
                "172S",
                "The world's most popular training aircraft. Reliable, easy to fly, and perfect for new pilots. Excellent visibility and forgiving flight characteristics.",
                389000.00, 2023, 4, 1185,
                "https://placehold.co/800x500/1e3a5f/ffffff?text=Cessna+172",
                "https://www.youtube.com/embed/9qQ2kQ1nQ1E",
                3, 1
            ),
            (
                "Piper PA-28 Cherokee",
                "PA-28-181",
                "A classic four-seat single-engine aircraft known for its solid handling and roomy cabin. Ideal for personal travel and flight training.",
                295000.00, 2021, 4, 950,
                "https://placehold.co/800x500/1e3a5f/ffffff?text=Piper+Cherokee",
                "https://www.youtube.com/embed/dQw4w9WgXcQ",
                2, 1
            ),
            (
                "Cirrus SR22 G6",
                "SR22-G6",
                "High-performance personal aircraft featuring the Cirrus Airframe Parachute System (CAPS). Glass cockpit, powerful engine, and exceptional safety record.",
                899000.00, 2024, 4, 1945,
                "https://placehold.co/800x500/0b3d5c/ffffff?text=Cirrus+SR22",
                "https://www.youtube.com/embed/9bZkp7q19f0",
                1, 1
            ),
            (
                "Beechcraft Bonanza G36",
                "G36",
                "Iconic high-performance single with retractable gear. Luxurious interior, advanced avionics, and legendary Beechcraft build quality.",
                825000.00, 2022, 6, 1700,
                "https://placehold.co/800x500/1a5f8a/ffffff?text=Beechcraft+Bonanza",
                "https://www.youtube.com/embed/jNQXAC9IVRw",
                1, 0
            ),
            (
                "Diamond DA40 NG",
                "DA40-NG",
                "Modern composite four-seater with diesel engine efficiency. Quiet, economical, and equipped with Garmin G1000 NXi glass cockpit.",
                520000.00, 2023, 4, 1500,
                "https://placehold.co/800x500/0b3d5c/ffffff?text=Diamond+DA40",
                "https://www.youtube.com/embed/kJQP7kiw5Fk",
                2, 0
            ),
            (
                "Cessna Citation M2",
                "Citation M2",
                "Entry-level business jet. Fast, efficient, and certified for single-pilot operation. Perfect step-up into jet aviation.",
                5800000.00, 2023, 7, 2870,
                "https://placehold.co/800x500/1e3a5f/ffffff?text=Citation+M2",
                "https://www.youtube.com/embed/L_jWHffIx5E",
                1, 1
            ),
        ]
        now = datetime.utcnow().isoformat()
        for a in sample_aircrafts:
            cur.execute("""
                INSERT INTO aircrafts
                (name, model, description, price, year, seats, range_km, image_url, trailer_url, stock, featured, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*a, now))

    # Seed one newsletter
    cur.execute("SELECT COUNT(*) FROM newsletters")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO newsletters (title, content, published, created_at)
            VALUES (?, ?, 1, ?)
        """, (
            "Welcome to SkyHangar!",
            "Thank you for joining the SkyHangar community. We bring you the finest selection of new and pre-owned aircraft from trusted manufacturers. Stay tuned for exclusive offers, flight tips, and new arrivals every month.",
            datetime.utcnow().isoformat()
        ))

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    salt = SECRET_KEY.encode()
    return hashlib.sha256(salt + password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

# ---------------------------------------------------------------------------
# Jinja environment
# ---------------------------------------------------------------------------
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

def render(template_name, **context):
    template = jinja_env.get_template(template_name)
    return template.render(**context)

# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class SkyHangarHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet logging
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def get_session(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("session_id="):
                sid = part[len("session_id="):]
                return sessions.get(sid), sid
        return None, None

    def set_session_cookie(self, session_id):
        self.send_header("Set-Cookie", f"session_id={session_id}; Path=/; HttpOnly; SameSite=Lax")

    def clear_session_cookie(self):
        self.send_header("Set-Cookie", "session_id=; Path=/; Max-Age=0")

    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def send_static(self, path):
        full = os.path.join(STATIC_DIR, path)
        if not os.path.isfile(full):
            self.send_error(404)
            return
        ext = os.path.splitext(full)[1].lower()
        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        ctype = content_types.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def parse_form(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        return urllib.parse.parse_qs(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        session, sid = self.get_session()
        user = session

        # Static files
        if path.startswith("/static/"):
            self.send_static(path[len("/static/"):])
            return

        try:
            if path == "/" or path == "/index":
                self.page_home(user, query)
            elif path == "/aircrafts":
                self.page_aircrafts(user, query)
            elif path.startswith("/aircraft/"):
                aircraft_id = path.split("/")[-1]
                self.page_aircraft_detail(user, aircraft_id)
            elif path == "/newsletter":
                self.page_newsletter(user)
            elif path == "/login":
                self.page_login(user)
            elif path == "/logout":
                if sid and sid in sessions:
                    del sessions[sid]
                self.clear_session_cookie()
                self.send_redirect("/")
            elif path == "/admin":
                self.page_admin_dashboard(user)
            elif path == "/admin/aircrafts":
                self.page_admin_aircrafts(user)
            elif path == "/admin/orders":
                self.page_admin_orders(user)
            elif path == "/admin/newsletters":
                self.page_admin_newsletters(user)
            elif path == "/admin/subscribers":
                self.page_admin_subscribers(user)
            elif path == "/admin/aircraft/new":
                self.page_admin_aircraft_form(user, None)
            elif path.startswith("/admin/aircraft/edit/"):
                aid = path.split("/")[-1]
                self.page_admin_aircraft_form(user, aid)
            elif path.startswith("/admin/aircraft/delete/"):
                aid = path.split("/")[-1]
                self.admin_delete_aircraft(user, aid)
            else:
                self.send_error(404, "Page not found")
        except Exception as e:
            print("Error:", e)
            self.send_error(500, str(e))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        session, sid = self.get_session()
        user = session
        form = self.parse_form()

        try:
            if path == "/subscribe":
                self.handle_subscribe(form)
            elif path == "/order":
                self.handle_order(form)
            elif path == "/login":
                self.handle_login(form)
            elif path == "/admin/aircraft/save":
                self.handle_admin_aircraft_save(user, form)
            elif path == "/admin/newsletter/save":
                self.handle_admin_newsletter_save(user, form)
            elif path == "/admin/order/status":
                self.handle_admin_order_status(user, form)
            else:
                self.send_error(404)
        except Exception as e:
            print("POST Error:", e)
            self.send_error(500, str(e))

    # -----------------------------------------------------------------------
    # Public pages
    # -----------------------------------------------------------------------
    def page_home(self, user, query=None):
        query = query or {}
        conn = get_db()
        featured = conn.execute(
            "SELECT * FROM aircrafts WHERE featured = 1 AND stock > 0 ORDER BY created_at DESC LIMIT 6"
        ).fetchall()
        latest_nl = conn.execute(
            "SELECT * FROM newsletters WHERE published = 1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        html = render(
            "index.html",
            user=user,
            featured=featured,
            latest_nl=latest_nl,
            subscribed=query.get("subscribed", [None])[0] == "1"
        )
        self.send_html(html)

    def page_aircrafts(self, user, query):
        conn = get_db()
        search = query.get("q", [""])[0].strip()
        if search:
            rows = conn.execute(
                "SELECT * FROM aircrafts WHERE stock > 0 AND (name LIKE ? OR model LIKE ? OR description LIKE ?) ORDER BY name",
                (f"%{search}%", f"%{search}%", f"%{search}%")
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM aircrafts WHERE stock > 0 ORDER BY featured DESC, name"
            ).fetchall()
        conn.close()
        html = render("aircrafts.html", user=user, aircrafts=rows, search=search)
        self.send_html(html)

    def page_aircraft_detail(self, user, aircraft_id):
        conn = get_db()
        aircraft = conn.execute("SELECT * FROM aircrafts WHERE id = ?", (aircraft_id,)).fetchone()
        conn.close()
        if not aircraft:
            self.send_error(404, "Aircraft not found")
            return
        html = render("aircraft_detail.html", user=user, aircraft=aircraft)
        self.send_html(html)

    def page_newsletter(self, user):
        conn = get_db()
        newsletters = conn.execute(
            "SELECT * FROM newsletters WHERE published = 1 ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        html = render("newsletter.html", user=user, newsletters=newsletters)
        self.send_html(html)

    def page_login(self, user):
        if user and user.get("is_admin"):
            self.send_redirect("/admin")
            return
        html = render("login.html", user=user, error=None)
        self.send_html(html)

    # -----------------------------------------------------------------------
    # Admin pages (require is_admin)
    # -----------------------------------------------------------------------
    def require_admin(self, user):
        if not user or not user.get("is_admin"):
            self.send_redirect("/login")
            return False
        return True

    def page_admin_dashboard(self, user):
        if not self.require_admin(user):
            return
        conn = get_db()
        stats = {
            "aircrafts": conn.execute("SELECT COUNT(*) FROM aircrafts").fetchone()[0],
            "orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "pending_orders": conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'").fetchone()[0],
            "subscribers": conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0],
            "newsletters": conn.execute("SELECT COUNT(*) FROM newsletters").fetchone()[0],
        }
        recent_orders = conn.execute(
            "SELECT o.*, a.name as aircraft_name FROM orders o JOIN aircrafts a ON o.aircraft_id = a.id ORDER BY o.created_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        html = render("admin_dashboard.html", user=user, stats=stats, recent_orders=recent_orders)
        self.send_html(html)

    def page_admin_aircrafts(self, user):
        if not self.require_admin(user):
            return
        conn = get_db()
        rows = conn.execute("SELECT * FROM aircrafts ORDER BY created_at DESC").fetchall()
        conn.close()
        html = render("admin_aircrafts.html", user=user, aircrafts=rows)
        self.send_html(html)

    def page_admin_aircraft_form(self, user, aircraft_id):
        if not self.require_admin(user):
            return
        aircraft = None
        if aircraft_id:
            conn = get_db()
            aircraft = conn.execute("SELECT * FROM aircrafts WHERE id = ?", (aircraft_id,)).fetchone()
            conn.close()
            if not aircraft:
                self.send_error(404)
                return
        html = render("admin_aircraft_form.html", user=user, aircraft=aircraft)
        self.send_html(html)

    def page_admin_orders(self, user):
        if not self.require_admin(user):
            return
        conn = get_db()
        orders = conn.execute(
            "SELECT o.*, a.name as aircraft_name FROM orders o JOIN aircrafts a ON o.aircraft_id = a.id ORDER BY o.created_at DESC"
        ).fetchall()
        conn.close()
        html = render("admin_orders.html", user=user, orders=orders)
        self.send_html(html)

    def page_admin_newsletters(self, user):
        if not self.require_admin(user):
            return
        conn = get_db()
        newsletters = conn.execute("SELECT * FROM newsletters ORDER BY created_at DESC").fetchall()
        conn.close()
        html = render("admin_newsletters.html", user=user, newsletters=newsletters)
        self.send_html(html)

    def page_admin_subscribers(self, user):
        if not self.require_admin(user):
            return
        conn = get_db()
        subscribers = conn.execute("SELECT * FROM subscribers ORDER BY created_at DESC").fetchall()
        conn.close()
        html = render("admin_subscribers.html", user=user, subscribers=subscribers)
        self.send_html(html)

    def admin_delete_aircraft(self, user, aircraft_id):
        if not self.require_admin(user):
            return
        conn = get_db()
        conn.execute("DELETE FROM aircrafts WHERE id = ?", (aircraft_id,))
        conn.commit()
        conn.close()
        self.send_redirect("/admin/aircrafts")

    # -----------------------------------------------------------------------
    # Form handlers
    # -----------------------------------------------------------------------
    def handle_subscribe(self, form):
        email = form.get("email", [""])[0].strip().lower()
        if not email or "@" not in email:
            self.send_redirect("/?error=invalid_email")
            return
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO subscribers (email, created_at) VALUES (?, ?)",
                (email, datetime.utcnow().isoformat())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # already subscribed
        conn.close()
        self.send_redirect("/?subscribed=1")

    def handle_order(self, form):
        name = form.get("name", [""])[0].strip()
        email = form.get("email", [""])[0].strip()
        phone = form.get("phone", [""])[0].strip()
        aircraft_id = form.get("aircraft_id", [""])[0]
        notes = form.get("notes", [""])[0].strip()

        if not name or not email or not aircraft_id:
            self.send_redirect(f"/aircraft/{aircraft_id}?error=missing")
            return

        conn = get_db()
        aircraft = conn.execute("SELECT * FROM aircrafts WHERE id = ? AND stock > 0", (aircraft_id,)).fetchone()
        if not aircraft:
            conn.close()
            self.send_redirect("/aircrafts?error=unavailable")
            return

        total = aircraft["price"]
        conn.execute("""
            INSERT INTO orders (customer_name, customer_email, customer_phone, aircraft_id, quantity, total_price, status, notes, created_at)
            VALUES (?, ?, ?, ?, 1, ?, 'pending', ?, ?)
        """, (name, email, phone, aircraft_id, total, notes, datetime.utcnow().isoformat()))
        # Reduce stock
        conn.execute("UPDATE aircrafts SET stock = stock - 1 WHERE id = ?", (aircraft_id,))
        conn.commit()
        conn.close()
        self.send_redirect(f"/aircraft/{aircraft_id}?ordered=1")

    def handle_login(self, form):
        username = form.get("username", [""])[0].strip()
        password = form.get("password", [""])[0]
        conn = get_db()
        user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user_row and verify_password(password, user_row["password_hash"]):
            sid = secrets.token_hex(16)
            sessions[sid] = {
                "user_id": user_row["id"],
                "username": user_row["username"],
                "is_admin": bool(user_row["is_admin"])
            }
            self.send_response(302)
            self.set_session_cookie(sid)
            self.send_header("Location", "/admin")
            self.end_headers()
        else:
            html = render("login.html", user=None, error="Invalid username or password")
            self.send_html(html)

    def handle_admin_aircraft_save(self, user, form):
        if not self.require_admin(user):
            return
        aircraft_id = form.get("id", [""])[0]
        name = form.get("name", [""])[0].strip()
        model = form.get("model", [""])[0].strip()
        description = form.get("description", [""])[0].strip()
        price = float(form.get("price", ["0"])[0] or 0)
        year = int(form.get("year", ["0"])[0] or 0)
        seats = int(form.get("seats", ["0"])[0] or 0)
        range_km = int(form.get("range_km", ["0"])[0] or 0)
        image_url = form.get("image_url", [""])[0].strip()
        trailer_url = form.get("trailer_url", [""])[0].strip()
        stock = int(form.get("stock", ["1"])[0] or 1)
        featured = 1 if form.get("featured") else 0

        conn = get_db()
        if aircraft_id:
            conn.execute("""
                UPDATE aircrafts SET name=?, model=?, description=?, price=?, year=?, seats=?, range_km=?,
                image_url=?, trailer_url=?, stock=?, featured=? WHERE id=?
            """, (name, model, description, price, year, seats, range_km, image_url, trailer_url, stock, featured, aircraft_id))
        else:
            conn.execute("""
                INSERT INTO aircrafts (name, model, description, price, year, seats, range_km, image_url, trailer_url, stock, featured, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, model, description, price, year, seats, range_km, image_url, trailer_url, stock, featured, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        self.send_redirect("/admin/aircrafts")

    def handle_admin_newsletter_save(self, user, form):
        if not self.require_admin(user):
            return
        title = form.get("title", [""])[0].strip()
        content = form.get("content", [""])[0].strip()
        if not title or not content:
            self.send_redirect("/admin/newsletters?error=missing")
            return
        conn = get_db()
        conn.execute(
            "INSERT INTO newsletters (title, content, published, created_at) VALUES (?, ?, 1, ?)",
            (title, content, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        self.send_redirect("/admin/newsletters")

    def handle_admin_order_status(self, user, form):
        if not self.require_admin(user):
            return
        order_id = form.get("order_id", [""])[0]
        status = form.get("status", [""])[0]
        if order_id and status in ("pending", "confirmed", "completed", "cancelled"):
            conn = get_db()
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            conn.commit()
            conn.close()
        self.send_redirect("/admin/orders")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    init_db()
    print("=" * 60)
    print("  SkyHangar Aircraft Marketplace")
    print("=" * 60)
    print(f"  Local server running at: http://{HOST}:{PORT}")
    print("  Admin login:  username = admin")
    print("                password = admin123")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    server = HTTPServer((HOST, PORT), SkyHangarHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()

if __name__ == "__main__":
    main()

# SkyHangar – Aircraft Marketplace

A complete **local** full-stack web application for browsing and ordering aircraft, watching trailers, managing newsletters, and full admin control.

Built with **pure Python 3** (standard library + Jinja2) + **SQLite**. No external frameworks required beyond what's already available.

## Features

### Public site
- Home page with featured aircraft
- Browse / search all available aircraft
- Aircraft detail pages with specs, description, and embedded video trailers
- Place order inquiries (name, email, phone, notes)
- Newsletter archive + email subscription

### Admin panel (login required)
- Dashboard with live statistics
- Full CRUD for aircraft (add, edit, delete, mark featured, manage stock)
- View and update order status (pending → confirmed → completed / cancelled)
- Post new newsletters
- View all newsletter subscribers

## Quick Start (Local)

```bash
# 1. Clone the repository
git clone https://github.com/tornqvisteliaz-cyber/skyhangar-aircraft-marketplace.git
cd skyhangar-aircraft-marketplace

# 2. Make sure you have Python 3.8+ and Jinja2
#    (Jinja2 is usually available; if not: pip install jinja2)

# 3. Run the server
python3 app.py
```

Then open your browser at:

**http://127.0.0.1:8000**

### Admin Login
- **Username:** `admin`
- **Password:** `admin123`

(Change these in production by editing the seeded user or the database.)

## Project Structure

```
skyhangar-aircraft-marketplace/
├── app.py                 # Main application (server + routes + DB logic)
├── data/
│   └── skyhangar.db       # SQLite database (created automatically)
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── aircrafts.html
│   ├── aircraft_detail.html
│   ├── newsletter.html
│   ├── login.html
│   └── admin_*.html
├── static/
│   ├── style.css
│   └── script.js
└── README.md
```

## Tech Notes

- **Backend:** Python `http.server` + custom request handler
- **Templating:** Jinja2
- **Database:** SQLite (file-based, zero config)
- **Auth:** Simple session cookies + SHA-256 password hashing
- **No external services** – everything runs fully offline after the first run

## Sample Data

On first launch the app automatically creates:
- One admin user
- Six sample aircraft (Cessna, Piper, Cirrus, Beechcraft, Diamond, Citation)
- One welcome newsletter

You can delete or edit any of them from the admin panel.

## License

This is a demonstration / educational project. Feel free to use and modify.

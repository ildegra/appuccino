import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer, BadSignature

APP_NAME = "Appuccino"
DB_PATH = os.getenv("DB_PATH", "/data/appuccino.sqlite3")
USERNAME = os.getenv("APP_USERNAME", "admin")
PASSWORD = os.getenv("APP_PASSWORD", "appuccino")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
signer = URLSafeSerializer(SECRET_KEY, salt="appuccino-login")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT DEFAULT '',
                city TEXT DEFAULT '',
                latitude REAL,
                longitude REAL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '⭐',
                weight REAL NOT NULL DEFAULT 10,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bar_id INTEGER NOT NULL REFERENCES bars(id) ON DELETE CASCADE,
                visited_at TEXT NOT NULL,
                drink TEXT DEFAULT '',
                food TEXT DEFAULT '',
                total_price REAL,
                wait_minutes INTEGER,
                crowd TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                criterion_id INTEGER REFERENCES criteria(id),
                score REAL NOT NULL,
                UNIQUE(visit_id, category_id, criterion_id)
            );
            """
        )
        existing = c.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
        if existing == 0:
            defaults = [
                ("Caffè", "☕", 30, 1, ["Gusto", "Temperatura", "Crema", "Presentazione"]),
                ("Brioche", "🥐", 25, 2, ["Freschezza", "Impasto", "Farcitura", "Varietà"]),
                ("Prezzo", "💶", 15, 3, ["Rapporto qualità/prezzo"]),
                ("Servizio", "😊", 15, 4, ["Gentilezza", "Rapidità", "Precisione"]),
                ("Ambiente", "🪑", 10, 5, ["Comfort", "Rumore", "Atmosfera"]),
                ("Pulizia", "🧼", 5, 6, ["Bancone", "Tavoli", "Bagno"]),
            ]
            for name, icon, weight, order, crits in defaults:
                cur = c.execute(
                    "INSERT INTO categories(name, icon, weight, sort_order, active) VALUES (?, ?, ?, ?, 1)",
                    (name, icon, weight, order),
                )
                cid = cur.lastrowid
                for i, crit in enumerate(crits, start=1):
                    c.execute(
                        "INSERT INTO criteria(category_id, name, sort_order, active) VALUES (?, ?, ?, 1)",
                        (cid, crit, i),
                    )


def is_logged(request: Request) -> bool:
    token = request.cookies.get("appuccino_session")
    if not token:
        return False
    try:
        data = signer.loads(token)
        return data.get("u") == USERNAME
    except BadSignature:
        return False


def require_login(request: Request):
    if not is_logged(request):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


def render(request: Request, template: str, context: dict):
    context.update({"request": request, "app_name": APP_NAME})
    return templates.TemplateResponse(template, context)


def categories_with_criteria(active_only=False):
    with db() as c:
        q = "SELECT * FROM categories" + (" WHERE active=1" if active_only else "") + " ORDER BY sort_order, id"
        cats = [dict(r) for r in c.execute(q).fetchall()]
        for cat in cats:
            cq = "SELECT * FROM criteria WHERE category_id=?" + (" AND active=1" if active_only else "") + " ORDER BY sort_order, id"
            cat["criteria"] = [dict(r) for r in c.execute(cq, (cat["id"],)).fetchall()]
        return cats


def visit_score(visit_id: int):
    with db() as c:
        cats = c.execute("SELECT * FROM categories WHERE active=1").fetchall()
        weighted = 0.0
        weights = 0.0
        category_scores = {}
        for cat in cats:
            rows = c.execute("SELECT score FROM ratings WHERE visit_id=? AND category_id=?", (visit_id, cat["id"])).fetchall()
            if not rows:
                continue
            avg = sum(r["score"] for r in rows) / len(rows)
            category_scores[cat["id"]] = avg
            weighted += avg * cat["weight"]
            weights += cat["weight"]
        return round(weighted / weights, 2) if weights else None, category_scores


def bar_summary(bar_id: int):
    with db() as c:
        visits = c.execute("SELECT id FROM visits WHERE bar_id=?", (bar_id,)).fetchall()
    scores = [visit_score(v["id"])[0] for v in visits]
    scores = [s for s in scores if s is not None]
    return round(sum(scores) / len(scores), 2) if scores else None


@app.on_event("startup")
def startup():
    init_db()



@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return render(request, "login.html", {"error": None})


@app.post("/login")
def login_post(username: str = Form(...), password: str = Form(...)):
    if username == USERNAME and password == PASSWORD:
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie("appuccino_session", signer.dumps({"u": username}), httponly=True, samesite="lax")
        return resp
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("appuccino_session")
    return resp


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    require_login(request)
    with db() as c:
        bars = [dict(r) for r in c.execute("SELECT * FROM bars ORDER BY name").fetchall()]
        visits_count = c.execute("SELECT COUNT(*) AS n FROM visits").fetchone()["n"]
        total_spent = c.execute("SELECT SUM(total_price) AS s FROM visits").fetchone()["s"] or 0
    for b in bars:
        b["score"] = bar_summary(b["id"])
    bars.sort(key=lambda x: (-(x["score"] or 0), x["name"].lower()))
    return render(request, "index.html", {"bars": bars, "visits_count": visits_count, "total_spent": total_spent})


@app.post("/bars")
def add_bar(request: Request, name: str = Form(...), address: str = Form(""), city: str = Form(""), notes: str = Form("")):
    require_login(request)
    with db() as c:
        c.execute("INSERT INTO bars(name,address,city,notes,created_at) VALUES(?,?,?,?,?)", (name, address, city, notes, datetime.now().isoformat()))
    return RedirectResponse("/", status_code=303)


@app.get("/bars/{bar_id}", response_class=HTMLResponse)
def bar_detail(request: Request, bar_id: int):
    require_login(request)
    with db() as c:
        bar = c.execute("SELECT * FROM bars WHERE id=?", (bar_id,)).fetchone()
        if not bar:
            raise HTTPException(404)
        visits = [dict(r) for r in c.execute("SELECT * FROM visits WHERE bar_id=? ORDER BY visited_at DESC, id DESC", (bar_id,)).fetchall()]
        category_avg = c.execute(
            """
            SELECT c.name, c.icon, AVG(r.score) AS avg_score
            FROM ratings r JOIN categories c ON c.id=r.category_id
            JOIN visits v ON v.id=r.visit_id
            WHERE v.bar_id=? AND c.active=1
            GROUP BY c.id ORDER BY c.sort_order
            """, (bar_id,)
        ).fetchall()
    for v in visits:
        v["score"], _ = visit_score(v["id"])
    return render(request, "bar_detail.html", {"bar": dict(bar), "visits": visits, "score": bar_summary(bar_id), "category_avg": category_avg})


@app.get("/bars/{bar_id}/visit", response_class=HTMLResponse)
def visit_form(request: Request, bar_id: int):
    require_login(request)
    with db() as c:
        bar = c.execute("SELECT * FROM bars WHERE id=?", (bar_id,)).fetchone()
    return render(request, "visit_form.html", {"bar": dict(bar), "cats": categories_with_criteria(True), "today": date.today().isoformat()})


@app.post("/bars/{bar_id}/visit")
def add_visit(request: Request, bar_id: int, visited_at: str = Form(...), drink: str = Form(""), food: str = Form(""), total_price: Optional[float] = Form(None), wait_minutes: Optional[int] = Form(None), crowd: str = Form(""), notes: str = Form("")):
    require_login(request)
    form = None
    with db() as c:
        cur = c.execute("INSERT INTO visits(bar_id,visited_at,drink,food,total_price,wait_minutes,crowd,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (bar_id, visited_at, drink, food, total_price, wait_minutes, crowd, notes, datetime.now().isoformat()))
        visit_id = cur.lastrowid
    return RedirectResponse(f"/visits/{visit_id}/ratings", status_code=303)


@app.get("/visits/{visit_id}/ratings", response_class=HTMLResponse)
def ratings_form(request: Request, visit_id: int):
    require_login(request)
    with db() as c:
        visit = c.execute("SELECT * FROM visits WHERE id=?", (visit_id,)).fetchone()
        bar = c.execute("SELECT * FROM bars WHERE id=?", (visit["bar_id"],)).fetchone()
    return render(request, "ratings_form.html", {"visit": dict(visit), "bar": dict(bar), "cats": categories_with_criteria(True)})


@app.post("/visits/{visit_id}/ratings")
def save_ratings(request: Request, visit_id: int):
    require_login(request)
    # FastAPI non espone form dinamici come parametro: leggiamo async in wrapper sync non è disponibile.
    raise HTTPException(405)


@app.post("/visits/{visit_id}/ratings/save")
async def save_ratings_async(request: Request, visit_id: int):
    require_login(request)
    form = await request.form()
    with db() as c:
        c.execute("DELETE FROM ratings WHERE visit_id=?", (visit_id,))
        for key, value in form.items():
            if not key.startswith("score_") or value in ("", None):
                continue
            _, cat_id, crit_id = key.split("_")
            c.execute("INSERT INTO ratings(visit_id,category_id,criterion_id,score) VALUES(?,?,?,?)", (visit_id, int(cat_id), int(crit_id), float(value)))
        bar_id = c.execute("SELECT bar_id FROM visits WHERE id=?", (visit_id,)).fetchone()["bar_id"]
    return RedirectResponse(f"/bars/{bar_id}", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    require_login(request)
    return render(request, "settings.html", {"cats": categories_with_criteria(False)})


@app.post("/settings/categories")
def add_category(request: Request, name: str = Form(...), icon: str = Form("⭐"), weight: float = Form(10), sort_order: int = Form(99)):
    require_login(request)
    with db() as c:
        c.execute("INSERT INTO categories(name,icon,weight,sort_order,active) VALUES(?,?,?,?,1)", (name, icon, weight, sort_order))
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/categories/{cat_id}")
def update_category(request: Request, cat_id: int, name: str = Form(...), icon: str = Form("⭐"), weight: float = Form(10), sort_order: int = Form(0), active: Optional[str] = Form(None)):
    require_login(request)
    with db() as c:
        c.execute("UPDATE categories SET name=?, icon=?, weight=?, sort_order=?, active=? WHERE id=?", (name, icon, weight, sort_order, 1 if active else 0, cat_id))
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/categories/{cat_id}/criteria")
def add_criterion(request: Request, cat_id: int, name: str = Form(...), sort_order: int = Form(99)):
    require_login(request)
    with db() as c:
        c.execute("INSERT INTO criteria(category_id,name,sort_order,active) VALUES(?,?,?,1)", (cat_id, name, sort_order))
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/criteria/{crit_id}")
def update_criterion(request: Request, crit_id: int, name: str = Form(...), sort_order: int = Form(0), active: Optional[str] = Form(None)):
    require_login(request)
    with db() as c:
        c.execute("UPDATE criteria SET name=?, sort_order=?, active=? WHERE id=?", (name, sort_order, 1 if active else 0, crit_id))
    return RedirectResponse("/settings", status_code=303)


@app.get("/export.csv")
def export_csv(request: Request):
    require_login(request)
    import csv, tempfile
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with db() as c, open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bar", "data", "bevanda", "cibo", "prezzo", "voto_globale", "note"])
        rows = c.execute("SELECT v.*, b.name AS bar_name FROM visits v JOIN bars b ON b.id=v.bar_id ORDER BY visited_at DESC").fetchall()
        for r in rows:
            writer.writerow([r["bar_name"], r["visited_at"], r["drink"], r["food"], r["total_price"], visit_score(r["id"])[0], r["notes"]])
    return FileResponse(path, media_type="text/csv", filename="appuccino-export.csv")

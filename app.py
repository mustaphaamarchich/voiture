"""Mon Voiture - application Streamlit pour conducteurs, techniciens et experts auto."""
import hashlib
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).parent
DB_PATH = BASE / "mycar.db"
ASSETS = BASE  # images locales optionnelles, placées à côté de app.py

# Vos images (placées à côté de app.py)
HERO_1 = "carte.png"      # application de carte dans la voiture
HERO_2 = "reglages.png"   # réglages de la voiture sur le téléphone
HERO_3 = "recharge.png"   # recharge d'une voiture électrique
FALLBACK = "https://loremflickr.com/900/500/car,driving?lock=21"

ROLES = ["Conducteur", "Technicien / Mécanicien", "Expert automobile"]
PRO_ROLES = ROLES[1:]
RAPPEL_TYPES = ["Visite technique", "Vidange", "Assurance", "Pneus", "Freins",
                "Batterie", "Révision", "Autre"]
CATEGORIES = ["Moteur", "Freins", "Pneus", "Batterie", "Climatisation",
              "Voiture électrique", "Suspension", "Carrosserie", "Documents", "Diagnostic"]

st.set_page_config(page_title="Mon Voiture", page_icon="🚗", layout="wide")


# ------------------------------------------------------------------ base de données
def run(sql, params=(), fetch=False, one=False):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.execute(sql, params)
    result = None
    if fetch:
        result = cur.fetchone() if one else cur.fetchall()
    con.commit()
    last = cur.lastrowid
    con.close()
    return result if fetch else last


def init_db():
    run("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, nom TEXT, email TEXT UNIQUE, salt TEXT, pwd TEXT,
        role TEXT, ville TEXT, specialite TEXT, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS cars(
        id INTEGER PRIMARY KEY, user_id INTEGER, marque TEXT, modele TEXT,
        annee INTEGER, immat TEXT, km INTEGER)""")
    run("""CREATE TABLE IF NOT EXISTS reminders(
        id INTEGER PRIMARY KEY, user_id INTEGER, car_id INTEGER, type TEXT,
        date TEXT, note TEXT, done INTEGER DEFAULT 0)""")
    run("""CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY, user_id INTEGER, car_id INTEGER, titre TEXT,
        description TEXT, categorie TEXT, budget REAL, statut TEXT DEFAULT 'ouverte',
        offer_id INTEGER, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS offers(
        id INTEGER PRIMARY KEY, request_id INTEGER, tech_id INTEGER,
        prix REAL, message TEXT, created TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY, room TEXT, sender_id INTEGER, text TEXT, created TEXT)""")


def hash_pwd(pwd, salt):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt), 100_000).hex()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@st.cache_data
def load_dataset():
    return pd.read_csv(BASE / "dataset.csv").fillna("")


# ------------------------------------------------------------------ images
def show_image(source, caption=None):
    """Affiche une vraie image : fichier local (assets/) ou URL."""
    if not source:
        return
    local = ASSETS / str(source)
    try:
        st.image(str(local) if local.exists() else str(source),
                 caption=caption, use_container_width=True)
    except Exception:
        st.image(FALLBACK, use_container_width=True)


def banner(file, title, subtitle=""):
    c1, c2 = st.columns([2, 3], vertical_alignment="center")
    with c1:
        show_image(file)
    with c2:
        st.title(title)
        if subtitle:
            st.write(subtitle)


# ------------------------------------------------------------------ authentification
def page_auth():
    banner(HERO_2, "🚗 Mon Voiture",
           "Votre voiture, vos rappels, vos experts, au même endroit.")
    tab_in, tab_up = st.tabs(["Se connecter", "Créer mon compte"])

    with tab_in:
        email = st.text_input("Email", key="li_email")
        pwd = st.text_input("Mot de passe", type="password", key="li_pwd")
        if st.button("Connexion", type="primary"):
            u = run("SELECT * FROM users WHERE email=?", (email.strip().lower(),),
                    fetch=True, one=True)
            if u and secrets.compare_digest(u["pwd"], hash_pwd(pwd, u["salt"])):
                st.session_state.user = dict(u)
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")

    with tab_up:
        nom = st.text_input("Nom complet")
        email = st.text_input("Email", key="su_email")
        pwd = st.text_input("Mot de passe (6 caractères min.)", type="password", key="su_pwd")
        role = st.selectbox("Votre métier / profil", ROLES)
        ville = st.text_input("Ville")
        spec = ""
        if role in PRO_ROLES:
            spec = st.selectbox("Spécialité", CATEGORIES)
        if st.button("Créer mon compte", type="primary"):
            if not nom or "@" not in email or len(pwd) < 6:
                st.error("Vérifiez le nom, l'email et le mot de passe.")
            else:
                salt = secrets.token_hex(16)
                try:
                    run("INSERT INTO users(nom,email,salt,pwd,role,ville,specialite,created)"
                        " VALUES(?,?,?,?,?,?,?,?)",
                        (nom.strip(), email.strip().lower(), salt, hash_pwd(pwd, salt),
                         role, ville.strip(), spec, now()))
                    st.success("Compte créé, vous pouvez vous connecter.")
                except sqlite3.IntegrityError:
                    st.error("Cet email est déjà utilisé.")


# ------------------------------------------------------------------ pages
def my_cars(uid):
    return run("SELECT * FROM cars WHERE user_id=?", (uid,), fetch=True)


def page_accueil(user):
    banner(HERO_1, f"Bonjour {user['nom'].split()[0]} 👋", f"Profil : {user['role']}")
    uid = user["id"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Mes voitures", len(my_cars(uid)))
    rem = run("SELECT * FROM reminders WHERE user_id=? AND done=0 ORDER BY date",
              (uid,), fetch=True)
    c2.metric("Rappels à venir", len(rem))
    if user["role"] == "Conducteur":
        n = run("SELECT COUNT(*) n FROM requests WHERE user_id=? AND statut='ouverte'",
                (uid,), fetch=True, one=True)["n"]
        c3.metric("Demandes ouvertes", n)
    else:
        n = run("SELECT COUNT(*) n FROM requests WHERE statut='ouverte'", fetch=True, one=True)["n"]
        c3.metric("Demandes disponibles", n)

    st.subheader("Prochaines échéances")
    if not rem:
        st.info("Aucun rappel. Ajoutez-en dans « Rappels & dates ».")
    for r in rem[:5]:
        d = (date.fromisoformat(r["date"]) - date.today()).days
        icon = "🔴" if d < 0 else "🟠" if d <= 30 else "🟢"
        st.write(f"{icon} **{r['type']}** le {r['date']} "
                 f"({'en retard de ' + str(-d) if d < 0 else 'dans ' + str(d)} jours)")

    st.subheader("Ma voiture électrique ?")
    show_image(HERO_3)


def page_voitures(user):
    st.header("🚘 Mes voitures")
    with st.form("car"):
        c1, c2, c3 = st.columns(3)
        marque = c1.text_input("Marque")
        modele = c2.text_input("Modèle")
        annee = c3.number_input("Année", 1980, date.today().year, 2018)
        c4, c5 = st.columns(2)
        immat = c4.text_input("Immatriculation")
        km = c5.number_input("Kilométrage", 0, 1_000_000, 50_000, step=500)
        if st.form_submit_button("Ajouter") and marque and modele:
            run("INSERT INTO cars(user_id,marque,modele,annee,immat,km) VALUES(?,?,?,?,?,?)",
                (user["id"], marque, modele, int(annee), immat, int(km)))
            st.rerun()
    cars = my_cars(user["id"])
    if cars:
        df = pd.DataFrame([dict(c) for c in cars]).drop(columns=["user_id"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        with st.expander("Mettre à jour le kilométrage"):
            car = st.selectbox("Voiture", cars, format_func=lambda c: f"{c['marque']} {c['modele']}")
            new_km = st.number_input("Nouveau km", 0, 1_000_000, int(car["km"]), step=100)
            if st.button("Enregistrer le km"):
                run("UPDATE cars SET km=? WHERE id=?", (int(new_km), car["id"]))
                st.rerun()


def page_conseils():
    st.header("💡 Conseils par partie de la voiture")
    df = load_dataset()
    df = df[df["type"] == "conseil"]
    c1, c2 = st.columns([1, 2])
    cat = c1.selectbox("Catégorie", ["Toutes"] + sorted(df["categorie"].unique()))
    txt = c2.text_input("Rechercher")
    if cat != "Toutes":
        df = df[df["categorie"] == cat]
    if txt:
        df = df[df["titre"].str.contains(txt, case=False) | df["contenu"].str.contains(txt, case=False)]
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        with cols[i % 3].container(border=True):
            show_image(r["image"])
            st.caption(r["categorie"])
            st.subheader(r["titre"])
            st.write(r["contenu"])


def page_rappels(user):
    st.header("📅 Rappels & dates importantes")
    cars = my_cars(user["id"])
    if not cars:
        st.warning("Ajoutez d'abord une voiture.")
        return
    with st.form("rem"):
        car = st.selectbox("Voiture", cars, format_func=lambda c: f"{c['marque']} {c['modele']}")
        c1, c2 = st.columns(2)
        typ = c1.selectbox("Type", RAPPEL_TYPES)
        d = c2.date_input("Date d'échéance", date.today())
        note = st.text_input("Note (garage, prix...)")
        if st.form_submit_button("Enregistrer"):
            run("INSERT INTO reminders(user_id,car_id,type,date,note) VALUES(?,?,?,?,?)",
                (user["id"], car["id"], typ, d.isoformat(), note))
            st.rerun()
    rows = run("""SELECT r.*, c.marque, c.modele FROM reminders r
                  JOIN cars c ON c.id=r.car_id WHERE r.user_id=? ORDER BY r.done, r.date""",
               (user["id"],), fetch=True)
    for r in rows:
        d = (date.fromisoformat(r["date"]) - date.today()).days
        icon = "✅" if r["done"] else "🔴" if d < 0 else "🟠" if d <= 30 else "🟢"
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.write(f"{icon} **{r['type']}** · {r['marque']} {r['modele']} · {r['date']} · {r['note'] or ''}")
        if not r["done"] and c2.button("Fait", key=f"d{r['id']}"):
            run("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))
            st.rerun()
        if c3.button("Suppr.", key=f"x{r['id']}"):
            run("DELETE FROM reminders WHERE id=?", (r["id"],))
            st.rerun()


def page_demandes_client(user):
    st.header("🛠️ Mes demandes de service")
    st.caption("Décrivez le problème et proposez un budget : les techniciens vous envoient leurs offres.")
    cars = my_cars(user["id"])
    with st.form("req"):
        titre = st.text_input("Problème (ex : bruit au freinage)")
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Catégorie", CATEGORIES)
        budget = c2.number_input("Votre budget (MAD / €)", 0, 100_000, 300, step=10)
        car = c3.selectbox("Voiture", cars or [None],
                           format_func=lambda c: f"{c['marque']} {c['modele']}" if c else "—")
        desc = st.text_area("Détails")
        if st.form_submit_button("Publier la demande") and titre:
            run("INSERT INTO requests(user_id,car_id,titre,description,categorie,budget,created)"
                " VALUES(?,?,?,?,?,?,?)",
                (user["id"], car["id"] if car else None, titre, desc, cat, budget, now()))
            st.rerun()

    for r in run("SELECT * FROM requests WHERE user_id=? ORDER BY id DESC", (user["id"],), fetch=True):
        with st.container(border=True):
            st.subheader(f"{r['titre']}  ·  {r['statut']}")
            st.write(f"{r['categorie']} · budget {r['budget']:.0f} · {r['created']}")
            st.write(r["description"])
            offers = run("""SELECT o.*, u.nom, u.specialite, u.ville FROM offers o
                            JOIN users u ON u.id=o.tech_id WHERE request_id=?""",
                         (r["id"],), fetch=True)
            for o in offers:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{o['nom']}** ({o['specialite'] or 'général'}, {o['ville']}) "
                         f"→ **{o['prix']:.0f}** · {o['message']}")
                if r["statut"] == "ouverte" and c2.button("Accepter", key=f"acc{o['id']}"):
                    run("UPDATE requests SET statut='acceptée', offer_id=? WHERE id=?",
                        (o["id"], r["id"]))
                    st.rerun()
            if r["statut"] == "acceptée":
                st.success("Offre acceptée : discutez dans l'onglet « Discussions ».")
                if st.button("Marquer terminée", key=f"fin{r['id']}"):
                    run("UPDATE requests SET statut='terminée' WHERE id=?", (r["id"],))
                    st.rerun()


def page_missions_pro(user):
    st.header("📍 Demandes près de vous")
    st.caption("Façon inDrive : proposez votre prix, le client choisit.")
    reqs = run("""SELECT r.*, u.nom, u.ville FROM requests r JOIN users u ON u.id=r.user_id
                  WHERE r.statut='ouverte' ORDER BY r.id DESC""", fetch=True)
    if not reqs:
        st.info("Aucune demande ouverte pour le moment.")
    for r in reqs:
        with st.container(border=True):
            st.subheader(r["titre"])
            st.write(f"{r['categorie']} · {r['nom']} ({r['ville']}) · budget client : **{r['budget']:.0f}**")
            st.write(r["description"])
            mine = run("SELECT * FROM offers WHERE request_id=? AND tech_id=?",
                       (r["id"], user["id"]), fetch=True, one=True)
            if mine:
                st.info(f"Votre offre : {mine['prix']:.0f}")
            else:
                c1, c2 = st.columns([1, 3])
                prix = c1.number_input("Votre prix", 0, 100_000, int(r["budget"]), key=f"p{r['id']}")
                msg = c2.text_input("Message", key=f"m{r['id']}")
                if st.button("Envoyer l'offre", key=f"o{r['id']}", type="primary"):
                    run("INSERT INTO offers(request_id,tech_id,prix,message,created) VALUES(?,?,?,?,?)",
                        (r["id"], user["id"], prix, msg, now()))
                    st.rerun()

    st.subheader("Mes missions acceptées")
    won = run("""SELECT r.* FROM requests r JOIN offers o ON o.id=r.offer_id
                 WHERE o.tech_id=? ORDER BY r.id DESC""", (user["id"],), fetch=True)
    for r in won:
        st.write(f"✅ **{r['titre']}** · {r['statut']}")


def rooms_for(user):
    rooms = {"Communauté Mon Voiture": "general", "Experts & techniciens": "pros"}
    if user["role"] == "Conducteur":
        q = "SELECT * FROM requests WHERE user_id=? AND statut IN ('acceptée','terminée')"
        params = (user["id"],)
    else:
        q = """SELECT r.* FROM requests r JOIN offers o ON o.id=r.offer_id
               WHERE o.tech_id=?"""
        params = (user["id"],)
    for r in run(q, params, fetch=True):
        rooms[f"Mission : {r['titre']}"] = f"req-{r['id']}"
    if user["role"] == "Conducteur":
        rooms.pop("Experts & techniciens")
    return rooms


def page_chat(user):
    st.header("💬 Discussions")
    rooms = rooms_for(user)
    label = st.selectbox("Salon", list(rooms))
    room = rooms[label]
    if st.button("Actualiser"):
        st.rerun()
    msgs = run("""SELECT m.*, u.nom, u.role FROM messages m JOIN users u ON u.id=m.sender_id
                  WHERE room=? ORDER BY m.id DESC LIMIT 60""", (room,), fetch=True)[::-1]
    box = st.container(height=420)
    for m in msgs:
        mine = m["sender_id"] == user["id"]
        with box.chat_message("user" if mine else "assistant"):
            st.markdown(f"**{m['nom']}** · _{m['role']}_ · {m['created']}")
            st.write(m["text"])
    text = st.chat_input("Écrire un message...")
    if text:
        run("INSERT INTO messages(room,sender_id,text,created) VALUES(?,?,?,?)",
            (room, user["id"], text, now()))
        st.rerun()


def page_videos():
    st.header("🎬 Vidéos pour réparer soi-même")
    df = load_dataset()
    df = df[df["type"] == "video"]
    cat = st.selectbox("Catégorie", ["Toutes"] + sorted(df["categorie"].unique()))
    if cat != "Toutes":
        df = df[df["categorie"] == cat]
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        with cols[i % 3].container(border=True):
            if "watch?v=" in r["lien"] or "youtu.be" in r["lien"]:
                st.video(r["lien"])
            else:
                show_image(r["image"])
                st.link_button("▶ Voir la vidéo", r["lien"], use_container_width=True)
            st.subheader(r["titre"])
            st.caption(f"{r['categorie']} · {r['contenu']}")


def page_profil(user):
    st.header("👤 Mon profil")
    st.write(f"**Nom** : {user['nom']}")
    st.write(f"**Email** : {user['email']}")
    st.write(f"**Métier** : {user['role']}")
    st.write(f"**Ville** : {user['ville']}")
    if user["specialite"]:
        st.write(f"**Spécialité** : {user['specialite']}")


# ------------------------------------------------------------------ main
def main():
    init_db()
    user = st.session_state.get("user")
    if not user:
        page_auth()
        return

    with st.sidebar:
        show_image(HERO_1)
        st.markdown(f"### 🚗 Mon Voiture\n**{user['nom']}**  \n{user['role']}")
        pages = ["Accueil", "Conseils", "Vidéos", "Discussions"]
        if user["role"] == "Conducteur":
            pages[1:1] = ["Mes voitures", "Rappels & dates"]
            pages.insert(-1, "Mes demandes")
        else:
            pages.insert(1, "Demandes clients")
        pages.append("Profil")
        page = st.radio("Navigation", pages, label_visibility="collapsed")
        if st.button("Se déconnecter"):
            st.session_state.clear()
            st.rerun()

    if page == "Accueil":
        page_accueil(user)
    elif page == "Mes voitures":
        page_voitures(user)
    elif page == "Rappels & dates":
        page_rappels(user)
    elif page == "Conseils":
        page_conseils()
    elif page == "Vidéos":
        page_videos()
    elif page == "Mes demandes":
        page_demandes_client(user)
    elif page == "Demandes clients":
        page_missions_pro(user)
    elif page == "Discussions":
        page_chat(user)
    else:
        page_profil(user)


main()

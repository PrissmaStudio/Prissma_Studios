================================================================================
                           PRISSMA STUDIO - DOCUMENTATIE COMPLETA
================================================================================

Data creării: April 5, 2026
Versiune: 1.0
Autor: AI Assistant

================================================================================
1. STRUCTURA PROIECTULUI
================================================================================

Prissma/
├── app.py                          # Aplicația principală Flask
├── requirements.txt                # Dependențele Python
├── run_server_5001.py            # Script simplu de pornire (dezvoltare)
├── start_gunicorn.sh              # Script complet automatizat de producție
├── reviews.json                   # Fișierul cu recenzii utilizatori
├── cookies.txt                    # Fișier temporar pentru sesiuni (gitignore)
├── .env                           # Variabile de mediu (SECRET_KEY, ADMIN_PASSWORD)
├── .venv/                         # Mediul virtual Python (creat automat)
│
├── static/                        # Fișiere statice
│   ├── css/
│   │   └── style.css             # Stiluri CSS principale
│   ├── img/                      # Imagini statice
│   └── uploads/                  # Fișiere media încărcate (dacă există)
│
├── templates/                     # Template-uri Jinja2
│   ├── index.html                # Pagina principală cu galerie
│   ├── about.html                # Pagina "Despre"
│   ├── welcome.html              # Pagina de întâmpinare
│   ├── admin_login.html          # Formular login admin
│   ├── admin_dashboard.html      # Panou control admin
│   ├── admin_folder_security.html # Gestionare securitate foldere
│   ├── admin_upload.html         # Upload fișiere admin
│   ├── all_reviews.html          # Toate recenziile
│   └── unlock.html               # Pagina de deblocare foldere
│
├── misc_data/                     # Date auxiliare
│   ├── cache/                    # Cache thumbnails (automat generat)
│   ├── cache_thumbs/             # Thumbnails pentru imagini/video
│   └── folder_security.json      # Configurație securitate foldere
│
└── .git/                         # Repository Git

================================================================================
2. ARHITECTURA ȘI DEPENDENȚE
================================================================================

2.1 TEHNOLOGII PRINCIPALE
-------------------------
- Backend: Python 3.9+ cu Flask 3.x
- Bază de date: SQLite cu SQLAlchemy ORM
- Internaționalizare: Flask-Babel 4.0 (3 limbi: RO/EN/HU)
- Frontend: HTML5, CSS3, JavaScript ES6+
- Template Engine: Jinja2 cu gettext
- WSGI Server: Gunicorn (producție)
- Cache: Flask-Caching cu FileSystemCache
- Rate Limiting: Flask-Limiter
- Imagini: Pillow (PIL)
- Video Processing: FFmpeg (subprocess)

2.2 DEPENDENȚE PYTHON (requirements.txt)
---------------------------------------
Flask>=2.0              # Framework web principal
Flask-Caching>=1.10.1   # Sistem de cache
python-dotenv>=1.0      # Variabile de mediu
Pillow>=9.0             # Procesare imagini
Flask-Limiter>=2.0      # Rate limiting
Flask-SQLAlchemy>=3.0   # ORM pentru baza de date SQLite
Flask-Babel>=4.0        # Sistem internaționalizare
gunicorn               # WSGI server producție

2.3 BAZA DE DATE
---------------
- Tip: SQLite (prissma.db în /instance/)
- Modele: Review, FolderSecurity
- Migrare automată: Date existente migrate la pornire
- Backup: Fișiere JSON păstrate ca .backup

================================================================================
3. FUNCȚIONALITĂȚI PRINCIPALE
================================================================================

3.1 GALERIE FOTOGRAFICĂ
-----------------------
- Afișare imagini/video în grid responsive
- Zoom control (+/- butoane)
- Lightbox pentru vizualizare full-screen
- Navigare cu săgeți și ESC
- Orientare automată pentru portret/peisaj
- Lazy loading pentru performanță

3.2 GESTIONARE FOLDERE
----------------------
- Structură ierarhică în directorul uploads/
- Suport pentru HDD extern (/Volumes/media/Uploads_Atestat)
- Cache automat pentru thumbnails
- Fallback la cache offline când HDD deconectat

3.3 SISTEM SECURITATE FOLDERE
-----------------------------
- Protecție individuală per folder
- Chei de acces unice (32 caractere)
- Cookie-based persistence (30 zile)
- Link-uri de share directe
- Modal de unlock cu toggle password visibility
- Suport universal unlock (orice cheie deblochează folderul corespunzător)

3.4 PANOU ADMINISTRATOR
-----------------------
- Autentificare cu parolă
- Dashboard cu statistici (fișiere, dimensiune, recenzii)
- Gestionare securitate foldere (protect/unprotect/regenerate)
- Upload fișiere în foldere noi
- Vizualizare toate recenziile
- Indicator vizual verde când logat

3.5 SISTEM RECENZII
-------------------
- Formular review după descărcare
- Stocare în reviews.json
- Afișare ultimele 10 recenzii în dashboard
- Pagina dedicată pentru toate recenziile

3.6 FUNCȚII AJUTĂTOR
--------------------
- Tutorial modal cu instrucțiuni
- Selecție multi-imagini pentru descărcare ZIP
- Generare automată thumbnails pentru imagini/video
- Rate limiting pentru API endpoints
- Cache inteligent pentru performanță

================================================================================
4. FLUXURI DE LUCRU
================================================================================

4.1 PORNIRE APLICAȚIE
----------------------
1. Rulează ./start_gunicorn.sh
2. Scriptul verifică/creează mediu virtual
3. Instalează dependențe din requirements.txt
4. Eliberează portul 5001 dacă ocupat
5. Pornește Gunicorn cu 9 workeri
6. Aplicația devine accesibilă la http://localhost:5001

4.2 ÎNCĂRCARE CONȚINUT
----------------------
1. Admin se loghează la /admin/login
2. Accesează /admin/upload
3. Selectează folder și încarcă fișiere
4. Sistemul generează automat thumbnails
5. Fișierele apar în galerie

4.3 PROTECȚIE FOLDER
--------------------
1. Admin accesează /admin/folder-security
2. Selectează folder și apasă "Protect"
3. Sistemul generează cheie unică
4. Folderul devine inaccesibil fără cheie

4.4 ACCES FOLDER PROTEJAT
-------------------------
1. Utilizatorul accesează folder protejat
2. Apare modal de unlock (dacă automat) sau buton manual
3. Introduce cheia de acces
4. Sistemul verifică și setează cookie
5. Folderul devine accesibil pentru 30 zile

4.5 DESCĂRCARE CONȚINUT
-----------------------
1. Utilizatorul apasă "Selectează"
2. Selectează imagini cu click sau Ctrl+click
3. Apasă "Descarcă Selecția"
4. Sistemul generează ZIP
5. Apare formular review după descărcare

================================================================================
5. API ENDPOINTS
================================================================================

5.1 RUTE PUBLICE
-----------------
GET  /                    -> welcome.html
GET  /about               -> about.html
GET  /gallery             -> index.html (redirect la folder default)
GET  /f/<folder>          -> index.html cu folder specific
GET  /unlock/<folder>     -> unlock.html pentru folder
GET  /share/<folder>?key= -> share link cu cheie directă

5.2 API ENDPOINTS
-----------------
POST /api/unlock-folder   -> Deblochează folder cu cheie
POST /api/save_review     -> Salvează recenzie utilizator

5.3 RUTE ADMINISTRATOR
----------------------
GET  /admin/login         -> Formular login
POST /admin/login         -> Procesare login
GET  /admin/dashboard     -> Panou control principal
GET  /admin/folder-security -> Gestionare securitate
POST /admin/folder-security -> Actualizare securitate foldere
GET  /admin/upload        -> Formular upload
POST /admin/upload        -> Procesare upload
GET  /admin/all-reviews   -> Toate recenziile

================================================================================
6. SISTEM CACHE ȘI PERFORMANȚĂ
================================================================================

6.1 CACHE THUMBNAILS
---------------------
- Locație: misc_data/cache_thumbs/
- Format: WebP pentru calitate optimă
- Dimensiune: 800x800px max, păstrează aspect ratio
- Generare: Automată la upload sau prima accesare
- Video: Extrage frame la 1 secundă

6.2 CACHE APLICAȚIE
--------------------
- Tip: FileSystemCache
- Locație: misc_data/cache/
- Timeout: 3600 secunde (1 oră)
- Utilizare: Cache template-uri, date statice

6.3 OPTIMIZĂRI PERFORMANȚĂ
--------------------------
- Lazy loading pentru imagini
- Rate limiting pe API (prevenire abuz)
- Gzip compression implicit în Gunicorn
- Background processing pentru thumbnails

================================================================================
7. SISTEM BAZA DE DATE ȘI PERSISTENȚĂ
================================================================================

7.1 STRUCTURA BAZEI DE DATE
---------------------------
- Tabel Review: Stochează recenziile utilizatorilor
  - id: Cheie primară auto-increment
  - name: Nume utilizator (100 caractere)
  - email: Email utilizator (120 caractere)
  - rating: Rating 1-5 stele
  - comment: Comentariu text (opțional)
  - date: Data și ora (format DD/MM/YYYY HH:MM)
  - folder: Folderul din care provine recenzia

- Tabel FolderSecurity: Configurații securitate foldere
  - id: Cheie primară auto-increment
  - folder_name: Nume folder (unic)
  - access_key: Cheie de acces (64 caractere)
  - is_protected: Boolean pentru protecție

7.2 MIGRARE DATE EXISTENTE
---------------------------
La prima pornire, sistemul:
1. Creează tabelele bazei de date
2. Migrează recenziile din reviews.json
3. Migrează configurațiile din folder_security.json
4. Creează backup-uri ale fișierelor JSON (.backup)
5. Șterge fișierele JSON originale

7.3 PERFORMANȚĂ ȘI OPTIMIZĂRI
-----------------------------
- Indexare automată pe cheile străine
- Tranzacții pentru integritatea datelor
- Cache la nivel de aplicație pentru performanță
- Backup automat al fișierelor JSON înainte de migrare

================================================================================
8. SECURITATE ȘI CONFIGURARE
================================================================================

7.1 AUTENTIFICARE ADMIN
-----------------------
- Parolă configurabilă în .env (ADMIN_PASSWORD)
- Sesiune Flask persistentă
- Indicator vizual verde când logat
- Redirect automat către dashboard după login

7.2 SECURITATE FOLDERE
----------------------
- Chei unice generate cu secrets.token_urlsafe(32)
- Cookie-uri HttpOnly pentru chei de acces
- Expirare 30 zile pentru acces persistent
- Suport share links cu cheie în URL

7.3 VALIDARE ȘI SĂNITIZARE
---------------------------
- secure_filename() pentru upload-uri
- Rate limiting pe toate endpoint-urile
- Validare tip fișier (jpg, png, webp, mp4, mov, avi)
- Protecție XSS prin Jinja2 auto-escape

================================================================================
8. SISTEM INTERNAȚIONALIZARE (I18N)
================================================================================

8.1 LIMBI SUPORTATE
--------------------
- Română (ro) - limba implicită
- Engleză (en) - traducere completă
- Maghiară (hu) - traducere completă

8.2 SCHIMBAREA LIMBII
----------------------
- Selector în header-ul paginilor
- Parametru URL: ?lang=ro|en|hu
- Sesiune persistentă între pagini
- Fallback la limba browser-ului

8.3 IMPLEMENTARE TEHNICĂ
------------------------
- Flask-Babel 4.0 pentru gestionarea traducerilor
- Fișiere .po/.mo în translations/[lang]/LC_MESSAGES/
- Funcția gettext(_) în template-uri și Python
- Context processor pentru variabile globale
- Selector limbă cu nume traduse
- Mesaje API și erori traduse
- Titluri pagini admin traduse
- Toate textele vizibile sunt internaționalizate

8.4 ADĂUGAREA UNEI LIMBI NOI
-----------------------------
1. Adaugă codul limbii în BABEL_SUPPORTED_LOCALES
2. Creează directorul translations/[code]/LC_MESSAGES/
3. Copiază messages.po din altă limbă
4. Tradu textele în msgid "" și msgstr ""
5. Rulează: pybabel compile -d translations

================================================================================
9. DEPANARE ȘI ÎNTREȚINERE
================================================================================

9.1 COMENZI UTILE
-----------------
# Pornire dezvoltare
python3 run_server_5001.py

# Pornire producție
./start_gunicorn.sh

# Oprire server
pkill -f gunicorn

# Curățare cache
rm -rf misc_data/cache/ misc_data/cache_thumbs/

# Reset sesiuni
rm -f cookies.txt

# Backup bază de date
cp instance/prissma.db instance/prissma.db.backup

9.2 LOGGING ȘI DEBUG
--------------------
- Nivel: DEBUG în consolă
- Format: timestamp - level - message
- Logger principal: app.py
- Erori salvate în terminal

9.3 PROBLEME COMUNE
-------------------
1. Port 5001 ocupat: lsof -ti:5001 | xargs kill -9
2. Cache corupt: șterge misc_data/cache/
3. Thumbnails lipsă: sistem regenerează automat
4. Sesiune pierdută: reclogin admin
5. Bază de date coruptă: restaurează din .backup

================================================================================
10. EXTENSII ȘI ÎMBUNĂTĂȚIRI FUTURE
================================================================================

10.1 FUNCȚIONALITĂȚI PLANIFICATE
-------------------------------
- ✅ Database persistentă (SQLite) - IMPLEMENTAT
- Autentificare utilizatori multipli
- Categorii și tag-uri pentru imagini
- Galerie cu slideshow automat
- Backup automat al bazei de date
- API REST pentru integrări externe
- Suport pentru mai multe formate media

10.2 OPTIMIZĂRI TEHNICE
----------------------
- ✅ Database persistentă (SQLite) - IMPLEMENTAT
- CDN pentru fișiere statice
- Docker containerizare
- Monitoring și analytics
- Cache distribuit (Redis)

================================================================================
11. CONTACT ȘI SUPORT
================================================================================

Pentru întrebări sau probleme:
- Verifică logs în terminal
- Consultă această documentație
- Testează cu ./start_gunicorn.sh pentru setup complet

Aplicația Prissma Studio este acum complet funcțională cu sistem
de bază de date persistentă SQLite și internaționalizare în 3 limbi.

================================================================================
END OF DOCUMENTATION
================================================================================
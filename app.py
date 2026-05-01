from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, make_response, g, has_request_context, flash
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel, gettext, lazy_gettext
import os, json, logging, subprocess, threading, secrets, hashlib, time
import base64
from io import BytesIO
from PIL import Image, ImageOps, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import event
from sqlalchemy.engine import Engine


load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://" # Ține minte IP-urile și încercările în memoria RAM
)

app.secret_key = os.getenv('SECRET_KEY', 'prissma_ultimate_v2026')

app.secret_key = os.getenv('SECRET_KEY', 'prissma_ultimate_v2026')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
app.permanent_session_lifetime = 86400

# 🚀 OPTIMIZĂRI PRODUCȚIE - Performanță maximă
app.config['TESTING'] = False
app.config['DEBUG'] = False  # Dezactivat pentru producție
app.config['ENV'] = 'production'  # Setat pentru producție
app.config['SESSION_COOKIE_SECURE'] = False  # Dezactivează HTTPS requirement pentru viteză
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PREFERRED_URL_SCHEME'] = 'http'

# Optimizări SQLAlchemy pentru performanță maximă și multi-worker
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prissma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,        # Verifică conexiunile înainte de utilizare
    'pool_recycle': 300,          # Reciclează conexiunile la 5 minute
    'pool_size': 10,              # Mărime pool pentru multi-worker
    'max_overflow': 20,           # Overflow maxim
    'echo': False,                # Dezactivează logging SQL pentru viteză
    'connect_args': {
        'check_same_thread': False,  # SQLite optimization pentru multi-threading
        'timeout': 30.0             # Timeout pentru conexiuni
    }
}
db = SQLAlchemy(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # Activează Write-Ahead Logging (permite citiri și scrieri paralele)
    cursor.execute("PRAGMA journal_mode=WAL")
    # Optimizează viteza de scriere pe disc
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Spune-i să aștepte 5 secunde dacă baza e ocupată, în loc să dea crash instantaneu
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

# Configurare Babel pentru internaționalizare
app.config['BABEL_DEFAULT_LOCALE'] = 'ro'
app.config['BABEL_SUPPORTED_LOCALES'] = ['ro', 'en', 'hu']
app.config['TEMPLATES_AUTO_RELOAD'] = True
babel = Babel()

# Funcție pentru detectarea limbii
def get_locale():
    # Verifică parametrul lang din URL
    lang = request.args.get('lang')
    if lang and lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['lang'] = lang
        return lang
    
    # Verifică sesiunea
    lang = session.get('lang')
    if lang and lang in app.config['BABEL_SUPPORTED_LOCALES']:
        return lang
    
    # Fallback la limba browser-ului sau română
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES']) or 'ro'

# Inițializează Babel cu app și locale selector
babel.init_app(app, locale_selector=get_locale)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTERNAL_HDD = '/Volumes/media/Uploads_Atestat'
LOCAL_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
BEST_STATIC_FOLDER = os.path.join(BASE_DIR, 'static', 'best')
BEST_FOLDER_ALIAS = 'Best'
STRUCTURED_CACHE = os.path.join(os.getcwd(), 'misc_data', 'cache_thumbs')
FOLDER_SECURITY_FILE = os.path.join(os.getcwd(), 'misc_data', 'folder_security.json')
STATIC_IMG_DIR = os.path.join(os.getcwd(), 'static', 'img')
OPTIMIZED_IMG_DIR = os.path.join(STATIC_IMG_DIR, 'optimized')
STATIC_VIDEO_DIR = os.path.join(os.getcwd(), 'static', 'video')
OPTIMIZED_VIDEO_DIR = os.path.join(STATIC_VIDEO_DIR, 'optimized')
MEDIA_OPTIMIZATION_MARKER = os.path.join(os.getcwd(), 'misc_data', 'media_optimization.json')
THUMB_AVIF_SUPPORTED = '.avif' in Image.registered_extensions()
SELECTED_FOLDERS_FILE = os.path.join(os.getcwd(), 'misc_data', 'selected_folders.json')
EXTERNAL_HDD_CONFIG_FILE = os.path.join(os.getcwd(), 'misc_data', 'external_hdd.json')

# Monitorizare volume noi
KNOWN_VOLUMES = set()
VOLUME_CHECK_INTERVAL = 5  # secunde

def load_external_hdd():
    """Încarcă calea HDD extern din configurație"""
    try:
        if os.path.exists(EXTERNAL_HDD_CONFIG_FILE):
            with open(EXTERNAL_HDD_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('path', '/Volumes/media/Uploads_Atestat')
    except:
        pass
    return '/Volumes/media/Uploads_Atestat'

def save_external_hdd(path):
    """Salvează calea HDD extern în configurație"""
    try:
        os.makedirs(os.path.dirname(EXTERNAL_HDD_CONFIG_FILE), exist_ok=True)
        with open(EXTERNAL_HDD_CONFIG_FILE, 'w') as f:
            json.dump({'path': path}, f)
        return True
    except:
        return False

# Încarcă configurația HDD extern
# EXTERNAL_HDD este acum încărcat dinamic din fișier pentru suport multi-worker

def get_current_volumes():
    """Obține lista volumelor montate"""
    try:
        return set(os.listdir('/Volumes/'))
    except:
        return set()

def load_selected_folders():
    """Încarcă folderele selectate din configurație"""
    try:
        if os.path.exists(SELECTED_FOLDERS_FILE):
            with open(SELECTED_FOLDERS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_selected_folders(config):
    """Salvează configurația folderelor selectate"""
    try:
        os.makedirs(os.path.dirname(SELECTED_FOLDERS_FILE), exist_ok=True)
        with open(SELECTED_FOLDERS_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

def monitor_volumes():
    """Monitorizează pentru volume noi și întreabă utilizatorul"""
    global EXTERNAL_HDD
    while True:
        try:
            current_volumes = get_current_volumes()
            new_volumes = current_volumes - KNOWN_VOLUMES
            
            for volume in new_volumes:
                volume_path = os.path.join('/Volumes', volume)
                if os.path.isdir(volume_path) and volume not in ['media', 'Macintosh HD']:  # Exclude known
                    print(f"\n🔍 Volum nou detectat: {volume_path}")
                    response = input("Doriți să atașați acest volum la site? (y/n): ").strip().lower()
                    if response == 'y' or response == 'yes':
                        EXTERNAL_HDD = volume_path
                        print(f"✅ Volum atașat: {volume_path}")
                        # Generează cache pentru folderele existente
                        generate_cache_for_attached_volume()
                    else:
                        print("❌ Volum ignorat")
            
            KNOWN_VOLUMES.update(new_volumes)
        except Exception as e:
            print(f"Eroare la monitorizarea volumelor: {e}")
        
        time.sleep(VOLUME_CHECK_INTERVAL)

def generate_cache_for_attached_volume():
    """Generează cache pentru volumul atașat"""
    try:
        base = get_base_dir()
        if not os.path.exists(base):
            print(f"❌ Baza {base} nu există")
            return
        
        selected_folders_config = load_selected_folders()
        volume_name = os.path.basename(base) if base.startswith('/Volumes/') else None
        print(f"🔄 Generare cache pentru volumul atașat: {base} (volume_name: {volume_name})")
        print(f"📁 Config selecții: {selected_folders_config}")
        processed = 0
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if _is_visible_folder(d)]
            rel_root = os.path.relpath(root, base)
            folder_name = '' if rel_root == '.' else rel_root.replace('\\', '/')
            
            # Verifică dacă folder-ul este selectat în configurația de stocare
            should_process = False
            if folder_name == '':
                should_process = True
                print(f"✅ Procesare root: {folder_name}")
            else:
                if _is_folder_selected(folder_name, selected_folders_config, volume_name):
                    should_process = True
                    print(f"✅ Procesare folder selectat: {folder_name}")
                else:
                    print(f"❌ Folder neselctat: {folder_name}")
            
            if should_process:
                for f in files:
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv')):
                        orig = os.path.join(root, f)
                        for variant in ('lqip', 'grid', 'lightbox'):
                            dest = _thumb_cache_path(folder_name, f, variant)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            if generate_fast_thumb(orig, dest, variant):
                                processed += 1
                                if processed % 10 == 0:
                                    print(f"Procesate {processed} imagini...")
        
        print(f"✅ Cache generat pentru {processed} fișiere din {base}")
    except Exception as e:
        print(f"❌ Eroare la generarea cache: {e}")
        import traceback
        traceback.print_exc()

# Inițializează volumele cunoscute
KNOWN_VOLUMES = get_current_volumes()

for folder in [STRUCTURED_CACHE, os.path.dirname(STRUCTURED_CACHE), LOCAL_FOLDER]:
    os.makedirs(folder, exist_ok=True)
os.makedirs(OPTIMIZED_IMG_DIR, exist_ok=True)
os.makedirs(OPTIMIZED_VIDEO_DIR, exist_ok=True)

# Modele baza de date
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    date = db.Column(db.String(20), nullable=False)
    folder = db.Column(db.String(200), nullable=True)

class FolderSecurity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_name = db.Column(db.String(200), unique=True, nullable=False)
    access_key = db.Column(db.String(64), nullable=True)
    is_protected = db.Column(db.Boolean, default=False)

# Funcții de migrare date existente
def migrate_reviews_to_db():
    """Migrează recenziile din JSON în baza de date"""
    if not os.path.exists('reviews.json'):
        return

    try:
        with open('reviews.json', 'r') as f:
            content = f.read().strip()
            if not content:  # Fișier gol
                logger.info("Reviews JSON file is empty, skipping migration")
                return
            reviews_data = json.loads(content)

        for review_data in reviews_data:
            # Verifică dacă recenzia există deja
            existing = Review.query.filter_by(
                name=review_data.get('name'),
                email=review_data.get('email'),
                date=review_data.get('date')
            ).first()

            if not existing:
                review = Review(
                    name=review_data.get('name', ''),
                    email=review_data.get('email', ''),
                    rating=review_data.get('rating', 5),
                    comment=review_data.get('comment'),
                    date=review_data.get('date', datetime.now().strftime("%d/%m/%Y %H:%M")),
                    folder=review_data.get('folder')
                )
                db.session.add(review)

        db.session.commit()
        logger.info(f"Migrated {len(reviews_data)} reviews to database")

        # Backup și ștergere fișier JSON
        os.rename('reviews.json', 'reviews.json.backup')
        logger.info("Reviews migrated successfully, JSON file backed up")

    except Exception as e:
        logger.error(f"Error migrating reviews: {e}")

def migrate_folder_security_to_db():
    """Migrează configurația securității folderelor din JSON în baza de date"""
    if not os.path.exists(FOLDER_SECURITY_FILE):
        return

    try:
        with open(FOLDER_SECURITY_FILE, 'r') as f:
            security_data = json.load(f)

        for folder_name, config in security_data.items():
            # Verifică dacă folderul există deja
            existing = FolderSecurity.query.filter_by(folder_name=folder_name).first()

            if not existing:
                folder_security = FolderSecurity(
                    folder_name=folder_name,
                    access_key=config.get('access_key'),
                    is_protected=config.get('is_protected', False)
                )
                db.session.add(folder_security)

        db.session.commit()
        logger.info(f"Migrated {len(security_data)} folder security configs to database")

        # Backup și ștergere fișier JSON
        os.rename(FOLDER_SECURITY_FILE, FOLDER_SECURITY_FILE + '.backup')
        logger.info("Folder security migrated successfully, JSON file backed up")

    except Exception as e:
        logger.error(f"Error migrating folder security: {e}")

# Inițializare bază de date și migrare
with app.app_context():
    db.create_all()
    migrate_reviews_to_db()
    migrate_folder_security_to_db()

# Middleware pentru marcare sesiuni permanente
@app.before_request
def make_session_permanent():
    session.permanent = True

cache = Cache(app, config={
    'CACHE_TYPE': 'FileSystemCache',
    'CACHE_DIR': 'misc_data/cache',
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_THRESHOLD': 1000,  # Mai multe fișiere în cache
    'CACHE_KEY_PREFIX': 'prissma_'
})

# 🚀 OPTIMIZARE STATIC FILES - Cache și compresie
@app.after_request
def add_static_cache_headers(response):
    """Adaugă headere pentru optimizare performanță"""
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 an
        response.headers['X-Accel-Expires'] = '31536000'
    return response

limiter = Limiter(get_remote_address, app=app)


@app.template_filter('b64encode')
def b64encode_filter(value):
    if value is None:
        return ''
    text = str(value)
    return base64.b64encode(text.encode('utf-8')).decode('ascii')

# --- UTILS ---
def get_base_dir():
    external_hdd = load_external_hdd()  # Citește direct din fișier pentru multi-worker
    if os.path.exists(external_hdd):
        return external_hdd
    if os.path.exists(LOCAL_FOLDER):
        return LOCAL_FOLDER
    return STRUCTURED_CACHE

def is_offline_mode():
    return get_base_dir() == STRUCTURED_CACHE


def _is_folder_selected(rel, selected_folders_config, volume_name=None):
    """Verifică dacă folder-ul este selectat pentru un volum"""
    if volume_name is None:
        # Pentru volume noi sau când nu știm numele volumului, permite toate
        return True
    
    selected_folders = selected_folders_config.get(volume_name) or []
    if not selected_folders:
        # Dacă nu există selecții explicite, permite toate folderele
        return True
    for selected_folder in selected_folders:
        if rel == selected_folder or rel.startswith(selected_folder + '/'):
            return True
    return False


def _list_cached_preview_media(folder_path):
    """Return only canonical preview files from cache_thumbs folder.
    Filters out variant files (.grid-*, .lightbox, .lqip) and duplicate copies.
    Keeps only WEBP format for consistency.
    """
    if not os.path.isdir(folder_path):
        return []

    entries = sorted(os.listdir(folder_path))
    by_stem = {}
    for name in entries:
        full_path = os.path.join(folder_path, name)
        if not os.path.isfile(full_path) or name.startswith('.'):
            continue

        lower = name.lower()
        if not lower.endswith('.webp'):
            continue

        stem, ext = os.path.splitext(name)
        stem_lower = stem.lower()

        if '.grid-' in stem_lower or '.lightbox' in stem_lower or '.lqip' in stem_lower:
            continue

        # Keep only WEBP files, no duplicates
        by_stem[stem] = name

    return [by_stem[key] for key in sorted(by_stem.keys(), key=str.lower)]

def is_video(filename):
    return filename.lower().endswith(('.mp4', '.mov', '.webm', '.avi', '.mkv'))

def is_safe_path(base, target):
    return os.path.abspath(target).startswith(os.path.abspath(base))


def normalize_folder_name(folder_name):
    if folder_name is None:
        return ''
    cleaned = str(folder_name).replace('\\', '/').strip('/')
    if not cleaned:
        return ''
    normalized = os.path.normpath(cleaned).replace('\\', '/')
    if normalized in ('', '.'):
        return ''
    if normalized == '..' or normalized.startswith('../') or '/..' in normalized:
        return None
    return normalized


def is_best_folder(folder_name):
    return normalize_folder_name(folder_name) == BEST_FOLDER_ALIAS


def translate_best_folder_name(folder_name):
    return normalize_folder_name(folder_name)

def _translate_best_path(p):
    return p


def _folder_cookie_key(folder_name):
    normalized = normalize_folder_name(folder_name) or ''
    digest = hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:20]
    return f'folder_key_{digest}'


def _folder_prefixes(folder_name):
    normalized = normalize_folder_name(folder_name)
    if normalized in (None, ''):
        return []
    parts = normalized.split('/')
    prefixes = []
    for i in range(1, len(parts) + 1):
        prefixes.append('/'.join(parts[:i]))
    return prefixes


def _is_visible_folder(folder_name):
    exclude = {'misc_data', '.ds_store'}   # ← 'best' a fost eliminat
    return bool(folder_name) and not folder_name.startswith('.') and folder_name.lower() not in exclude


def list_accessible_folders():
    collected = []
    seen = set()

    # Verifică AMBELE surse: HDD + local
    bases = []
    external_hdd = load_external_hdd()
    if os.path.exists(external_hdd):
        bases.append(external_hdd)
    if os.path.exists(LOCAL_FOLDER) and LOCAL_FOLDER not in bases:
        bases.append(LOCAL_FOLDER)

    security = load_folder_security()
    request_cookies = request.cookies if has_request_context() else {}
    selected_folders_config = load_selected_folders()

    for base in bases:
        if not os.path.exists(base):
            continue
        volume_name = os.path.basename(base) if base.startswith('/Volumes/') else None

        for root, dirs, _ in os.walk(base):
            dirs[:] = sorted([d for d in dirs if _is_visible_folder(d)])
            rel_root = os.path.relpath(root, base)
            for folder in dirs:
                rel = folder if rel_root == '.' else os.path.join(rel_root, folder).replace('\\', '/')
                if rel in seen:
                    continue
                if user_has_access(rel, security=security, cookies=request_cookies):
                    if _is_folder_selected(rel, selected_folders_config, volume_name):
                        collected.append(rel)
                        seen.add(rel)

    return sorted(set(collected), key=lambda x: (x.count('/'), x.lower()))

def list_direct_subfolders(folder_name):
    base = get_base_dir()
    normalized = translate_best_folder_name(folder_name)
    if normalized is None:
        return []

    parent_path = base if not normalized else os.path.join(base, normalized)
    if not os.path.isdir(parent_path):
        return []

    security = load_folder_security()
    request_cookies = request.cookies if has_request_context() else {}
    selected_folders_config = load_selected_folders()
    volume_name = os.path.basename(base) if base.startswith('/Volumes/') else None

    subfolders = []
    for entry in sorted(os.listdir(parent_path)):
        if not _is_visible_folder(entry):
            continue
        full = os.path.join(parent_path, entry)
        if not os.path.isdir(full):
            continue
        rel = entry if not normalized else f"{normalized}/{entry}"
        rel = rel.replace('\\', '/')
        if user_has_access(rel, security=security, cookies=request_cookies):
            if _is_folder_selected(rel, selected_folders_config, volume_name):
                subfolders.append(rel)
    return subfolders


def build_folder_breadcrumbs(folder_name):
    normalized = translate_best_folder_name(folder_name)
    if normalized in (None, ''):
        return []

    parts = normalized.split('/')
    crumbs = []
    for i, part in enumerate(parts, 1):
        crumbs.append({
            'name': part,
            'path': '/'.join(parts[:i])
        })
    return crumbs

def _thumb_variant_suffix(variant, image_format='webp'):
    fmt = 'avif' if image_format == 'avif' else 'webp'
    base = {
        'grid': '',
        'grid_md': '.grid-md',
        'grid_sm': '.grid-sm',
        'grid_xs': '.grid-xs',
        'lightbox': '.lightbox',
        'lqip': '.lqip'
    }.get(variant, '')
    return f"{base}.{fmt}"


def _thumb_variant_config(variant):
    if variant == 'grid_md':
        return {'size': (640, 640), 'quality': 64, 'method': 6}
    if variant == 'grid_sm':
        return {'size': (480, 480), 'quality': 56, 'method': 6}
    if variant == 'grid_xs':
        return {'size': (320, 320), 'quality': 46, 'method': 6}
    if variant == 'lightbox':
        return {'size': (1800, 1800), 'quality': 86, 'method': 6}
    if variant == 'lqip':
        return {'size': (64, 64), 'quality': 36, 'method': 6}
    return {'size': (800, 800), 'quality': 72, 'method': 6}


def _thumb_cache_path(folder, filename, variant='grid', image_format='webp'):
    stem = os.path.splitext(filename)[0]
    return os.path.join(STRUCTURED_CACHE, folder, f"{stem}{_thumb_variant_suffix(variant, image_format)}")


def generate_fast_thumb(orig, cache_p, variant='grid', image_format='webp'):
    if os.path.exists(cache_p):
        return True
    try:
        cfg = _thumb_variant_config(variant)
        if not is_video(orig):
            with Image.open(orig) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                img.thumbnail(cfg['size'], Image.Resampling.LANCZOS)
                if image_format == 'avif' and THUMB_AVIF_SUPPORTED:
                    img.save(cache_p, 'AVIF', quality=cfg['quality'], optimize=True, exif=b'')
                else:
                    img.save(
                        cache_p,
                        'WEBP',
                        quality=cfg['quality'],
                        method=cfg['method'],
                        optimize=True,
                        exif=b''
                    )
        else:
            scale = f"scale={cfg['size'][0]}:-1"
            subprocess.run(
                ['ffmpeg', '-y', '-i', orig, '-ss', '00:00:01', '-vframes', '1', '-vf', scale, '-q:v', '45', cache_p],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        return True
    except:
        return False


def list_folder_media(folder_name, base_dir=None):
    normalized = normalize_folder_name(folder_name)
    if normalized is None:
        return []

    # Offline mode
    if is_offline_mode():
        target = os.path.join(get_base_dir(), normalized)
        if os.path.exists(target) and is_safe_path(get_base_dir(), target):
            return _list_cached_preview_media(target)
        return []

    cache_key = f"media_list::{normalized}::{get_base_dir()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    files = []
    seen = set()

    primary_base = base_dir if base_dir is not None else get_base_dir()
    target = os.path.join(primary_base, normalized)
    if os.path.exists(target) and is_safe_path(primary_base, target):
        for f in sorted(os.listdir(target)):
            full_path = os.path.join(target, f)
            if f.startswith('.') or not os.path.isfile(full_path):
                continue
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv')):
                files.append(f)
                seen.add(f.lower())

    if primary_base != LOCAL_FOLDER and os.path.exists(LOCAL_FOLDER):
        local_target = os.path.join(LOCAL_FOLDER, normalized)
        if os.path.exists(local_target) and is_safe_path(LOCAL_FOLDER, local_target):
            for f in sorted(os.listdir(local_target)):
                if f.lower() in seen:
                    continue
                full_path = os.path.join(local_target, f)
                if f.startswith('.') or not os.path.isfile(full_path):
                    continue
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv')):
                    files.append(f)
                    seen.add(f.lower())

    files.sort(key=str.lower)
    cache.set(cache_key, files, timeout=60)
    return files

def generate_thumbs_for_folder(folder_path):
    if is_offline_mode(): return
    base = get_base_dir()
    rel = os.path.relpath(folder_path, base)
    for f in os.listdir(folder_path):
        if f.lower().endswith(('.jpg','.jpeg','.png','.heic','.heif','.mp4','.mov')):
            orig = os.path.join(folder_path, f)
            for variant in ('lqip', 'grid', 'lightbox'):
                dest = _thumb_cache_path(rel, f, variant)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                generate_fast_thumb(orig, dest, variant)
                if THUMB_AVIF_SUPPORTED and not is_video(f):
                    avif_dest = _thumb_cache_path(rel, f, variant, image_format='avif')
                    os.makedirs(os.path.dirname(avif_dest), exist_ok=True)
                    generate_fast_thumb(orig, avif_dest, variant, image_format='avif')

    cache.delete(f"media_list::{rel}::{get_base_dir()}")


def _optimize_static_images():
    processed = 0
    if not os.path.exists(STATIC_IMG_DIR):
        return processed

    image_ext = ('.jpg', '.jpeg', '.png', '.webp')

    for root, _, files in os.walk(STATIC_IMG_DIR):
        if os.path.abspath(root).startswith(os.path.abspath(OPTIMIZED_IMG_DIR)):
            continue

        rel_root = os.path.relpath(root, STATIC_IMG_DIR)
        for file_name in files:
            if not file_name.lower().endswith(image_ext):
                continue

            source_path = os.path.join(root, file_name)
            rel_name = os.path.splitext(file_name)[0] + '.webp'
            if rel_root == '.':
                dest_path = os.path.join(OPTIMIZED_IMG_DIR, rel_name)
            else:
                dest_path = os.path.join(OPTIMIZED_IMG_DIR, rel_root, rel_name)

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            if os.path.exists(dest_path) and os.path.getmtime(dest_path) >= os.path.getmtime(source_path):
                continue

            try:
                with Image.open(source_path) as img:
                    img = ImageOps.exif_transpose(img)
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                    img.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
                    img.save(dest_path, 'WEBP', quality=84, method=6, optimize=True, exif=b'')
                    processed += 1
            except Exception as exc:
                logger.warning(f"Static optimization skipped for {source_path}: {exc}")

    return processed


def _prebuild_all_gallery_thumbs():
    if is_offline_mode():
        return 0

    base = get_base_dir()
    if not os.path.exists(base):
        return 0

    processed = 0
    tasks = []
    valid_ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv')

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if _is_visible_folder(d)]
        rel_root = os.path.relpath(root, base)
        rel_root = '' if rel_root == '.' else rel_root.replace('\\', '/')

        for file_name in files:
            if not file_name.lower().endswith(valid_ext):
                continue

            source_path = os.path.join(root, file_name)
            folder_name = rel_root
            if not folder_name:
                continue

            for variant in ('lqip', 'grid', 'lightbox'):
                destination = _thumb_cache_path(folder_name, file_name, variant, image_format='webp')
                if os.path.exists(destination):
                    continue
                tasks.append((source_path, destination, variant, 'webp'))

                if THUMB_AVIF_SUPPORTED and not is_video(file_name):
                    avif_destination = _thumb_cache_path(folder_name, file_name, variant, image_format='avif')
                    if not os.path.exists(avif_destination):
                        tasks.append((source_path, avif_destination, variant, 'avif'))

    if not tasks:
        return 0

    worker_count = max(2, min(24, (os.cpu_count() or 4) * 2))

    def _run_thumb_task(task):
        source_path, destination, variant, image_format = task
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        existed_before = os.path.exists(destination)
        if generate_fast_thumb(source_path, destination, variant, image_format=image_format) and not existed_before:
            return 1
        return 0

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for created in executor.map(_run_thumb_task, tasks):
            processed += created

    return processed


def _optimize_background_video():
    webm_dest = os.path.join(OPTIMIZED_VIDEO_DIR, 'background.webm')
    source = os.path.join(STATIC_VIDEO_DIR, 'background.mp4')
    if not os.path.exists(source):
        return {'webm': os.path.exists(webm_dest)}

    source_mtime = os.path.getmtime(source)
    webm_done = os.path.exists(webm_dest) and os.path.getmtime(webm_dest) >= source_mtime

    if not webm_done:
        try:
            subprocess.run(
                [
                    'ffmpeg', '-y', '-i', source,
                    '-vf', 'scale=1280:-2',
                    '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '35',
                    '-an', webm_dest
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
            webm_done = os.path.exists(webm_dest)
        except Exception as exc:
            logger.warning(f"WebM optimization failed: {exc}")

    return {'webm': webm_done}


def optimize_existing_media_assets(force=False):
    today = datetime.now().strftime('%Y-%m-%d')
    if not force and os.path.exists(MEDIA_OPTIMIZATION_MARKER):
        try:
            with open(MEDIA_OPTIMIZATION_MARKER, 'r') as marker_file:
                marker_data = json.load(marker_file)
            if marker_data.get('date') == today:
                return marker_data
        except Exception:
            pass

    static_count = _optimize_static_images()
    thumbs_count = _prebuild_all_gallery_thumbs()
    video_status = _optimize_background_video()
    marker_data = {
        'date': today,
        'static_optimized': static_count,
        'thumbs_generated': thumbs_count,
        'video_webm_ready': video_status['webm']
    }

    try:
        os.makedirs(os.path.dirname(MEDIA_OPTIMIZATION_MARKER), exist_ok=True)
        with open(MEDIA_OPTIMIZATION_MARKER, 'w') as marker_file:
            json.dump(marker_data, marker_file)
    except Exception as exc:
        logger.warning(f"Could not persist optimization marker: {exc}")

    return marker_data


def start_media_optimization_warmup():
    def _worker():
        import time
        import os
        
        # Așteptăm 2 secunde să pornească toți workerii Gunicorn
        time.sleep(2)
        
        # Creăm un "semafor" ca să ne asigurăm că un singur worker face treaba
        lock_file = os.path.join(get_base_dir(), '.warmup_lock')
        
        # Dacă fișierul există și a fost creat recent (în ultimele 60 de sec), alt worker deja lucrează
        if os.path.exists(lock_file) and (time.time() - os.path.getmtime(lock_file) < 60):
            return 
            
        try:
            # Blocăm accesul celorlalți workeri
            with open(lock_file, 'w') as f:
                f.write('ocupat')
                
            with app.app_context():
                print("🔄 [Worker Principal] Scanare poze și generare cache...")
                cache.clear()
                _prebuild_all_gallery_thumbs()
                print("✅ Scanare și cache complet!")
        except Exception as exc:
            print(f"⚠️ Eroare la cache: {exc}")
            
    threading.Thread(target=_worker, daemon=True).start()



# --- FOLDER SECURITY FUNCTIONS ---
def load_folder_security(force_refresh=False):
    """Încarcă configurația de securitate a folderelor din baza de date"""
    if has_request_context() and not force_refresh:
        cached_in_request = getattr(g, '_folder_security_cache', None)
        if cached_in_request is not None:
            return cached_in_request

    if not force_refresh:
        cached_global = cache.get('folder_security_db_v1')
        if cached_global is not None:
            if has_request_context():
                g._folder_security_cache = cached_global
            return cached_global

    security_dict = {}
    try:
        folder_securities = FolderSecurity.query.all()
        for fs in folder_securities:
            security_dict[fs.folder_name] = {
                'is_protected': fs.is_protected,
                'access_key': fs.access_key
            }
        cache.set('folder_security_db_v1', security_dict, timeout=30)
        if has_request_context():
            g._folder_security_cache = security_dict
    except Exception as e:
        logger.error(f"Error loading folder security: {e}")
    return security_dict

def save_folder_security(data):
    """Salvează configurația de securitate a folderelor în baza de date"""
    try:
        for folder_name, config in data.items():
            folder_security = FolderSecurity.query.filter_by(folder_name=folder_name).first()
            if folder_security:
                folder_security.is_protected = config.get('is_protected', False)
                folder_security.access_key = config.get('access_key')
            else:
                folder_security = FolderSecurity(
                    folder_name=folder_name,
                    access_key=config.get('access_key'),
                    is_protected=config.get('is_protected', False)
                )
                db.session.add(folder_security)
        db.session.commit()
        cache.delete('folder_security_db_v1')
        if has_request_context() and hasattr(g, '_folder_security_cache'):
            delattr(g, '_folder_security_cache')
    except Exception as e:
        logger.error(f"Error saving folder security: {e}")
        db.session.rollback()

def generate_access_key():
    """Generează o cheie de acces unică"""
    return secrets.token_urlsafe(32)

def is_folder_protected(folder_name):
    """Verifică dacă un folder este protejat"""
    security = load_folder_security()
    return folder_name in security and security[folder_name].get('is_protected', False)


def find_folder_by_access_key(access_key):
    """Caută folderul asociat unei chei de acces"""
    if not access_key:
        return None
    security = load_folder_security()
    for folder, data in security.items():
        if data.get('is_protected') and data.get('access_key') == access_key:
            return folder

    # Backward compatibility: if the DB key differs from the backup file,
    # allow unlocking with a valid key from the legacy backup data.
    backup_file = os.path.join(os.getcwd(), 'misc_data', 'folder_security.json.backup')
    if os.path.exists(backup_file):
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            for folder, data in backup_data.items():
                if data.get('is_protected') and data.get('access_key') == access_key:
                    return folder
        except Exception:
            pass
    return None


def user_has_access(folder_name, access_key=None, security=None, cookies=None):
    """Verifică dacă utilizatorul are acces la un folder protejat"""
    normalized = normalize_folder_name(folder_name)
    if normalized is None:
        return False

    security = security if security is not None else load_folder_security()
    cookies = cookies if cookies is not None else (request.cookies if has_request_context() else {})

    protected_prefixes = [
        p for p in _folder_prefixes(normalized)
        if security.get(p, {}).get('is_protected', False)
    ]

    if not protected_prefixes:
        return True

    if access_key is not None and normalized in protected_prefixes:
        return access_key == security.get(normalized, {}).get('access_key')

    for protected_folder in protected_prefixes:
        current_key = security.get(protected_folder, {}).get('access_key')
        cookie_key = cookies.get(_folder_cookie_key(protected_folder)) if cookies else None
        if cookie_key != current_key:
            return False

    return True

def set_folder_access_cookie(response, folder_name, access_key):
    """Setează cookie pentru acces la folder"""
    response.set_cookie(_folder_cookie_key(folder_name), access_key, max_age=2592000, path='/')  # 30 zile

@app.context_processor
def inject_global_data():
    offline = is_offline_mode()
    proiecte = list_accessible_folders()
    proiecte_dropdown = []
    seen_projects = set()
    for folder_path in proiecte:
        project_name = folder_path.split('/')[0]
        if project_name not in seen_projects:
            seen_projects.add(project_name)
            proiecte_dropdown.append(project_name)

    print(f"🔍 Context processor: base_dir={get_base_dir()}, proiecte={len(proiecte)}, dropdown={len(proiecte_dropdown)}")
    optimized_logo_rel = os.path.join('img', 'optimized', 'Untitled design - 2.webp')
    if os.path.exists(os.path.join(os.getcwd(), 'static', optimized_logo_rel)):
        logo_asset = optimized_logo_rel
    else:
        logo_asset = os.path.join('img', 'Untitled design - 2.png')
    
    return {
        'proiecte': proiecte,
        'proiecte_dropdown': proiecte_dropdown,
        'is_admin': session.get('is_admin', False),
        'is_offline': offline,
        'logo_asset': logo_asset,
        'current_lang': get_locale(),
        'available_languages': [
            {'code': 'ro', 'name': gettext('Romanian')},
            {'code': 'en', 'name': gettext('English')},
            {'code': 'hu', 'name': gettext('Hungarian')}
        ]
    }

# --- RUTE ---

@app.route('/set-language/<lang>')
def set_language(lang):
    """Set user's language preference"""
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['lang'] = lang
    referrer = request.referrer or url_for('gallery')
    return redirect(referrer)


@app.route('/')
def welcome(): return render_template('welcome.html')

@app.   route('/about')
def about(): return render_template('about.html')

@app.route('/gallery')
@app.route('/f/')
@app.route('/f/<path:folder_name>')
def gallery(folder_name=None):
    base = get_base_dir()

    # 1. Logică de portofoliu principal: dacă intră pe /gallery, deschide direct folderul Best
    if folder_name is None:
        if os.path.isdir(os.path.join(base, 'Best')):
            selected = 'Best'
        elif os.path.isdir(os.path.join(base, 'best')):
            selected = 'best'
        else:
            selected = ''
    else:
        selected = normalize_folder_name(folder_name)
        if selected is None:
            return "Invalid folder", 400

    selected_path = os.path.join(base, selected) if selected else base

    # Fallback la HDD offline
    if not os.path.isdir(selected_path):
        alt_base = LOCAL_FOLDER if base != LOCAL_FOLDER else get_base_dir()
        alt_path = os.path.join(alt_base, selected) if selected else alt_base
        if os.path.isdir(alt_path):
            base = alt_base
            selected_path = alt_path

    security = load_folder_security()
    request_cookies = request.cookies if has_request_context() else {}

    is_protected = security.get(selected, {}).get('is_protected', False)
    has_access = user_has_access(selected, security=security, cookies=request_cookies)

    subfolders = list_direct_subfolders(selected)
    breadcrumbs = build_folder_breadcrumbs(selected)
    # Afișează scurtătura către proiect doar dacă suntem adânc într-un subfolder, nu la rădăcină
    project_root = selected.split('/')[0] if selected and '/' in selected else ''

    if is_protected and not has_access:
        fisiere_data = []
        is_empty = len(subfolders) == 0
        show_unlock_modal = True
    else:
        fisiere_data = list_folder_media(selected)
        is_empty = (len(fisiere_data) == 0 and len(subfolders) == 0)
        show_unlock_modal = False

    initial_batch_size = 10000
    
    return render_template('index.html',
        fisiere=fisiere_data,
        fisiere_initial=fisiere_data[:initial_batch_size],
        initial_batch_size=initial_batch_size,
        folder_activ=selected,
        is_empty=is_empty,
        is_protected=is_protected,
        show_unlock_modal=show_unlock_modal,
        subfolders=subfolders,
        breadcrumbs=breadcrumbs,
        project_root=project_root,
        best_folder_available=False,
        best_folder_count=0)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    base = get_base_dir()
    total_files = total_images = total_videos = total_size = 0
    for root, _, files in os.walk(base):
        for f in files:
            if f.lower().endswith(('.jpg','.jpeg','.png','.heic','.heif','.mp4','.mov')):
                total_files += 1
                total_size += os.path.getsize(os.path.join(root, f))
                if is_video(f): total_videos += 1
                else: total_images += 1

    reviews_data = []
    try:
        # 🚀 OPTIMIZARE: Cache pentru reviews (5 minute)
        cache_key = 'admin_reviews_data'
        reviews_data = cache.get(cache_key)
        if reviews_data is None:
            reviews = Review.query.filter(Review.comment != None, Review.comment != '').order_by(Review.id.desc()).all()
            reviews_data = [{
                'id': r.id,
                'name': r.name,
                'email': r.email,
                'rating': r.rating,
                'comment': r.comment,
                'date': r.date,
                'folder': r.folder
            } for r in reviews]
            cache.set(cache_key, reviews_data, timeout=300)  # 5 minute cache
    except Exception as e:
        logger.error(f"Error loading reviews: {e}")

    return render_template('admin_dashboard.html',
                           total_files=total_files,
                           total_images=total_images,
                           total_videos=total_videos,
                           total_size_gb=round(total_size / (1024**3), 2),
                           reviews=reviews_data[:10],
                           has_more=(len(reviews_data) > 10))

@app.route('/admin/all-reviews')
def all_reviews():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    reviews_data = []
    try:
        # 🚀 OPTIMIZARE: Cache pentru toate reviews (5 minute)
        cache_key = 'all_reviews_data'
        reviews_data = cache.get(cache_key)
        if reviews_data is None:
            reviews = Review.query.filter(Review.comment != None, Review.comment != '').order_by(Review.id.desc()).all()
            reviews_data = [{
                'id': r.id,
                'name': r.name,
                'email': r.email,
                'rating': r.rating,
                'comment': r.comment,
                'date': r.date,
                'folder': r.folder
            } for r in reviews]
            cache.set(cache_key, reviews_data, timeout=300)  # 5 minute cache
    except Exception as e:
        logger.error(f"Error loading reviews: {e}")
    return render_template('all_reviews.html', reviews=reviews_data)

@app.route('/admin/review/<int:review_id>')
def view_review_fullscreen(review_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        review = Review.query.get(review_id)
        if not review:
            return "Review not found", 404
        
        review_data = {
            'id': review.id,
            'name': review.name,
            'email': review.email,
            'rating': review.rating,
            'comment': review.comment,
            'date': review.date,
            'folder': review.folder
        }
        return render_template('review_fullscreen.html', review=review_data)
    except Exception as e:
        logger.error(f"Error loading review: {e}")
        return "Error loading review", 500

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # Permite maxim 5 încercări de logare pe minut per IP!
def admin_login():
    if request.method == 'POST' and request.form.get('password') == ADMIN_PASSWORD:
        session['is_admin'] = True
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/upload', methods=['GET', 'POST'])
def admin_upload():
    # <- Aici sunt 4 spații
    
    if request.method == 'POST':
        # <- Aici sunt 8 spații
        folder = secure_filename(request.form.get('folder_name', 'uploads'))
        base_dir = get_base_dir()
        target = os.path.join(base_dir, folder)
        # ... restul codului ...
        folder = secure_filename(request.form.get('folder_name', 'uploads'))
        base_dir = get_base_dir()
        target = os.path.join(base_dir, folder)
        os.makedirs(target, exist_ok=True)

        # 1. ADAUGĂ FOLDERUL NOU ÎN WHITELIST (ca să nu fie ascuns)
        volume_name = os.path.basename(base_dir) if base_dir.startswith('/Volumes/') else None
        if volume_name:
            selected_folders_config = load_selected_folders()
            if volume_name in selected_folders_config:
                if folder not in selected_folders_config[volume_name]:
                    selected_folders_config[volume_name].append(folder)
                    save_selected_folders(selected_folders_config)

        uploaded_files = []
        for file in request.files.getlist('files'):
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(target, filename)
                file.save(file_path)
                uploaded_files.append((filename, file_path))

        # 2. ȘTERGE CACHE-UL SERVERULUI IMEDIAT
        cache.delete(f"media_list::{folder}::{base_dir}")

        # Generare thumbnails în background
        threading.Thread(target=generate_thumbs_for_folder, args=(target,), daemon=True).start()

         

        flash(f"{len(uploaded_files)} fișiere încărcate cu succes.", "success")
        return redirect(url_for('gallery', folder_name=folder))

    return render_template('admin_upload.html')

@app.route('/admin/folder-security', methods=['GET', 'POST'])
def admin_folder_security():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    security = load_folder_security()
    base = get_base_dir()
    
    # Obține lista tuturor folderelor (inclusiv subfoldere)
    all_folders = []
    if os.path.exists(base):
        for root, dirs, _ in os.walk(base):
            dirs[:] = sorted([d for d in dirs if _is_visible_folder(d)])
            rel_root = os.path.relpath(root, base)
            for folder in dirs:
                rel = folder if rel_root == '.' else os.path.join(rel_root, folder).replace('\\', '/')
                all_folders.append(rel)
    
    # Formează lista de foldere cu status-ul lor
    folders_status = []
    for folder in all_folders:
        folder_data = security.get(folder, {})
        folders_status.append({
            'name': folder,
            'is_protected': folder_data.get('is_protected', False),
            'access_key': folder_data.get('access_key', ''),
            'created': folder_data.get('created', '')
        })
    
    if request.method == 'POST':
        action = request.form.get('action')
        folder = request.form.get('folder')
        
        if action == 'protect' and folder:
            new_key = generate_access_key()
            security[folder] = {
                'is_protected': True,
                'access_key': new_key,
                'created': datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            save_folder_security(security)
            return jsonify({"status": "success", "access_key": new_key})
        
        elif action == 'unprotect' and folder:
            try:
                folder_security = FolderSecurity.query.filter_by(folder_name=folder).first()
                if folder_security:
                    db.session.delete(folder_security)
                    db.session.commit()
                    cache.delete('folder_security_db_v1')
                    if has_request_context() and hasattr(g, '_folder_security_cache'):
                        delattr(g, '_folder_security_cache')
            except Exception as e:
                logger.error(f"Error unprotecting folder: {e}")
                db.session.rollback()
            return jsonify({"status": "success"})
        
        elif action == 'regenerate' and folder:
            if folder in security:
                new_key = generate_access_key()
                security[folder]['access_key'] = new_key
                security[folder]['regenerated'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                save_folder_security(security)
                return jsonify({"status": "success", "access_key": new_key})
        
        return jsonify({"status": "error"})
    
    return render_template('admin_folder_security.html', folders=folders_status)

@app.route('/admin/storage', methods=['GET', 'POST'])
def admin_storage():
    """Management pentru dispozitive de stocare externe"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    global EXTERNAL_HDD
    selected_folders_config = load_selected_folders()
    
    current_volumes = get_current_volumes()
    cache_key = f"admin_storage_volumes::{','.join(sorted(current_volumes))}"
    volumes_info = cache.get(cache_key) if request.method == 'GET' else None

    if volumes_info is None:
        volumes_info = []
        for volume in sorted(current_volumes):
            if volume in ['media', 'Macintosh HD']:
                continue

            volume_path = os.path.join('/Volumes', volume)
            if os.path.isdir(volume_path):
                # Calculează informații despre volum și colectează TOȚI folderele
                total_files = 0
                total_size = 0
                all_folders = []
                preview_files = []

                try:
                    for root, dirs, files in os.walk(volume_path):
                        # Exclude hidden directories
                        dirs[:] = [d for d in dirs if not d.startswith('.')]

                        rel_root = os.path.relpath(root, volume_path)
                        if rel_root != '.' and rel_root not in ['.']:
                            all_folders.append(rel_root.replace('\\', '/'))

                        for f in files:
                            if f.startswith('.'):
                                continue

                            total_files += 1
                            file_path = os.path.join(root, f)
                            try:
                                total_size += os.path.getsize(file_path)
                            except Exception:
                                pass

                            # Colectează fișiere pentru preview (max 10)
                            if len(preview_files) < 10:
                                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv')):
                                    rel_path = os.path.relpath(file_path, volume_path)
                                    preview_files.append({
                                        'name': f,
                                        'path': rel_path,
                                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                                        'type': 'video' if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')) else 'image'
                                    })
                except Exception:
                    pass

                # Determină dacă volumul este atașat
                current_external_hdd = load_external_hdd()
                is_attached = (current_external_hdd == volume_path)
                print(f"🔍 Volum {volume}: path={volume_path}, EXTERNAL_HDD={current_external_hdd}, is_attached={is_attached}")

                # Obține folderele selectate pentru acest volum
                selected_folders = selected_folders_config.get(volume, [])

                volumes_info.append({
                    'name': volume,
                    'path': volume_path,
                    'is_attached': is_attached,
                    'total_files': total_files,
                    'total_size_gb': round(total_size / (1024**3), 2) if total_size > 0 else 0,
                    'folders': sorted(set(all_folders)),
                    'selected_folders': selected_folders,
                    'preview_files': preview_files,
                    'has_content': total_files > 0
                })
        if request.method == 'GET':
            cache.set(cache_key, volumes_info, timeout=30)
    
    if request.method == 'POST':
        action = request.form.get('action')
        volume_name = request.form.get('volume')
        
        if action == 'attach' and volume_name:
            volume_path = os.path.join('/Volumes', volume_name)
            if os.path.exists(volume_path):
                save_external_hdd(volume_path)
                
                # Pentru volume noi, selectează implicit toate folderele
                selected_folders_config = load_selected_folders()
                if volume_name not in selected_folders_config:
                    # Listează toate folderele din volum
                    all_folders = []
                    for root, dirs, _ in os.walk(volume_path):
                        dirs[:] = [d for d in dirs if _is_visible_folder(d)]
                        rel_root = os.path.relpath(root, volume_path)
                        for folder in dirs:
                            rel = folder if rel_root == '.' else os.path.join(rel_root, folder).replace('\\', '/')
                            all_folders.append(rel)
                    selected_folders_config[volume_name] = all_folders
                    save_selected_folders(selected_folders_config)
                    print(f"✅ Selectate implicit {len(all_folders)} foldere pentru volumul nou: {volume_name}")
                
                # Generează cache pentru volumul nou în contextul aplicației
                def _generate_cache():
                    with app.app_context():
                        generate_cache_for_attached_volume()
                threading.Thread(target=_generate_cache, daemon=True).start()
                flash(f"✅ Volumul '{volume_name}' a fost atașat cu succes!", "success")
        
        elif action == 'detach':
            EXTERNAL_HDD = LOCAL_FOLDER if os.path.exists(LOCAL_FOLDER) else STRUCTURED_CACHE
            save_external_hdd(EXTERNAL_HDD)
            flash("✅ Volumul a fost detașat. Se folosește stocarea locală.", "info")
        
        elif action == 'select_folders' and volume_name:
            # Salvează folderele selectate pentru volumul respectiv
            selected = request.form.getlist('selected_folders[]')
            selected_folders_config[volume_name] = selected
            if save_selected_folders(selected_folders_config):
                flash(f"✅ {len(selected)} foldere selectate pentru '{volume_name}'", "success")
            else:
                flash("❌ Eroare la salvarea selecției", "error")
        cache.delete(cache_key)
        return redirect(url_for('admin_storage'))
    return render_template('admin_storage.html', volumes=volumes_info, current_storage=get_base_dir())

@app.route('/unlock/<path:folder_name>', methods=['GET', 'POST'])
def unlock_folder(folder_name):
    """Pagina de unlock pentru foldere protejate"""
    folder_name = normalize_folder_name(folder_name)
    if folder_name is None:
        return "Invalid folder", 400

    if not is_folder_protected(folder_name):
        return redirect(url_for('gallery', folder_name=folder_name))
    
    if request.method == 'POST':
        access_key = request.form.get('access_key', '')
        security = load_folder_security()
        correct_key = security.get(folder_name, {}).get('access_key')
        
        if access_key == correct_key:
            response = make_response(redirect(url_for('gallery', folder_name=folder_name)))
            set_folder_access_cookie(response, folder_name, access_key)
            return response
        else:
            return render_template('unlock.html', folder_name=folder_name, error=gettext("Incorrect access key!"))
    
    return render_template('unlock.html', folder_name=folder_name)

@app.route('/share/<path:folder_name>')
def share_folder(folder_name):
    """Share link - acceptă cheia direct în URL și setează cookie"""
    folder_name = normalize_folder_name(folder_name)
    if folder_name is None:
        return "Invalid folder", 400

    access_key = request.args.get('key', '')
    
    if not is_folder_protected(folder_name):
        return redirect(url_for('gallery', folder_name=folder_name))
    
    security = load_folder_security()
    correct_key = security.get(folder_name, {}).get('access_key')
    
    if access_key == correct_key:
        response = make_response(redirect(url_for('gallery', folder_name=folder_name)))
        set_folder_access_cookie(response, folder_name, access_key)
        return response
    else:
        return render_template('unlock.html', folder_name=folder_name, error=gettext("The link has expired or is invalid!"))

@app.route('/api/unlock-folder', methods=['POST'])
def api_unlock_folder():
    """API endpoint pentru unlock foldere"""
    data = request.json or {}
    folder_name = normalize_folder_name(data.get('folder')) if data.get('folder') else None
    access_key = data.get('access_key', '').strip()
    
    matched_folder = find_folder_by_access_key(access_key)
    if matched_folder:
        response = make_response(jsonify({"status": "success", "folder": matched_folder}))
        set_folder_access_cookie(response, matched_folder, access_key)
        return response

    if folder_name:
        if not is_folder_protected(folder_name):
            return jsonify({"status": "error", "message": gettext("Folder not protected")}), 400
        return jsonify({"status": "error", "message": gettext("Invalid access key")}), 401

    return jsonify({"status": "error", "message": "Invalid access key"}), 401

@app.route('/api/save_review', methods=['POST'])
def save_review():
    data = request.json or {}
    name = (data.get('name', '') or data.get('nume', '')).strip()
    email = (data.get('email', '') or data.get('contact', '')).strip()
    comment = (data.get('comment') or data.get('mesaj') or '').strip()
    folder = (data.get('folder') or data.get('proiect') or '').strip()
    rating = data.get('rating', 5)
    
    # Validare rating
    try:
        rating = max(1, min(5, int(rating)))
    except:
        rating = 5

    if not name or not email or not comment or not folder:
        logger.warning(f"Invalid review submission: name={name!r}, email={email!r}, comment={comment!r}, folder={folder!r}")
        return jsonify({"status": "error", "message": gettext("Please complete all review fields.")}), 400

    try:
        review = Review(
            name=name,
            email=email,
            rating=rating,
            comment=comment,
            date=datetime.now().strftime("%d/%m/%Y %H:%M"),
            folder=folder
        )
        db.session.add(review)
        db.session.commit()
        
        # 🚀 OPTIMIZARE: Șterge cache-ul pentru reviews după adăugare
        cache.delete('admin_reviews_data')
        cache.delete('all_reviews_data')
        
        # Salvează și în JSON pentru backup
        review_json = {
            'name': name,
            'email': email,
            'rating': rating,
            'comment': comment,
            'date': review.date,
            'folder': folder
        }
        
        # Citește JSON-ul existent
        reviews_json_file = 'reviews.json'
        existing_reviews = []
        if os.path.exists(reviews_json_file):
            try:
                with open(reviews_json_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        existing_reviews = json.loads(content)
            except:
                existing_reviews = []
        
        # Adaugă recenzia nouă
        existing_reviews.append(review_json)
        
        # Scrie JSON-ul actualizat
        with open(reviews_json_file, 'w') as f:
            json.dump(existing_reviews, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Review saved: name={name}, folder={folder}, rating={rating}")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error saving review: {e}")
        db.session.rollback()
        return jsonify({"status": "error", "message": gettext("Failed to save review")}), 500

def _translate_best_path(p):
    if not p:
        return p
    parts = p.split('/', 1)
    if parts[0].lower() == 'best':
        return parts[1] if len(parts) > 1 else ''
    return p


@app.route('/media/')
def serve_media():
    p = request.args.get('p', '')
    if not p:
        return "Not Found", 404

    base = get_base_dir()
    real_p = os.path.join(base, p)

    if not is_safe_path(base, real_p) or not os.path.exists(real_p):
        if base != LOCAL_FOLDER:
            local_p = os.path.join(LOCAL_FOLDER, p)
            if is_safe_path(LOCAL_FOLDER, local_p) and os.path.exists(local_p):
                response = send_file(local_p)
                response.headers['Cache-Control'] = 'public, max-age=2592000, stale-while-revalidate=86400'
                return response
        return "Not Found", 404

    media_folder = os.path.dirname(p).replace('\\', '/')
    if media_folder and not user_has_access(media_folder):
        return "Forbidden", 403

    response = send_file(real_p)
    response.headers['Cache-Control'] = 'public, max-age=2592000, stale-while-revalidate=86400'
    return response

@app.route('/thumb/')
def serve_thumb():
    p = request.args.get('p', '')
    if not p:
        return "Not Found", 404
    # === SPECIAL: static/best ===
    if p.lower().startswith('best/') or p.lower() == 'best':
        fname = p[5:] if p.lower().startswith('best/') else ''
        orig_path = os.path.join(BEST_STATIC_FOLDER, fname)
        cache_dir = os.path.join(STRUCTURED_CACHE, 'best')
        
        requested_variant = request.args.get('variant', 'grid').lower()
        allowed_variants = {'grid', 'grid_md', 'grid_sm', 'grid_xs', 'lightbox', 'lqip'}
        variant = 'grid' if requested_variant in {'grid_md', 'grid_sm', 'grid_xs'} else (requested_variant if requested_variant in allowed_variants else 'grid')
        
        requested_fmt = request.args.get('fmt', 'auto').lower()
        accept_header = (request.headers.get('Accept') or '').lower()
        can_use_avif = THUMB_AVIF_SUPPORTED and not is_video(fname)
        
        if requested_fmt == 'avif' and can_use_avif:
            image_format = 'avif'
        elif requested_fmt == 'webp':
            image_format = 'webp'
        elif requested_fmt == 'auto' and can_use_avif and 'image/avif' in accept_header:
            image_format = 'avif'
        else:
            image_format = 'webp'
        
        stem = os.path.splitext(fname)[0]
        cached_path = os.path.join(cache_dir, f"{stem}{_thumb_variant_suffix(variant, image_format)}")
        
        if os.path.exists(cached_path):
            response = send_file(cached_path)
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            if requested_fmt == 'auto':
                response.headers['Vary'] = 'Accept'
            return response
        
        if not is_offline_mode() and os.path.exists(orig_path):
            os.makedirs(cache_dir, exist_ok=True)
            if generate_fast_thumb(orig_path, cached_path, variant, image_format=image_format):
                response = send_file(cached_path)
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                if requested_fmt == 'auto':
                    response.headers['Vary'] = 'Accept'
                return response
        
        if image_format == 'avif':
            fallback_path = os.path.join(cache_dir, f"{stem}{_thumb_variant_suffix(variant, 'webp')}")
            if not is_offline_mode() and os.path.exists(orig_path):
                os.makedirs(cache_dir, exist_ok=True)
                if generate_fast_thumb(orig_path, fallback_path, variant, image_format='webp'):
                    response = send_file(fallback_path)
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                    if requested_fmt == 'auto':
                        response.headers['Vary'] = 'Accept'
                    return response
        return "Not Found", 404

    # Normal path pentru restul folderelor
    requested_path = _translate_best_path(p)
    folder, fname = os.path.split(requested_path)
    folder = folder.replace('\\', '/')
    if folder and not user_has_access(folder):
        return "Forbidden", 403

    orig_path = os.path.join(get_base_dir(), requested_path)
    best_cache_folder = None


    requested_variant = request.args.get('variant', 'grid').lower()
    allowed_variants = {'grid', 'grid_md', 'grid_sm', 'grid_xs', 'lightbox', 'lqip'}
    if requested_variant in {'grid_md', 'grid_sm', 'grid_xs'}:
        variant = 'grid'
    else:
        variant = requested_variant if requested_variant in allowed_variants else 'grid'

    requested_fmt = request.args.get('fmt', 'auto').lower()
    accept_header = (request.headers.get('Accept') or '').lower()
    can_use_avif = THUMB_AVIF_SUPPORTED and (not is_video(fname))

    if requested_fmt == 'avif' and can_use_avif:
        image_format = 'avif'
    elif requested_fmt == 'webp':
        image_format = 'webp'
    elif requested_fmt == 'auto' and can_use_avif and 'image/avif' in accept_header:
        image_format = 'avif'
    else:
        image_format = 'webp'

    if best_cache_folder:
        stem = os.path.splitext(fname)[0]
        cached_path = os.path.join(best_cache_folder, f"{stem}{_thumb_variant_suffix(variant, image_format)}")
    else:
        cached_path = _thumb_cache_path(folder, fname, variant, image_format=image_format)

    if os.path.exists(cached_path):
        response = send_file(cached_path)
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        if requested_fmt == 'auto':
            response.headers['Vary'] = 'Accept'
        return response

    if not is_offline_mode():
        os.makedirs(os.path.dirname(cached_path), exist_ok=True)
        if os.path.exists(orig_path) and generate_fast_thumb(orig_path, cached_path, variant, image_format=image_format):
            response = send_file(cached_path)
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            if requested_fmt == 'auto':
                response.headers['Vary'] = 'Accept'
            return response

    if image_format == 'avif':
        fallback_path = cached_path.replace('.avif', '.webp') if best_cache_folder else _thumb_cache_path(folder, fname, variant, image_format='webp')
        os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
        if os.path.exists(orig_path) and generate_fast_thumb(orig_path, fallback_path, variant, image_format='webp'):
            response = send_file(fallback_path)
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            if requested_fmt == 'auto':
                response.headers['Vary'] = 'Accept'
            return response
    return "Not Found", 404


@app.route('/api/gallery-items/<path:folder_name>')
def api_gallery_items(folder_name):
    folder_name = normalize_folder_name(folder_name)
    if folder_name is None:
        return jsonify({"status": "error", "message": "Invalid folder"}), 400

    # === SPECIAL: static/best ===
    if folder_name.lower() == 'best':
        all_files = list_folder_media('best')
        chunk = all_files  # sau adaugă paginație dacă vrei
        
        items = [
            {
                'name': f,
                'is_video': is_video(f),
                'thumb': url_for('serve_thumb', p=f"best/{f}", fmt='auto'),
                'lqip': url_for('serve_thumb', p=f"best/{f}", variant='lqip'),
                'lightbox': url_for('serve_thumb', p=f"best/{f}", variant='lightbox', fmt='auto'),
                'media': url_for('serve_media', p=f"best/{f}")
            }
            for f in chunk
        ]
        return jsonify({
            'status': 'ok',
            'offset': 0,
            'limit': len(all_files),
            'total': len(all_files),
            'has_more': False,
            'items': items
        })

    if folder_name == BEST_FOLDER_ALIAS:
        folder_name = ''

    if not user_has_access(folder_name):
        return jsonify({"status": "error", "message": gettext("No access")}), 403

    try:
        offset = max(0, int(request.args.get('offset', 0)))
        limit = max(1, min(10000, int(request.args.get('limit', 24))))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid pagination"}), 400

    all_files = list_folder_media(folder_name)
    chunk = all_files[offset:offset + limit]

    path_prefix = f"{folder_name}/" if folder_name else ""

    # Client-side cache key for this exact slice.
    etag_payload = {
        'folder': folder_name,
        'offset': offset,
        'limit': limit,
        'total': len(all_files),
        'chunk': chunk
    }
    etag_value = hashlib.sha1(
        json.dumps(etag_payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    ).hexdigest()

    incoming_etag = (request.headers.get('If-None-Match') or '').strip('"')
    if incoming_etag == etag_value:
        response = make_response('', 304)
        response.headers['ETag'] = f'"{etag_value}"'
        response.headers['Cache-Control'] = 'private, max-age=60, stale-while-revalidate=300'
        return response

    items = [
        {
            'name': f,
            'is_video': is_video(f),
            'thumb': url_for('serve_thumb', p=f"{path_prefix}{f}", fmt='auto'),
            'lqip': url_for('serve_thumb', p=f"{path_prefix}{f}", variant='lqip'),
            'lightbox': url_for('serve_thumb', p=f"{path_prefix}{f}", variant='lightbox', fmt='auto'),
            'media': url_for('serve_media', p=f"{path_prefix}{f}")
        }
        for f in chunk
    ]

    response = jsonify({
        'status': 'ok',
        'offset': offset,
        'limit': limit,
        'total': len(all_files),
        'has_more': (offset + limit) < len(all_files),
        'items': items
    })
    response.headers['ETag'] = f'"{etag_value}"'
    response.headers['Cache-Control'] = 'private, max-age=0, stale-while-revalidate=300'
    return response


@app.route('/admin/optimize-media', methods=['POST'])
def admin_optimize_media():
    if not session.get('is_admin'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    payload = request.json or {}
    force = bool(payload.get('force', False))

    def _worker():
        with app.app_context():
            optimize_existing_media_assets(force=force)

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({'status': 'started', 'force': force})

@app.route('/download_selection', methods=['POST'])
def download_selection():


    data = request.json
    files, folder = data.get('files', []), normalize_folder_name(data.get('folder', ''))
    if folder is None:
        return jsonify({"status": "error", "message": "Invalid folder"}), 400

    if is_folder_protected(folder) and not user_has_access(folder):
        return jsonify({"status": "error", "message": gettext("No access")}), 403

    if folder.lower() == 'best':
        base = BEST_STATIC_FOLDER
        folder_path = ''
    else:
        base = get_base_dir()
        folder_path = folder

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            path = os.path.join(base, folder_path, f)
            if os.path.exists(path) and is_safe_path(base, path):
                zf.write(path, f)
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='selectie.zip')

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('welcome'))

@app.after_request
def add_dynamic_no_cache_headers(response):
    # Nu forța no-cache pe media/thumb/api paginat ca să permitem performanță bună la galerie.
    cache_friendly_prefixes = ('/static/', '/media/', '/thumb/', '/api/gallery-items/')
    if not request.path.startswith(cache_friendly_prefixes):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


start_media_optimization_warmup()

# Pornește monitorizarea volumelor DOAR în modul dezvoltare/debug
if app.debug or app.config.get('ENV') == 'development':
    volume_thread = threading.Thread(target=monitor_volumes, daemon=True)
    volume_thread.start()
else:
    print("ℹ️  Monitorizarea volumelor dezactivată în producție (Gunicorn)")

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
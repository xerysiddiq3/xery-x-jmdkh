from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
from faulthandler import enable as faulthandler_enable
from telegram.ext import Updater as tgUpdater
from qbittorrentapi import Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from os import remove as osremove, path as ospath, environ
from requests import get as rget
from json import loads as jsonloads
from subprocess import Popen, run as srun, check_output
from time import sleep, time
from threading import Thread, Lock
from dotenv import load_dotenv
from pyrogram import Client, enums
from asyncio import get_event_loop
from megasdkrestclient import MegaSdkRestClient, errors as mega_err

main_loop = get_event_loop()

faulthandler_enable()

setdefaulttimeout(600)

botStartTime = time()

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[FileHandler('log.txt'), StreamHandler()],
                    level=INFO)

LOGGER = getLogger(__name__)

load_dotenv('config.env', override=True)

NETRC_URL = environ.get('NETRC_URL', '')
if len(NETRC_URL) != 0:
    try:
        res = rget(NETRC_URL)
        if res.status_code == 200:
            with open('.netrc', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download .netrc {res.status_code}")
    except Exception as e:
        log_error(f"NETRC_URL: {e}")

TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = None if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

PORT = environ.get('PORT')
Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{PORT}", shell=True)
srun(["firefox", "-d", "--profile=."])
if not ospath.exists('.netrc'):
    srun(["touch", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "600", ".netrc"])
trackers = check_output("curl -Ns https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/all.txt https://ngosang.github.io/trackerslist/trackers_all_http.txt https://newtrackon.com/api/all https://raw.githubusercontent.com/hezhijie0327/Trackerslist/main/trackerslist_tracker.txt | awk '$0' | tr '\n\n' ','", shell=True).decode('utf-8').rstrip(',')
with open("a2c.conf", "a+") as a:
    if TORRENT_TIMEOUT is not None:
        a.write(f"bt-stop-timeout={TORRENT_TIMEOUT}\n")
    a.write(f"bt-tracker=[{trackers}]")
srun(["chrome", "--conf-path=/usr/src/app/a2c.conf"])
alive = Popen(["python3", "alive.py"])
sleep(0.5)

Interval = []
QbInterval = []
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []

def getConfig(name: str):
    return environ[name]

try:
    if bool(getConfig('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

aria2 = ariaAPI(
    ariaClient(
        host="http://localhost",
        port=6800,
        secret="",
    )
)

def get_client():
    return qbClient(host="localhost", port=8090, VERIFY_WEBUI_CERTIFICATE=False, REQUESTS_ARGS={'timeout': (30, 60)})

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# key: rss_title
# value: [rss_feed, last_link, last_title, filter]
rss_dict = {}
# key: msg_id
# value: [listener, extras, isNeedEngine, time_out]
btn_listener = {}

AS_DOC_USERS = set()
AS_MEDIA_USERS = set()
EXTENSION_FILTER = {'.aria2'}

try:
    BOT_TOKEN = getConfig('BOT_TOKEN')
    parent_id = getConfig('GDRIVE_FOLDER_ID')
    DOWNLOAD_DIR = getConfig('DOWNLOAD_DIR')
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = DOWNLOAD_DIR + '/'
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig('DOWNLOAD_STATUS_UPDATE_INTERVAL'))
    OWNER_ID = int(getConfig('OWNER_ID'))
    AUTO_DELETE_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_MESSAGE_DURATION'))
    TELEGRAM_API = getConfig('TELEGRAM_API')
    TELEGRAM_HASH = getConfig('TELEGRAM_HASH')
except:
    log_error("One or more env variables missing! Exiting now")
    exit(1)

aid = environ.get('AUTHORIZED_CHATS', '')
aid = aid.split()
AUTHORIZED_CHATS = {int(_id.strip()) for _id in aid}
aid = environ.get('SUDO_USERS', '')
aid = aid.split()
SUDO_USERS = {int(_id.strip()) for _id in aid}
fx = environ.get('EXTENSION_FILTER', '')
if len(fx) > 0:
    fx = fx.split()
    for x in fx:
        EXTENSION_FILTER.add(x.strip().lower())


IS_PREMIUM_USER = False
USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
if len(USER_SESSION_STRING) == 0:
    log_info("Creating client from BOT_TOKEN")
    app = Client(name='pyrogram', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML, no_updates=True)
else:
    log_info("Creating client from USER_SESSION_STRING")
    app = Client(name='pyrogram', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
    with app:
        IS_PREMIUM_USER = app.me.is_premium

RSS_USER_SESSION_STRING = environ.get('RSS_USER_SESSION_STRING', '')
if len(RSS_USER_SESSION_STRING) == 0:
    rss_session = None
else:
    log_info("Creating client from RSS_USER_SESSION_STRING")
    rss_session = Client(name='rss_session', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=RSS_USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)

def aria2c_init():
    try:
        log_info("Initializing Aria2c")
        link = "https://linuxmint.com/torrents/lmde-5-cinnamon-64bit.iso.torrent"
        dire = DOWNLOAD_DIR.rstrip("/")
        aria2.add_uris([link], {'dir': dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(20)
        for download in downloads:
            aria2.remove([download], force=True, files=True)
    except Exception as e:
        log_error(f"Aria2c initializing error: {e}")
Thread(target=aria2c_init).start()

MEGA_KEY = environ.get('MEGA_API_KEY', '')
if len(MEGA_KEY) == 0:
    log_warning('MEGA API KEY not provided!')
    MEGA_KEY = None

MEGA_EMAIL_ID = environ.get('MEGA_EMAIL_ID', '')
MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
    log_warning('MEGA Credentials not provided!')
    MEGA_EMAIL_ID = None
    MEGA_PASSWORD = None

if MEGA_KEY is not None:
    # Start megasdkrest binary
    Popen(["megasdkrest", "--apikey", MEGA_KEY])
    sleep(3)  # Wait for the mega server to start listening
    mega_client = MegaSdkRestClient('http://localhost:6090')
    try:
        MEGA_USERNAME = getConfig('MEGA_EMAIL_ID')
        MEGA_PASSWORD = getConfig('MEGA_PASSWORD')
        if len(MEGA_USERNAME) > 0 and len(MEGA_PASSWORD) > 0:
            try:
                mega_client.login(MEGA_USERNAME, MEGA_PASSWORD)
            except mega_err.MegaSdkRestClientException as e:
                log_error(e.message['message'])
                exit(0)
        else:
            log_info("Mega API KEY provided but credentials not provided. Starting mega in anonymous mode!")
    except:
        log_info("Mega API KEY provided but credentials not provided. Starting mega in anonymous mode!")
else:
    sleep(1.5)

DB_URI = environ.get('DATABASE_URL', '')
if len(DB_URI) == 0:
    DB_URI = None

MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
if len(LEECH_SPLIT_SIZE) == 0 or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
    LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
else:
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

DUMP_CHAT = environ.get('DUMP_CHAT', '')
DUMP_CHAT = None if len(DUMP_CHAT) == 0 else int(DUMP_CHAT)
STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
STATUS_LIMIT = None if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)
UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
if len(UPTOBOX_TOKEN) == 0:
    UPTOBOX_TOKEN = None

INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = None
    INDEX_URLS.append(None)
else:
    INDEX_URLS.append(INDEX_URL)

SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = None

SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)
RSS_COMMAND = environ.get('RSS_COMMAND', '')
if len(RSS_COMMAND) == 0:
    RSS_COMMAND = None

CMD_INDEX = environ.get('CMD_INDEX', '')

RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
RSS_CHAT_ID = None if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)
RSS_DELAY = environ.get('RSS_DELAY', '')
RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)
BASE_URL = environ.get('BASE_URL_OF_BOT', '').rstrip("/")
if len(BASE_URL) == 0:
    log_warning('BASE_URL_OF_BOT not provided!')
    BASE_URL = None

CUSTOM_FILENAME = environ.get('CUSTOM_FILENAME', '')
if len(CUSTOM_FILENAME) == 0:
    CUSTOM_FILENAME = None

SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = None
else:
    SEARCH_PLUGINS = jsonloads(SEARCH_PLUGINS)

INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '')
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'

STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '')
STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

VIEW_LINK = environ.get('VIEW_LINK', '')
VIEW_LINK = VIEW_LINK.lower() == 'true'

IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', '')
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', '')
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

WEB_PINCODE = environ.get('WEB_PINCODE', '')
WEB_PINCODE = WEB_PINCODE.lower() == 'true'

IGNORE_PENDING_REQUESTS = environ.get('IGNORE_PENDING_REQUESTS', '')
IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == 'true'

AS_DOCUMENT = environ.get('AS_DOCUMENT', '')
AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

EQUAL_SPLITS = environ.get('EQUAL_SPLITS', '')
EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

TOKEN_PICKLE_URL = environ.get('TOKEN_PICKLE_URL', '')
if len(TOKEN_PICKLE_URL) != 0:
    try:
        res = rget(TOKEN_PICKLE_URL)
        if res.status_code == 200:
            with open('token.pickle', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download token.pickle, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"TOKEN_PICKLE_URL: {e}")

ACCOUNTS_ZIP_URL = environ.get('ACCOUNTS_ZIP_URL', '')
if len(ACCOUNTS_ZIP_URL) != 0:
    try:
        res = rget(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
            srun(["unzip", "-q", "-o", "accounts.zip"])
            srun(["chmod", "-R", "777", "accounts"])
            osremove("accounts.zip")
        else:
            log_error(f"Failed to download accounts.zip, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"ACCOUNTS_ZIP_URL: {e}")

MULTI_SEARCH_URL = environ.get('MULTI_SEARCH_URL', '')
if len(MULTI_SEARCH_URL) != 0:
    try:
        res = rget(MULTI_SEARCH_URL)
        if res.status_code == 200:
            with open('drive_folder', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download drive_folder, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"MULTI_SEARCH_URL: {e}")

YT_COOKIES_URL = environ.get('YT_COOKIES_URL', '')
if len(YT_COOKIES_URL) != 0:
    try:
        res = rget(YT_COOKIES_URL)
        if res.status_code == 200:
            with open('cookies.txt', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download cookies.txt, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"YT_COOKIES_URL: {e}")

DRIVES_NAMES.append("Main")
DRIVES_IDS.append(parent_id)
if ospath.exists('drive_folder'):
    with open('drive_folder', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVES_IDS.append(temp[1])
            DRIVES_NAMES.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
                INDEX_URLS.append(None)
CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = None if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
MEGA_LIMIT = None if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
STORAGE_THRESHOLD = None if len(STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
LEECH_LIMIT = None if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

PLAYLIST_LIMIT = environ.get('PLAYLIST_LIMIT', '')
PLAYLIST_LIMIT = None if len(PLAYLIST_LIMIT) == 0 else int(PLAYLIST_LIMIT)

BUTTON_FIVE_NAME = environ.get('BUTTON_FIVE_NAME', '')
BUTTON_FIVE_URL = environ.get('BUTTON_FIVE_URL', '')
if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None

BUTTON_SIX_NAME = environ.get('BUTTON_SIX_NAME', '')
BUTTON_SIX_URL = environ.get('BUTTON_SIX_URL', '')
if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None

GDTOT_CRYPT = environ.get('GDTOT_CRYPT', '')
if len(GDTOT_CRYPT) == 0:
    GDTOT_CRYPT = None

SHARER_EMAIL = environ.get('SHARER_EMAIL', '')
SHARER_PASS = environ.get('SHARER_PASS', '')
if len(SHARER_EMAIL) == 0 or len(SHARER_PASS) == 0:
    SHARER_EMAIL = None
    SHARER_PASS = None

ENABLE_CHAT_RESTRICT = environ.get('ENABLE_CHAT_RESTRICT', '')
ENABLE_CHAT_RESTRICT = ENABLE_CHAT_RESTRICT.lower() == 'true'

ENABLE_MESSAGE_FILTER = environ.get('ENABLE_MESSAGE_FILTER', '')
ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER.lower() == 'true'

STOP_DUPLICATE_TASKS = environ.get('STOP_DUPLICATE_TASKS', '')
STOP_DUPLICATE_TASKS = STOP_DUPLICATE_TASKS.lower() == 'true'
SHARER_DRIVE_SITE = environ.get('SHARER_DRIVE_SITE', '')
if len(SHARER_DRIVE_SITE) == 0:
    SHARER_DRIVE_SITE = None
ENABLE_SHARER_LIST = environ.get('ENABLE_SHARER_LIST', '')
ENABLE_SHARER_LIST = ENABLE_SHARER_LIST.lower() == 'true'

DISABLE_DRIVE_LINK = environ.get('DISABLE_DRIVE_LINK', '')
DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

SHORTENER = environ.get('SHORTENER', '')
SHORTENER_API = environ.get('SHORTENER_API', '')
if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
    SHORTENER = None
    SHORTENER_API = None
FSUB_IDS = set()
fsubid = environ.get('FSUB_IDS', '')
for f_id in fsubid.split():
    if not f_id.startswith('-100'):
        continue
    try:
        FSUB_IDS.add(int(f_id))
    except:
        pass
updater = tgUpdater(token=BOT_TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 15})
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
botname = bot.username
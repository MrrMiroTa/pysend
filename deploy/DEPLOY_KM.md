# របៀប Deploy GPS Expiry Notifier ឡើង Web (Ubuntu VPS)

កម្មវិធីនេះមាន background thread និងឯកសារ session របស់ Telegram ដូច្នេះត្រូវដំណើរការលើ **VPS** (Ubuntu 22.04/24.04, RAM យ៉ាងតិច 1 GB)។
**មិនអាច** ប្រើ Shared hosting / cPanel / Vercel / Netlify បានទេ។

អ្វីដែលត្រូវមាន: VPS មួយ, Domain មួយ (ឧ. `notifier.yourdomain.com`) ដែលចង្អុលទៅ IP របស់ VPS (A record), និង `API_ID` / `API_HASH` ពី https://my.telegram.org

---
## ១. រៀបចំ Server
```bash
ssh root@IP_របស់_SERVER
apt update && apt upgrade -y
apt install -y python3-venv python3-pip unzip nginx certbot python3-certbot-nginx mariadb-server fonts-khmeros ufw
adduser --system --group --home /opt/gps_notifier gps
```

## ២. បង្កើត Database (MariaDB / MySQL)
```bash
mysql
```
```sql
CREATE DATABASE gps_notifier CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'gps'@'localhost' IDENTIFIED BY 'ពាក្យសម្ងាត់ខ្លាំង';
GRANT ALL ON gps_notifier.* TO 'gps'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```
> `utf8mb4` ចាំបាច់ ដើម្បីរក្សាអក្សរខ្មែរបានត្រឹមត្រូវ។
> ចង់ប្រើ SQLite (ងាយបំផុត មិនបាច់តំឡើងអ្វី) ក៏បាន: ទុក `DATABASE_URL=` ទទេ។

## ៣. ដាក់កូដឡើង Server
ពី computer របស់អ្នក (Windows PowerShell):
```powershell
scp gps_expiry_notifier_web_v13.zip root@IP_របស់_SERVER:/tmp/
```
នៅលើ server:
```bash
cd /opt/gps_notifier && unzip -o /tmp/gps_expiry_notifier_web_v13.zip -d /tmp/gps && cp -r /tmp/gps/gps_notifier/. /opt/gps_notifier/
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export PLAYWRIGHT_BROWSERS_PATH=/opt/gps_notifier/browsers
.venv/bin/playwright install --with-deps chromium     # សម្រាប់បង្កើតរូបតារាង
chown -R gps:gps /opt/gps_notifier
```

## ៤. កំណត់ `.env`
```bash
cp .env.example .env && nano .env
```
ត្រូវបំពេញយ៉ាងហោចណាស់:
```text
SECRET_KEY=          # python3 -c "import secrets;print(secrets.token_hex(32))"
ADMIN_USER=admin                   # ប្រើតែពេលចាប់ផ្តើមលើកដំបូង ដើម្បីបង្កើត admin ទី១
ADMIN_PASSWORD_HASH='scrypt:...'   # .venv/bin/python app.py hash   (ដាក់ក្នុង single quote)
TIMEZONE=Asia/Phnom_Penh           # ឲ្យ Report រាប់ថ្ងៃតាមម៉ោងកម្ពុជា (server ភាគច្រើនជា UTC)
COOKIE_SECURE=1
TRUST_PROXY=1
HOST=127.0.0.1
API_ID=...
API_HASH=...
CONTACT_PHONE=087500502
DATABASE_URL=mysql+pymysql://gps:ពាក្យសម្ងាត់@127.0.0.1:3306/gps_notifier?charset=utf8mb4
```
> បើពាក្យសម្ងាត់មានសញ្ញាពិសេស សូមប្តូរ: `@`→`%40`, `#`→`%23`, `/`→`%2F`, `:`→`%3A`។
```bash
chmod 600 .env
```

## ៥. បង្កើត Table និង Login Telegram (ម្តង)
```bash
sudo -u gps .venv/bin/python scripts/init_db.py                       # បង្កើត table: users, send_log
sudo -u gps .venv/bin/python scripts/login_telegram.py                # បញ្ចូលលេខទូរស័ព្ទ + code
chmod 600 /opt/gps_notifier/sessions/*
```

> Database រក្សាទុកតែ ២ យ៉ាង: **users** (Admin login) និង **send_log** (Report តាមថ្ងៃ)។ បញ្ជីអតិថិជនយកពី Excel តាមប៊ូតុង **Browse file**។
> Admin ទី១ ត្រូវបានបង្កើតដោយស្វ័យប្រវត្តិពី `ADMIN_USER` + `ADMIN_PASSWORD_HASH` ពេលចាប់ផ្តើមលើកដំបូង។ បន្ទាប់មកគ្រប់គ្រងក្នុងផ្ទាំង **Users** (បន្ថែម/កែពាក្យសម្ងាត់/បិទ/លុប)។
> ភ្លេចពាក្យសម្ងាត់? `sudo -u gps .venv/bin/python scripts/create_user.py admin --reset`

## ៦. ដំណើរការជា Service
```bash
cp deploy/gps.service /etc/systemd/system/gps.service
systemctl daemon-reload && systemctl enable --now gps
systemctl status gps            # ត្រូវឃើញ active (running)
journalctl -u gps -f            # មើល log
curl http://127.0.0.1:5000/healthz    # ត្រូវឆ្លើយ: ok
```
> ដំណើរការ **តែ 1 process** ប៉ុណ្ណោះ (កុំបើក gunicorn ច្រើន worker)។

## ៧. Nginx + HTTPS ឥតគិតថ្លៃ
```bash
cp deploy/nginx_gps.conf /etc/nginx/sites-available/gps
nano /etc/nginx/sites-available/gps          # ប្តូរ server_name ជា domain របស់អ្នក
ln -s /etc/nginx/sites-available/gps /etc/nginx/sites-enabled/gps
nginx -t && systemctl reload nginx
certbot --nginx -d notifier.yourdomain.com   # បើក HTTPS
```
បើកទំព័រ `https://notifier.yourdomain.com` ហើយចូលដោយ `ADMIN_USER` + ពាក្យសម្ងាត់។

## ៨. Firewall
```bash
ufw allow OpenSSH && ufw allow 'Nginx Full' && ufw enable
```
Port 5000 និង 3306 មិនបើកចេញក្រៅទេ (កម្មវិធីស្តាប់តែ 127.0.0.1)។

## ៩. Backup រាល់ថ្ងៃ
```bash
crontab -e
0 2 * * * /opt/gps_notifier/deploy/backup.sh
```
Backup រក្សា database និង session ទុក 14 ថ្ងៃនៅ `/var/backups/gps`។ សូមចម្លងចេញទៅកន្លែងផ្សេងម្តងម្កាល។

## ១០. ធ្វើបច្ចុប្បន្នភាពកំណែ
```bash
systemctl stop gps
# ចម្លងឯកសារថ្មីជាន់លើ (កុំជាន់ .env, sessions/, data/)
.venv/bin/pip install -r requirements.txt
systemctl start gps
```

## បញ្ហាដែលតែងជួប
| បញ្ហា | ដំណោះស្រាយ |
|---|---|
| ចូលមិនបាន / "Wrong username or password" | បង្កើត hash ថ្មី ហើយដាក់ក្នុង single quote ក្នុង `.env` |
| "Telegram session not logged in" | ដំណើរការ `scripts/login_telegram.py` ម្តងទៀត (ពេល service ឈប់) |
| តារាងជាអក្សរ (មិនមានរូប) | ដំណើរការ `playwright install --with-deps chromium` ជាមួយ `PLAYWRIGHT_BROWSERS_PATH` |
| អក្សរខ្មែរជាប្រអប់ ឬ `???` | ប្រើ `utf8mb4` ក្នុង DATABASE_URL និងតំឡើង `fonts-khmeros` |
| 502 Bad Gateway | `systemctl status gps` / `journalctl -u gps -n 50` |

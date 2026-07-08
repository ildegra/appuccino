# Appuccino

Appuccino è una piccola web app personale per recensire i bar dove fai colazione.

Prima versione:

- FastAPI + SQLite
- Docker singolo tramite Docker Compose
- login con username/password
- gestione bar
- gestione visite
- categorie, criteri e pesi configurabili
- calcolo voto globale pesato
- export CSV
- interfaccia responsive chiara con accenti caffè/cappuccino

## Deploy consigliato con Portainer da Git

Portainer può deployare uno stack da repository Git e clona l'intero repository prima del deploy. Questo è il modo più comodo per un progetto composto da più file.

### 1. Crea un repository GitHub

1. Vai su GitHub.
2. Crea un nuovo repository, per esempio `appuccino`.
3. Può essere pubblico o privato.
4. Carica tutti i file di questa cartella nel repository.

Struttura attesa:

```text
appuccino/
├── app/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

### 2. Deploy in Portainer

1. Apri Portainer.
2. Vai su **Stacks**.
3. Clicca **Add stack**.
4. Nome stack: `appuccino`.
5. Scegli **Git Repository**.
6. Repository URL: URL del tuo repository GitHub.
7. Reference: `main`.
8. Compose path: `docker-compose.yml`.
9. Se il repository è privato, abilita l'autenticazione e inserisci le credenziali/token.
10. Nella sezione Environment variables imposta almeno:

```text
APP_USERNAME=admin
APP_PASSWORD=una-password-lunga
SECRET_KEY=una-stringa-lunga-casuale
```

11. Clicca **Deploy the stack**.

L'app sarà disponibile su:

```text
http://IP_DEL_RASPBERRY:8033
```

## Esposizione fuori casa

Per usarla fuori casa è meglio esporla dietro reverse proxy HTTPS, ad esempio Nginx Proxy Manager, Cloudflare Tunnel o il reverse proxy che già usi. Non pubblicare direttamente la porta 8033 senza HTTPS.

## Dati e backup

Il database SQLite e gli upload sono salvati nel volume Docker `appuccino_data` montato su `/data` nel container.

File principale:

```text
/data/appuccino.sqlite3
```

Per un backup basta salvare il volume o esportare il database dall'interfaccia.

## Sviluppo futuro

Funzioni previste:

- modifica/eliminazione bar e visite
- grafici
- classifiche filtrate
- foto multiple
- mappa
- PWA mobile
- import/export completo

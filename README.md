# Appuccino v0.4.2

Web app locale per registrare e valutare bar/colazioni.

## Funzioni attuali

- Login con utente/password
- Profilo utente e cambio password
- Database SQLite
- Gestione bar
- Nuova visita con elementi ordinati selezionabili da menu
- Più elementi per visita, anche nella stessa macrocategoria
- Macrocategorie solo contenitori
- Categorie valutabili con criteri e peso
- Voto globale pesato
- Modifica e cancellazione visite
- Export CSV
- Interfaccia aggiornata in stile app, con menu laterale, card e tema caffè/cappuccino

## Deploy con Portainer

Carica il contenuto di questa cartella in un repository Git e usa Stacks → Add stack → Git Repository.

Variabili consigliate:

```env
APP_USERNAME=admin
APP_PASSWORD=cambia-questa-password
SECRET_KEY=stringa-lunga-casuale
```

Porta predefinita:

```text
8033
```

URL:

```text
http://IP_DEL_RASPBERRY:8033
```

## Aggiornamento

Dopo aver aggiornato il repository:

1. Portainer → Stack Appuccino
2. Pull and redeploy
3. Se il browser mostra ancora la vecchia grafica, svuota la cache o usa Ctrl+F5

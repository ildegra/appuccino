# Appuccino v0.5.1

Versione Docker/FastAPI/SQLite di Appuccino.

## v0.5.1

- Fix aggiunta nuova visita: parsing più robusto di prezzi e tempi, anche con virgola decimale italiana.
- Controllo più sicuro sull'esistenza del bar prima di creare la visita.
- Aggiunto prezzo unitario per ogni elemento ordinato.
- Prezzo medio del singolo prodotto disponibile nelle classifiche.
- Export CSV aggiornato con prezzo unitario degli elementi.

## v0.5.0

- Aggiunta pagina Classifiche.
- Classifica generale dei bar per voto globale.
- Classifiche dei prodotti: per ogni prodotto mostra i bar migliori.
- Classifica globale dei prodotti e filtro per numero minimo di visite.

## Deploy

Aggiorna il repository Git con questi file, poi in Portainer usa **Pull and redeploy**.
Verifica che nella barra alta compaia `v0.5.1`.

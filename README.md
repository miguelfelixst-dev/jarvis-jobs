# JARVIS Jobs

Radar automático de oportunidades digitais.

## Como funciona
O GitHub Actions executa `scripts/radar.py` periodicamente, coleta oportunidades públicas,
calcula um score de compatibilidade e atualiza `data/jobs.json`.

O painel em GitHub Pages lê esse arquivo e mostra as oportunidades com filtros.

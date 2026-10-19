# CLAUDE.md

## Constantes

- Toda constante (nomes, valores padrão, timeouts, intervalos, URLs, identificadores) fica no arquivo `constants.py` do próprio diretório/pacote onde é usada (ex.: `src/mpb_data_pipelines/ops/constants.py`).
- Não declare constantes soltas em módulos de lógica; importe-as de `constants.py`.
- Se o diretório ainda não tiver `constants.py`, crie um ao adicionar a primeira constante.
- Constantes compartilhadas por vários pacotes ficam em `src/mpb_data_pipelines/constants.py`.

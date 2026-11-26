# Evals 2026-11-26 — repeated-search-baseline

Modelo de conversa (e juiz): `qwen2.5:7b` · embeddings: `nomic-embed-text` · cada cenário rodou 5x

## Agente

| Métrica | Valor |
|---|---|
| Execuções que passaram em tudo | 4/5 (80%) |
| Respostas do modelo por execução (média) | 2.8 |
| Tokens por execução (média) | 8127 |
| Chamadas de ferramenta | 9 |
| Chamadas recusadas pela ferramenta | 1/9 (11%) |
| Chamadas escritas como texto (resgatadas) | 0/9 (0%) |
| Descobertas julgadas | 2 |
| Fiéis às páginas (juiz) | 0/2 (0%) |
| Afirmações com citação nas páginas (média) | 78% |

| Checagem | Passou |
|---|---|
| finished_with_answer | 5/5 (100%) |
| no_invented_sources | 5/5 (100%) |
| no_repeated_search | 5/5 (100%) |
| no_suggestion_before_saving | 4/5 (80%) |
| no_acknowledging_reply | 5/5 (100%) |
| no_announced_search | 5/5 (100%) |
| saved_in_portuguese | 2/2 (100%) |

| Cenário | Passou em tudo |
|---|---|
| handles_a_search_she_already_did | 4/5 (80%) |

Afirmações sem apoio nas páginas, segundo o juiz:

- brilham antes de se extinguir
- estrelas cadentes brilham como farol de avião

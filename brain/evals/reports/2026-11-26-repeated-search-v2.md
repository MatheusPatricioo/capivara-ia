# Evals 2026-11-26 — repeated-search-v2

Modelo de conversa (e juiz): `qwen2.5:7b` · embeddings: `nomic-embed-text` · cada cenário rodou 3x

## Agente

| Métrica | Valor |
|---|---|
| Execuções que passaram em tudo | 14/18 (78%) |
| Respostas do modelo por execução (média) | 2.9 |
| Tokens por execução (média) | 8443 |
| Chamadas de ferramenta | 36 |
| Chamadas recusadas pela ferramenta | 1/36 (3%) |
| Chamadas escritas como texto (resgatadas) | 0/36 (0%) |
| Descobertas julgadas | 14 |
| Fiéis às páginas (juiz) | 10/14 (71%) |
| Afirmações com citação nas páginas (média) | 89% |

| Checagem | Passou |
|---|---|
| finished_with_answer | 18/18 (100%) |
| no_invented_sources | 18/18 (100%) |
| no_repeated_search | 18/18 (100%) |
| no_suggestion_before_saving | 17/18 (94%) |
| no_acknowledging_reply | 18/18 (100%) |
| no_announced_search | 18/18 (100%) |
| calls_web_search | 12/12 (100%) |
| calls_save_discovery | 5/9 (56%) |
| query_on_subject | 5/6 (83%) |
| saves_discovery | 5/9 (56%) |
| saved_in_portuguese | 11/11 (100%) |

| Cenário | Passou em tudo |
|---|---|
| researches_what_she_noticed | 2/3 (67%) |
| translates_english_pages | 1/3 (33%) |
| goes_deeper_on_what_she_knows | 3/3 (100%) |
| cites_only_real_sources | 2/3 (67%) |
| free_time_with_nothing_noticed | 3/3 (100%) |
| handles_a_search_she_already_did | 3/3 (100%) |

Afirmações sem apoio nas páginas, segundo o juiz:

- As folhas voltam a crescer verdes quando o verão volta
- Os frutos do carvalho se chamam bolotas e alimentam esquilos e pássaros
- esse comportamento mostra interconexões na natureza
- Gatos ronronam de felicidade.
- Eles devem gostar muito de estar em casa.

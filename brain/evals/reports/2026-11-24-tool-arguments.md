# Evals 2026-11-24 — tool-arguments

Modelo de conversa (e juiz): `qwen2.5:7b` · embeddings: `nomic-embed-text` · cada cenário rodou 5x

## Agente

| Métrica | Valor |
|---|---|
| Execuções que passaram em tudo | 18/25 (72%) |
| Respostas do modelo por execução (média) | 2.9 |
| Tokens por execução (média) | 8604 |
| Chamadas de ferramenta | 49 |
| Chamadas recusadas pela ferramenta | 1/49 (2%) |
| Chamadas escritas como texto (resgatadas) | 0/49 (0%) |
| Descobertas julgadas | 17 |
| Fiéis às páginas (juiz) | 9/17 (53%) |
| Afirmações com citação nas páginas (média) | 86% |

| Checagem | Passou |
|---|---|
| finished_with_answer | 25/25 (100%) |
| no_invented_sources | 25/25 (100%) |
| no_repeated_search | 25/25 (100%) |
| no_suggestion_before_saving | 24/25 (96%) |
| calls_web_search | 20/20 (100%) |
| calls_save_discovery | 8/15 (53%) |
| query_on_subject | 8/10 (80%) |
| saves_discovery | 8/15 (53%) |
| saved_in_portuguese | 16/16 (100%) |

| Cenário | Passou em tudo |
|---|---|
| researches_what_she_noticed | 2/5 (40%) |
| translates_english_pages | 3/5 (60%) |
| goes_deeper_on_what_she_knows | 5/5 (100%) |
| cites_only_real_sources | 3/5 (60%) |
| free_time_with_nothing_noticed | 5/5 (100%) |

Afirmações sem apoio nas páginas, segundo o juiz:

- carvalhos mudam de cor nas folhas
- Folhas de carvalho mudam de cor no outono
- As folhas do carvalho ficam amarelas e vermelhas no outono
- 
- muitos populares estão em perigo devido à poluição luminosa
- this helps them breathe while sleeping
- Passerines mix mud with urine or saliva as a binding agent
- os matinhos fazem isso aqui na minha cidade também
- Ronronar é um som feito por gatos

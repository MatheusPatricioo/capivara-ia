# Evals: medindo a capivara

Testes conferem o código com um LLM falso. **Evals** conferem o comportamento do modelo de verdade: rodam cada caso várias vezes (o modelo não responde sempre igual) e devolvem taxas, para que cada mudança no agente tenha um "antes e depois" com números.

- **Recuperação (RAG):** 16 descobertas fixas e 30 perguntas com resposta conhecida (6 delas sem resposta na memória) medem a busca com **recall@k** e **MRR**, e a decisão final (o que vai para o contexto dela) com uma tabela de acertos por limite de similaridade.
- **Agente:** 5 momentos da vida dela, com o modelo, os prompts, a voz interior e as ferramentas reais. Só a internet e os arquivos são roteirizados. Checagens em código contam quantas vezes ela tentou quebrar uma regra (fonte inventada, busca repetida, sugestão antes de salvar) e se fez o que o momento pedia.
- **Fidelidade (LLM-as-judge):** um juiz no Ollama quebra cada resumo salvo em afirmações e precisa citar o trecho exato das páginas que sustenta cada uma. O código confere se a citação existe e calcula a nota. O que dá para checar por código (como o idioma) não passa pelo juiz.

Cada execução gera um relatório em `brain/evals/reports/`. A linha de base está em [`2026-11-24-baseline.md`](../brain/evals/reports/2026-11-24-baseline.md) e a versão atual em [`2026-11-24-rag-v2.md`](../brain/evals/reports/2026-11-24-rag-v2.md):

| Medida | Linha de base | Atual |
|---|---|---|
| RAG: recall@1 / recall@3 / MRR | 0,71 / 0,79 / 0,77 | 0,88 / 0,96 / 0,93 |
| RAG: decisões certas | 47% (limite 0,70) | 97% (rerank com LLM) |
| Agente: execuções que passaram em tudo | 84% (21 de 25) | 76% (19 de 25) |
| Agente: chamadas de ferramenta recusadas / escritas como texto | 2% / 0% | 0% / 0% |
| Agente: tentativas de quebrar regras (fonte inventada, busca repetida, sugestão antes de salvar) | 0 | 0 |
| Fidelidade: afirmações com citação nas páginas | 81% | 91% |

Duas lições do baseline. Com o mesmo código, duas rodadas de 25 execuções variaram de 68% a 84% em "passou em tudo", então diferenças menores que uns 15 pontos são ruído. E o juiz local (7B) ainda erra para os dois lados: pega invenções reais ("na primavera", quando a página dizia outono) e às vezes não acha a citação de uma frase que está na página. Por isso o relatório lista cada afirmação sem apoio, para conferir à mão.

## Rodar os evals

Os evals usam o Ollama de verdade (e o PostgreSQL para a recuperação, num banco separado `<MEMORY_DB_NAME>_eval`), então ficam fora do `pytest` e do CI:

```bash
cd brain
python -m src.run_evals                          # tudo, cada cenário 3 vezes (~4 min)
python -m src.run_evals --suite retrieval        # só o RAG (segundos)
python -m src.run_evals --repeats 5 --label nome-da-mudanca
```

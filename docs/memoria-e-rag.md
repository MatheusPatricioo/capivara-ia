# Memória e RAG

A memória tem duas camadas:

- **Descobertas:** arquivos Markdown legíveis na pasta de descobertas (`DISCOVERIES_DIR` no `brain/.env`, ou `discoveries/` por padrão). Qualquer pessoa pode ver o que a capivara encontrou. Eles são a fonte da verdade.
- **Memória de longo prazo:** cada descoberta salva também vai para o PostgreSQL, inteira e em pedaços (*chunks*: o texto todo e janelas de duas frases, cada uma com o título e o tema como cabeçalho). Cada pedaço guarda um embedding do `nomic-embed-text` (busca por significado, com [pgvector](https://github.com/pgvector/pgvector)) e um `tsvector` (busca por palavras, com o full-text search do próprio PostgreSQL, em português e sem acentos).

Se o banco estiver desligado, nada quebra: a descoberta continua salva em Markdown, ela só não entra na memória (fica um aviso no log). Para colocar na memória as descobertas que já estavam na pasta, existe um comando próprio (veja [Ligar a memória](como-rodar.md#ligar-a-memória)).

**Como ela lembra (RAG):** no começo de cada ciclo do modo vivo, para cada coisa que ela notou no mundo (como "um carvalho enorme de folhas alaranjadas"), o pipeline decide se alguma descoberta do tesouro é sobre aquilo:

1. **Busca híbrida:** os pedaços são buscados por significado e por palavras ao mesmo tempo, e as duas listas são juntadas por **Reciprocal Rank Fusion** (RRF). Embeddings e consultas usam os prefixos de tarefa do `nomic-embed-text` (`search_document:` e `search_query:`).
2. **Rerank com LLM:** as 5 descobertas mais próximas (acima de um piso de similaridade) vão para o modelo, que escolhe a que é mesmo sobre a coisa notada, ou "nenhuma". A resposta é restrita a essas opções (saída estruturada) e conferida no código.
3. **Reescrita da pergunta (opcional):** "luzinhas piscando no jardim" vira também "vaga-lumes bioluminescência". Melhora a busca, mas com o rerank as decisões já acertavam tanto quanto, então vem desligada para economizar uma chamada ao modelo.

A descoberta escolhida volta para o contexto dela com o resumo completo, para que ela vá atrás de um detalhe novo em vez de pesquisar de novo o que já sabe.

**Memória como ferramenta (agentic RAG):** além do RAG automático, existe a ferramenta `recall_memory`, para ela decidir sozinha quando procurar no tesouro. Ela vem **desligada** (`MEMORY_RECALL_TOOL=false`), e o motivo é o próprio eval. O qwen2.5:7b não chamou a ferramenta nenhuma vez em 15 execuções do cenário feito para ela. Pior: só por ela estar na lista, ele passou a salvar menos descobertas, e uma frase no prompt sobre ela derrubou o salvamento de 5/5 para 2/5. Com um modelo maior, vale ligar e medir de novo.

Cada passo foi ligado um de cada vez e medido nos [evals](evals.md). Cada etapa pode ser ligada e desligada no `brain/.env` (`MEMORY_SEARCH_MODE`, `MEMORY_TASK_PREFIXES`, `MEMORY_QUERY_REWRITING`, `MEMORY_RERANK`, `MEMORY_RECALL_TOOL`).

Resultado nas 30 perguntas do eval ([relatório](../brain/evals/reports/2026-11-24-rag-v2.md)). "Decisões certas" conta tanto lembrar a descoberta certa quanto ficar em silêncio quando nenhuma é sobre o assunto:

| Variante | recall@1 | MRR | Decisões certas | Lembrou errada |
|---|---|---|---|---|
| Vetor do texto inteiro (como era) | 0,71 | 0,77 | 57% | 13 |
| + prefixos de tarefa | 0,62 | 0,76 | 57% | 7 |
| + chunks e busca híbrida (RRF) | 0,88 | 0,93 | 77% | 5 |
| + reescrita da pergunta | 0,92 | 0,95 | 83% | 2 |
| + rerank com LLM | 0,92 | 0,95 | 97% | 0 |
| **Híbrida + rerank, sem reescrita (padrão)** | 0,88 | 0,93 | **97%** | **0** |

As variantes sem rerank usam o melhor limite de similaridade achado no próprio conjunto, o que as favorece, e mesmo assim ficam bem abaixo. Os prefixos sozinhos até pioram o recall@1: só rendem junto com os pedaços e a busca híbrida. No eval do agente, a nova versão passou em tudo em 76% das execuções, dentro da faixa do baseline (68% a 84%).

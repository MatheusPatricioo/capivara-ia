# Capivara IA

[![CI](https://github.com/MatheusPatricioo/corvo-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/MatheusPatricioo/corvo-ia/actions/workflows/ci.yml)

**Um agente de IA autônomo com corpo: uma capivara que explora a internet, rabisca o que descobre e guarda o que aprende.**

## A ideia

Capivara IA é uma capivara que vive num pequeno mundo 3D, comandada por um cérebro de IA. Sozinha, ela pesquisa assuntos na internet, rabisca ideias no computador e salva suas descobertas em textos e desenhos. Dá para acompanhar tudo em tempo real.

## Arquitetura

O projeto tem três partes:

| Parte | Tecnologia | Responsabilidade |
|-------|------------|------------------|
| **Mundo** | Godot 4 | Renderiza o mundo 3D e anima a capivara. Nenhuma lógica de IA fica aqui. |
| **Cérebro** | Python | Roda o loop do agente: decide o que fazer, chama ferramentas (pesquisa na web, desenho, salvar) e conversa com o LLM. |
| **Memória** | Markdown + PostgreSQL (pgvector) | Guarda tudo o que a capivara aprendeu: arquivos para pessoas lerem e um índice por significado para ela lembrar. |

Mundo e Cérebro conversam por WebSocket, com mensagens JSON validadas. O Cérebro segue uma arquitetura em camadas (domain → application → infrastructure), então provedores de LLM e ferramentas podem ser trocados sem mexer nas regras do agente.

### Memória

A memória tem duas camadas:

- **Descobertas:** arquivos Markdown legíveis na pasta de descobertas (`DISCOVERIES_DIR` no `brain/.env`, ou `discoveries/` por padrão). Qualquer pessoa pode ver o que a capivara encontrou. Eles são a fonte da verdade.
- **Memória de longo prazo:** cada descoberta salva também vai para o PostgreSQL, inteira e em pedaços (*chunks*: o texto todo e janelas de duas frases, cada uma com o título e o tema como cabeçalho). Cada pedaço guarda um embedding do `nomic-embed-text` (busca por significado, com [pgvector](https://github.com/pgvector/pgvector)) e um `tsvector` (busca por palavras, com o full-text search do próprio PostgreSQL, em português e sem acentos).

Se o banco estiver desligado, nada quebra: a descoberta continua salva em Markdown, ela só não entra na memória (fica um aviso no log). Para colocar na memória as descobertas que já estavam na pasta, existe um comando próprio (veja [Ligar a memória](#ligar-a-memória)).

**Como ela lembra (RAG):** no começo de cada ciclo do modo vivo, para cada coisa que ela notou no mundo (como "um carvalho enorme de folhas alaranjadas"), o pipeline decide se alguma descoberta do tesouro é sobre aquilo:

1. **Busca híbrida:** os pedaços são buscados por significado e por palavras ao mesmo tempo, e as duas listas são juntadas por **Reciprocal Rank Fusion** (RRF). Embeddings e consultas usam os prefixos de tarefa do `nomic-embed-text` (`search_document:` e `search_query:`).
2. **Rerank com LLM:** as 5 descobertas mais próximas (acima de um piso de similaridade) vão para o modelo, que escolhe a que é mesmo sobre a coisa notada, ou "nenhuma". A resposta é restrita a essas opções (saída estruturada) e conferida no código.
3. **Reescrita da pergunta (opcional):** "luzinhas piscando no jardim" vira também "vaga-lumes bioluminescência". Melhora a busca, mas com o rerank as decisões já acertavam tanto quanto, então vem desligada para economizar uma chamada ao modelo.

A descoberta escolhida volta para o contexto dela com o resumo completo, para que ela vá atrás de um detalhe novo em vez de pesquisar de novo o que já sabe.

**Memória como ferramenta (agentic RAG):** além do RAG automático, existe a ferramenta `recall_memory`, para ela decidir sozinha quando procurar no tesouro. Ela vem **desligada** (`MEMORY_RECALL_TOOL=false`), e o motivo é o próprio eval. O qwen2.5:7b não chamou a ferramenta nenhuma vez em 15 execuções do cenário feito para ela. Pior: só por ela estar na lista, ele passou a salvar menos descobertas, e uma frase no prompt sobre ela derrubou o salvamento de 5/5 para 2/5. Com um modelo maior, vale ligar e medir de novo.

Cada passo foi ligado um de cada vez e medido nos [evals](#evals-medindo-a-capivara). Cada etapa pode ser ligada e desligada no `brain/.env` (`MEMORY_SEARCH_MODE`, `MEMORY_TASK_PREFIXES`, `MEMORY_QUERY_REWRITING`, `MEMORY_RERANK`, `MEMORY_RECALL_TOOL`).

Resultado nas 30 perguntas do eval ([relatório](brain/evals/reports/2026-11-24-rag-v2.md)). "Decisões certas" conta tanto lembrar a descoberta certa quanto ficar em silêncio quando nenhuma é sobre o assunto:

| Variante | recall@1 | MRR | Decisões certas | Lembrou errada |
|---|---|---|---|---|
| Vetor do texto inteiro (como era) | 0,71 | 0,77 | 57% | 13 |
| + prefixos de tarefa | 0,62 | 0,76 | 57% | 7 |
| + chunks e busca híbrida (RRF) | 0,88 | 0,93 | 77% | 5 |
| + reescrita da pergunta | 0,92 | 0,95 | 83% | 2 |
| + rerank com LLM | 0,92 | 0,95 | 97% | 0 |
| **Híbrida + rerank, sem reescrita (padrão)** | 0,88 | 0,93 | **97%** | **0** |

As variantes sem rerank usam o melhor limite de similaridade achado no próprio conjunto, o que as favorece, e mesmo assim ficam bem abaixo. Os prefixos sozinhos até pioram o recall@1: só rendem junto com os pedaços e a busca híbrida. No eval do agente, a nova versão passou em tudo em 76% das execuções, dentro da faixa do baseline (68% a 84%).

### Desenhos

Toda descoberta salva vira um rascunho de alguma coisa dela. A escolha do que desenhar usa **retrieve and rerank**:

1. **Retrieve:** o título e o resumo da descoberta viram um embedding, comparado com rótulos em português das 345 categorias do Quick, Draw!. As 5 mais parecidas viram candidatas.
2. **Rerank:** o LLM lê a descoberta e escolhe uma das 5, ou responde "nenhuma" quando nada nela é desenhável (como "Independência do Brasil"). A resposta é restrita a essas opções e conferida no código.

A capivara então pega um rabisco real, feito por uma pessoa, dessa categoria como referência e **redesenha com a mão dela**: um pouco inclinado, com outras proporções, os traços fora do lugar e uma linha levemente ondulada, então nenhum desenho sai igual a outro. Cada desenho é salvo como PNG em estilo Paint (traço preto sobre fundo branco) na pasta de descobertas e aparece na aba **Desenhos** do computador do mundo.

**Próxima etapa planejada:** hoje ela reinterpreta um rabisco que já existe. O plano é ela criar desenhos inéditos com o [Sketch-RNN](https://magenta.tensorflow.org/sketch-rnn-demo) (Google Magenta), uma rede neural pequena treinada no Quick, Draw! que desenha traço por traço e pode partir de um rabisco existente para criar uma variação. Ela vai rodar localmente e de graça, como o resto do projeto.

### Ela sugere, eu construo

À medida que aprende sobre as coisas, a capivara vai **sugerir melhorias para a própria vida** no mundinho. Depois de pesquisar sobre vitórias-régias, por exemplo, ela pode pedir "um laguinho maior, com vitórias-régias de verdade", e depois de aprender sobre vaga-lumes, "luzinhas no jardim à noite".

Cada sugestão fica num arquivo Markdown em `sugestoes/`, dentro da pasta de descobertas, com o pedido, o motivo e a descoberta que a inspirou. Eu leio as sugestões e, aos poucos, construo as que fizerem sentido no mundo do Godot. Assim o mundo cresce a partir do que ela aprende, e ela pode reparar nas novidades quando passear por elas.

As regras ficam no código, não só no prompt: ela só sugere depois de salvar uma descoberta no mesmo ciclo (que vira a inspiração), no máximo uma vez por ciclo, e um pedido parecido demais com um que ela já fez é recusado. A comparação usa embeddings, com o limite `SUGGESTION_REPEAT_MIN_SIMILARITY` (0,80 por padrão, medido com o `nomic-embed-text`).

O convite para sugerir aparece no momento certo: no fim da resposta de cada descoberta salva. Com a regra só no prompt de sistema, ela nunca sugeria (0 de 20 momentos reais). Com o convite, sugere em cerca de 1 a cada 10 descobertas, sempre com pedidos concretos ("Vaga-lumes no jardim à noite"). A cada ciclo, a voz interior também lista as últimas sugestões que ela já fez, para ela não pedir a mesma coisa com outras palavras.

Para ler os pedidos, clique no computador do mundo e abra a aba **Sugestões**: a lista fica à esquerda, das mais novas para as mais antigas, e o pedido escolhido aparece à direita, com o motivo e a descoberta que o inspirou. Os pedidos já construídos ganham um ✔ na lista.

Quando eu construo um pedido, marco a sugestão como construída:

```powershell
cd brain
python -m src.mark_suggestion_built                 # lista as sugestões esperando
python -m src.mark_suggestion_built 2026-11-24-um-laguinho-com-vitorias-regias.md --thing-id water_lilies
```

Isso troca a linha `- **Situação:** pendente` do arquivo por `construída` (editar a linha à mão também funciona). A partir daí, a voz interior conta a ela quais pedidos o criador construiu e quais ainda estão esperando. O `--thing-id` é opcional: é o `thing_id` do `Observable` que coloquei no mundo para o pedido. Quando ela passa perto dele, repara na coisa e fica sabendo que é o que ela pediu.

### Evals: medindo a capivara

Testes conferem o código com um LLM falso. **Evals** conferem o comportamento do modelo de verdade: rodam cada caso várias vezes (o modelo não responde sempre igual) e devolvem taxas, para que cada mudança no agente tenha um "antes e depois" com números.

- **Recuperação (RAG):** 16 descobertas fixas e 30 perguntas com resposta conhecida (6 delas sem resposta na memória) medem a busca com **recall@k** e **MRR**, e a decisão final (o que vai para o contexto dela) com uma tabela de acertos por limite de similaridade.
- **Agente:** 5 momentos da vida dela, com o modelo, os prompts, a voz interior e as ferramentas reais. Só a internet e os arquivos são roteirizados. Checagens em código contam quantas vezes ela tentou quebrar uma regra (fonte inventada, busca repetida, sugestão antes de salvar) e se fez o que o momento pedia.
- **Fidelidade (LLM-as-judge):** um juiz no Ollama quebra cada resumo salvo em afirmações e precisa citar o trecho exato das páginas que sustenta cada uma. O código confere se a citação existe e calcula a nota. O que dá para checar por código (como o idioma) não passa pelo juiz.

Cada execução gera um relatório em `brain/evals/reports/`. A linha de base está em [`2026-11-24-baseline.md`](brain/evals/reports/2026-11-24-baseline.md) e a versão atual em [`2026-11-24-rag-v2.md`](brain/evals/reports/2026-11-24-rag-v2.md):

| Medida | Linha de base | Atual |
|---|---|---|
| RAG: recall@1 / recall@3 / MRR | 0,71 / 0,79 / 0,77 | 0,88 / 0,96 / 0,93 |
| RAG: decisões certas | 47% (limite 0,70) | 97% (rerank com LLM) |
| Agente: execuções que passaram em tudo | 84% (21 de 25) | 76% (19 de 25) |
| Agente: chamadas de ferramenta recusadas / escritas como texto | 2% / 0% | 0% / 0% |
| Agente: tentativas de quebrar regras (fonte inventada, busca repetida, sugestão antes de salvar) | 0 | 0 |
| Fidelidade: afirmações com citação nas páginas | 81% | 91% |

Duas lições do baseline. Com o mesmo código, duas rodadas de 25 execuções variaram de 68% a 84% em "passou em tudo", então diferenças menores que uns 15 pontos são ruído. E o juiz local (7B) ainda erra para os dois lados: pega invenções reais ("na primavera", quando a página dizia outono) e às vezes não acha a citação de uma frase que está na página. Por isso o relatório lista cada afirmação sem apoio, para conferir à mão.

## Stack

- **Mundo:** Godot 4, GDScript
- **Cérebro:** Python 3.12, Pydantic, WebSocket
- **LLM:** Ollama (local), atrás da interface `LanguageModel` do domínio, então trocar de provedor é escrever um novo adapter sem mexer nas regras do agente
- **Memória:** Markdown, PostgreSQL + pgvector (Docker Compose), psycopg 3
- **Voz (opcional):** Piper (texto para fala) e faster-whisper (fala para texto), os dois locais e offline, com sounddevice para tocar e gravar
- **Qualidade:** pytest, ruff, mypy (strict)

## Como começar

### Pré-requisitos

- [Python 3.12+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) com o modelo de conversa `qwen2.5:7b` e o modelo de embedding `nomic-embed-text` (que escolhe o que ela desenha e dá à capivara a memória por significado):

  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para o PostgreSQL da memória de longo prazo)
- [Godot 4](https://godotengine.org/download) (só para ver o mundo 3D)

### Instalação

Crie e ative um ambiente virtual e instale as dependências (`--group` exige pip 25.1+):

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install --group dev .
Copy-Item brain\.env.example brain\.env
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install --group dev .
cp brain/.env.example brain/.env
```

Depois, abra o `brain/.env` e escolha uma senha para o banco em `MEMORY_DB_PASSWORD`.

### Ligar a memória

Com o Docker Desktop aberto, na raiz do projeto (igual em todos os sistemas):

```bash
docker compose --env-file brain/.env up -d
```

O `compose.yaml` lê as mesmas variáveis `MEMORY_DB_*` do `brain/.env`. Na primeira subida, o banco é criado com a tabela e o índice de `brain/database/init/`. Os dados ficam num volume do Docker, então sobrevivem a `docker compose --env-file brain/.env down`.

Se você já tem descobertas salvas na pasta, coloque-as na memória (pode rodar quantas vezes quiser: nada é duplicado):

```bash
cd brain
python -m src.load_discoveries_into_memory
```

A partir daí, toda descoberta nova entra na memória sozinha.

**Atualizando de uma versão anterior:** o cérebro aplica sozinho, ao ligar, os arquivos novos de `brain/database/init/` (como a tabela de pedaços). Rode o comando acima uma vez para que as descobertas antigas ganhem pedaços e embeddings com os prefixos de tarefa. O mesmo vale sempre que mudar `MEMORY_TASK_PREFIXES`.

### Conversar com a capivara

Com o Ollama rodando (igual em todos os sistemas):

```bash
cd brain
python -m src.chat_with_capybara
```

Digite `sair` para encerrar o chat.

#### Conversar por voz

Ela também pode falar em voz alta, e você pode falar com ela pelo microfone. O texto continua igual: o que ela diz aparece na tela, e você pode digitar quando quiser. Tudo roda na sua máquina, sem internet depois dos downloads.

Uma vez só, instale as bibliotecas de voz e baixe a voz em português (na raiz do projeto):

```bash
pip install ".[voice]"
python -m piper.download_voices pt_BR-faber-medium --download-dir brain/voices
```

Depois, ligue o chat com `--voz`:

```bash
cd brain
python -m src.chat_with_capybara --voz
```

Para falar, aperte Enter com a linha vazia, fale e aperte Enter de novo. Na primeira vez, o modelo do Whisper (`small`, ~480 MB) é baixado sozinho. O tamanho do modelo, o idioma e o uso de GPU ficam em `SPEECH_RECOGNITION_*`, no `brain/.env`.

### Ver a capivara viva

No modo vivo ninguém fala com a capivara: a cada poucos minutos ela decide sozinha o que fazer (pesquisar algo, salvar uma descoberta e rabiscar um desenho dela, ou só descansar), e o corpo dela acompanha no mundo 3D.

No Windows, um comando liga tudo: o Ollama (se ainda não estiver rodando), a memória no Docker (abrindo o Docker Desktop se precisar, e esperando o banco ficar pronto), o cérebro numa janela própria do PowerShell, com os logs visíveis, e o mundo no Godot:

```powershell
setx GODOT_PATH "C:\caminho\para\Godot_v4.x-stable_win64.exe"   # só na primeira vez; abra um terminal novo depois
.\start.ps1           # roda o jogo
.\start.ps1 -Editor   # abre o editor do Godot em vez do jogo
```

A memória é opcional: sem Docker, ou se o banco não subir, o script avisa e segue, e a capivara funciona do mesmo jeito, só não lembra do que já descobriu.

Para ligar cada parte à mão:

1. Com o Ollama rodando e a memória ligada (veja [Ligar a memória](#ligar-a-memória)), inicie o cérebro:

   ```bash
   cd brain
   python -m src.live_capybara
   ```

2. Abra a pasta `world/` no Godot e aperte Play. A ordem não importa: o mundo fica tentando se conectar ao cérebro.

Atalho no Windows: abrir o mundo pelo editor do Godot e apertar Play já basta. Se nenhum cérebro responder em 4 segundos, o próprio mundo roda o `start.ps1 -SkipWorld` (Ollama, memória e cérebro, sem abrir outro Godot), e o aviso na tela mostra "Ligando o cérebro...". Ele tenta uma vez por Play, e fechar o jogo não desliga o cérebro. Para desligar esse atalho, defina a variável de ambiente `CAPYBARA_BRAIN_AUTOSTART=0`.

O Godot é opcional: com ele fechado, a capivara continua pesquisando, salvando e desenhando do mesmo jeito. O mundo só mostra o que o cérebro faz e, ao abrir, já recebe como ela está se sentindo e o céu do momento. O contrário não vale: sem o cérebro, ela só passeia, e o mundo mostra o aviso "Cérebro desconectado" no canto da tela até ele ligar.

No mundo, ela vai até o computador antes de pesquisar e antes de salvar, e o desenho de cada descoberta sai ali mesmo. Para ver os desenhos, clique no computador e abra a aba **Desenhos**. Toda descoberta (Markdown) e todo desenho (PNG) ficam na pasta de descobertas (`DISCOVERIES_DIR` no `brain/.env`, ou `discoveries/` por padrão).

Aperte `Ctrl+C` para encerrar. O intervalo entre os ciclos e o limite de tokens por hora ficam no `brain/.env` (`AUTONOMOUS_CYCLE_INTERVAL_SECONDS`, `MAX_TOKENS_PER_HOUR`).

### Rodar os testes

Na raiz do projeto:

```bash
pytest
ruff check .
mypy brain/src
```

Os testes nunca chamam o LLM nem a internet de verdade: usam fakes. Os testes marcados com `database` usam o PostgreSQL do Docker, num banco separado (`<MEMORY_DB_NAME>_test`, criado sozinho), então nunca tocam na memória real. Com o banco desligado, eles são pulados com uma dica de como ligar. Para deixá-los de fora:

```bash
pytest -m "not database"
```

A cada push e pull request, o GitHub Actions (`.github/workflows/ci.yml`) roda `ruff`, `mypy` e a suíte inteira, com um PostgreSQL + pgvector de verdade como serviço, então os testes de `database` também rodam lá.

### Rodar os evals

Os evals usam o Ollama de verdade (e o PostgreSQL para a recuperação, num banco separado `<MEMORY_DB_NAME>_eval`), então ficam fora do `pytest` e do CI:

```bash
cd brain
python -m src.run_evals                          # tudo, cada cenário 3 vezes (~4 min)
python -m src.run_evals --suite retrieval        # só o RAG (segundos)
python -m src.run_evals --repeats 5 --label nome-da-mudanca
```

## Créditos

- Kits de natureza e móveis por [Kenney](https://kenney.nl) (CC0)
- Rabiscos de referência dos desenhos: amostra do dataset [Quick, Draw!](https://github.com/googlecreativelab/quickdraw-dataset) do Google, sob licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Os traços foram convertidos para pares `[x, y]` e só 30 rabiscos por categoria foram guardados (`brain/doodles/quickdraw_sample.json`, gerado por `python -m src.download_quickdraw_sample`).
- Modelo da capivara gerado com TRELLIS (Microsoft, MIT)

## Status

🚧 Em desenvolvimento ativo.

- **Funcionando:** chat e modo vivo autônomo, pesquisa na web, descobertas salvas em Markdown, rascunhos das descobertas escolhidos por embeddings, memória de longo prazo com RAG (busca híbrida com pgvector e full-text, RRF e rerank com LLM) e ferramenta de memória opcional (agentic RAG), evals automatizados com LLM-as-judge, CI, sugestões de melhorias para o mundo (com a aba Sugestões no computador e a capivara reconhecendo o que foi construído), mundo 3D conectado ao cérebro por WebSocket e limite de tokens por hora.
- **Próximos passos** (técnicas de IA usadas no mercado, nesta ordem, sempre com ferramentas gratuitas):
  1. ~~**CI:** `ruff`, `mypy` e `pytest` (com PostgreSQL + pgvector) a cada push, no GitHub Actions.~~ ✔
  2. ~~**Evals automatizados:** RAG (recall@k, MRR, acerto da decisão), agente (checagens de regras e expectativas) e fidelidade com LLM-as-judge.~~ ✔ (veja [Evals](#evals-medindo-a-capivara))
  3. ~~**Argumentos de ferramenta com um schema só:** cada ferramenta tem uma classe Pydantic que gera o JSON Schema enviado ao modelo e valida o que ele manda, com erros campo por campo para ele se corrigir. O tool calling já era nativo: o eval mostrou 0 chamadas escritas como texto.~~ ✔ ([relatório](brain/evals/reports/2026-11-24-tool-arguments.md): sem regressão, tudo dentro do ruído do baseline)
  4. ~~**RAG v2:** pedaços (chunking) com cabeçalho, busca híbrida (full-text do PostgreSQL + pgvector) por Reciprocal Rank Fusion, rerank com LLM, reescrita da pergunta e a memória como ferramenta (agentic RAG).~~ ✔ (decisões certas de 57% para 97%; veja [Memória](#memória))
  5. **Observabilidade:** cada passo do agente (prompt, ferramenta, tokens, tempo) registrado com OpenTelemetry e visto num painel do Langfuse rodando no Docker, com os prompts versionados.
  6. **Reflexão e consolidação de memória:** de tempos em tempos ela relê as descobertas e escreve reflexões de nível mais alto, que também viram memória (como no artigo *Generative Agents*).
  7. **Defesa contra prompt injection:** páginas de ataque ("ignore suas instruções e...") nos evals, provando que conteúdo da web é tratado como dado, com uma camada de guardrail.
  8. **Servidor MCP:** as descobertas e as ferramentas da capivara expostas pelo Model Context Protocol, para qualquer cliente MCP consultar.
  9. **Multiagente:** papéis separados (pesquisadora, revisora que confere as fontes, artista) num fluxo orquestrado, medido pelos evals.
  10. **Fine-tuning com LoRA:** um modelo pequeno ajustado (Unsloth, no Colab grátis) com os logs de uso de ferramentas dela, comparado ao modelo base pelos evals.
  11. **Visão e desenhos inéditos:** um modelo de visão local confere se o desenho parece o que ela quis desenhar, e o Sketch-RNN cria desenhos inéditos em vez de escolher rabiscos prontos.
  12. **Dia, noite e o clima real:** o mundo segue o horário de verdade e o clima da cidade, por uma API gratuita de previsão do tempo. À noite ela dorme na casinha, e na chuva fica em casa, pensativa. Para testar rápido, `WORLD_CLOCK_MODE=fast` no `brain/.env` faz o dia inteiro durar `WORLD_FAST_DAY_MINUTES` (60 por padrão): a cada hora amanhece no minuto 15 e anoitece no minuto 45. O clima vem da [Open-Meteo](https://open-meteo.com) (gratuita, sem chave), de Belo Horizonte por padrão (`WEATHER_LATITUDE`/`WEATHER_LONGITUDE`), e é sempre o real, nos dois modos: quando chove em BH, chove no jogo. Para testar a chuva sem esperar, `WEATHER_OVERRIDE=rain` (ou `clear`, `cloudy`, `fog`, `storm`) fixa o céu. *Técnica: dados externos influenciando comportamento e emoção.* (Feito: o relógio com os dois modos, o clima de BH e o céu no Godot, com sol, lua, nuvens, neblina e chuva. Falta ela dormir à noite e ficar em casa, pensativa, na chuva.)
  13. **Caixa de cartas:** quando o criador some, ela escreve cartinhas e deixa numa caixa de correio clicável no mundo. Ele pode responder, e ela lê na próxima vez. Combina com o sistema de saudade que já existe. *Técnica: comunicação assíncrona e memória do que os dois conversaram.* (Feito: ela escreve as cartas quando sente saudade, no máximo uma a cada `LETTER_MIN_HOURS_BETWEEN` horas e parando quando `LETTER_MAX_UNREAD` cartas esperam sem ser lidas. Ficam em `cartas/`, na pasta de descobertas. Ela vai até a caixa de correio, ao lado da casinha, deixar cada carta, e a bandeirinha sobe enquanto alguma está sem ler. Clicando na caixa, as cartas abrem numa folha de papel, e abrir uma carta a marca como lida. Embaixo de cada carta dá para escrever uma resposta, que fica guardada no mesmo arquivo, na seção "Resposta do criador". Falta ela ler a resposta.) Mais para frente: um **webhook** (Discord ou ntfy.sh, ambos gratuitos) avisa no celular quando ela escreve uma carta.

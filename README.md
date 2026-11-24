# Capivara IA

**Um agente de IA autônomo com corpo: uma capivara que explora a internet, pensa em voz alta numa lousa e guarda o que aprende.**

## A ideia

Capivara IA é uma capivara que vive num pequeno mundo 3D, comandada por um cérebro de IA. Sozinha, ela pesquisa assuntos na internet, rabisca ideias numa lousa e salva suas descobertas em textos e desenhos. Dá para acompanhar tudo em tempo real.

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
- **Memória de longo prazo:** cada descoberta salva também vira uma linha no PostgreSQL com a extensão [pgvector](https://github.com/pgvector/pgvector), junto do embedding do texto (gerado pelo `nomic-embed-text`). É um índice por significado: "roedor que mergulha" encontra "Capivaras nadam", mesmo sem nenhuma palavra em comum.

Se o banco estiver desligado, nada quebra: a descoberta continua salva em Markdown, ela só não entra na memória (fica um aviso no log). Para colocar na memória as descobertas que já estavam na pasta, existe um comando próprio (veja [Ligar a memória](#ligar-a-memória)).

**Como ela lembra (RAG):** no começo de cada ciclo do modo vivo, para cada coisa que ela notou no mundo (como "um carvalho enorme de folhas alaranjadas"), a descoberta mais parecida volta para o contexto dela, com o resumo completo. Assim, em vez de pesquisar de novo o que já sabe, ela vai atrás de um detalhe novo. Só volta a descoberta mais parecida, e só se a similaridade chegar a `MEMORY_RECALL_MIN_SIMILARITY` (0,70 por padrão, medido com as coisas do mundo). Cada comparação fica no log, para recalibrar esse valor com o uso.

### Desenhos na lousa

Toda descoberta salva vira um rascunho de alguma coisa dela. A escolha do que desenhar usa **retrieve and rerank**:

1. **Retrieve:** o título e o resumo da descoberta viram um embedding, comparado com rótulos em português das 345 categorias do Quick, Draw!. As 5 mais parecidas viram candidatas.
2. **Rerank:** o LLM lê a descoberta e escolhe uma das 5, ou responde "nenhuma" quando nada nela é desenhável (como "Independência do Brasil"). A resposta é restrita a essas opções e conferida no código.

A capivara então pega um rabisco real, feito por uma pessoa, dessa categoria como referência e **redesenha com a mão dela**: um pouco inclinado, com outras proporções, os traços fora do lugar e uma linha levemente ondulada, então nenhum desenho sai igual a outro. Cada desenho é salvo como PNG em estilo Paint (traço preto sobre fundo branco) na pasta de descobertas.

**Próxima etapa planejada:** hoje ela reinterpreta um rabisco que já existe. O plano é ela criar desenhos inéditos com o [Sketch-RNN](https://magenta.tensorflow.org/sketch-rnn-demo) (Google Magenta), uma rede neural pequena treinada no Quick, Draw! que desenha traço por traço e pode partir de um rabisco existente para criar uma variação. Ela vai rodar localmente e de graça, como o resto do projeto.

## Stack

- **Mundo:** Godot 4, GDScript
- **Cérebro:** Python 3.12, Pydantic, WebSocket
- **LLMs:** Ollama (local), Claude, OpenAI, atrás de uma única interface
- **Memória:** Markdown, PostgreSQL + pgvector (Docker Compose), psycopg 3
- **Qualidade:** pytest, ruff, mypy (strict)

## Como começar

### Pré-requisitos

- [Python 3.12+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) com o modelo de conversa `qwen2.5:7b` e o modelo de embedding `nomic-embed-text` (que escolhe o rabisco da lousa e dá à capivara a memória por significado):

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

### Conversar com a capivara

Com o Ollama rodando (igual em todos os sistemas):

```bash
cd brain
python -m src.chat_with_capybara
```

Digite `sair` para encerrar o chat.

### Ver a capivara viva

No modo vivo ninguém fala com a capivara: a cada poucos minutos ela decide sozinha o que fazer (pesquisar algo, salvar uma descoberta, desenhar na lousa ou só descansar), e o corpo dela acompanha no mundo 3D.

Antes, suba a memória (veja [Ligar a memória](#ligar-a-memória)). Sem ela, a capivara funciona do mesmo jeito, só não lembra do que já descobriu.

No Windows, um comando liga o resto: o Ollama (se ainda não estiver rodando), o cérebro numa janela própria do PowerShell, com os logs visíveis, e o mundo no Godot:

```powershell
setx GODOT_PATH "C:\caminho\para\Godot_v4.x-stable_win64.exe"   # só na primeira vez; abra um terminal novo depois
.\start.ps1           # roda o jogo
.\start.ps1 -Editor   # abre o editor do Godot em vez do jogo
```

Para ligar cada parte à mão:

1. Com o Ollama rodando, inicie o cérebro:

   ```bash
   cd brain
   python -m src.live_capybara
   ```

2. Abra a pasta `world/` no Godot e aperte Play. A ordem não importa: o mundo fica tentando se conectar ao cérebro.

O Godot é opcional: com ele fechado, a capivara continua pesquisando, salvando e desenhando do mesmo jeito. O mundo só mostra o que o cérebro faz e, ao abrir, já recebe a lousa atual.

No mundo, ela vai até o computador antes de pesquisar e antes de salvar, e até a lousa antes de desenhar. A lousa é a galeria dela: mostra os três desenhos (PNG) mais recentes da pasta de descobertas e se atualiza sozinha quando aparece um novo. Toda descoberta (Markdown) e todo desenho (PNG) ficam na pasta de descobertas (`DISCOVERIES_DIR` no `brain/.env`, ou `discoveries/` por padrão).

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

## Créditos

- Kits de natureza e móveis por [Kenney](https://kenney.nl) (CC0)
- Rabiscos da lousa: amostra do dataset [Quick, Draw!](https://github.com/googlecreativelab/quickdraw-dataset) do Google, sob licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Os traços foram convertidos para pares `[x, y]` e só 30 rabiscos por categoria foram guardados (`brain/doodles/quickdraw_sample.json`, gerado por `python -m src.download_quickdraw_sample`).
- Modelo da capivara gerado com TRELLIS (Microsoft, MIT)

## Status

🚧 Em desenvolvimento ativo.

- **Funcionando:** chat e modo vivo autônomo, pesquisa na web, descobertas salvas em Markdown, rascunhos na lousa escolhidos por embeddings, memória de longo prazo com RAG (PostgreSQL + pgvector), mundo 3D conectado ao cérebro por WebSocket e limite de tokens por hora.
- **Próximos passos:** desenhos inéditos com o Sketch-RNN, a lousa do Godot desenhando traço por traço e a capivara decidindo sozinha quando consultar a memória (agentic RAG).

# Como rodar

## Pré-requisitos

- [Python 3.12+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) com o modelo de conversa `qwen2.5:7b` e o modelo de embedding `nomic-embed-text` (que escolhe o que ela desenha e dá à capivara a memória por significado):

  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para o PostgreSQL da memória de longo prazo)
- [Godot 4](https://godotengine.org/download) (só para ver o mundo 3D)
- **Só no Windows:** o `libpq.dll` do PostgreSQL no PATH. O Smart App Control do Windows 11 bloqueia a DLL não assinada do `psycopg[binary]`, então no Windows o projeto instala o `psycopg` puro, que usa o libpq do sistema. Baixe o zip de binários da [EnterpriseDB](https://www.enterprisedb.com/download-postgresql-binaries) (as DLLs são assinadas), copie `libpq.dll`, `libssl-3-x64.dll`, `libcrypto-3-x64.dll`, `libintl-9.dll` e `libiconv-2.dll` da pasta `pgsql\bin` para uma pasta como `C:\tools\libpq` e coloque essa pasta no PATH. Para conferir: `python -c "import psycopg; print(psycopg.pq.__impl__)"` deve mostrar `python`.

## Instalação

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

## Ligar a memória

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

## Conversar com a capivara

Com o Ollama rodando (igual em todos os sistemas):

```bash
cd brain
python -m src.chat_with_capybara
```

Digite `sair` para encerrar o chat.

### Conversar por voz

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

## Ver a capivara viva

No modo vivo, a cada poucos minutos ela decide sozinha o que fazer (pesquisar algo, salvar uma descoberta e rabiscar um desenho dela, ou só descansar), e o corpo dela acompanha no mundo 3D.

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

Para conversar com ela no mundo, aperte **Enter**, escreva e aperte Enter de novo (Esc fecha a caixa). A resposta aparece num balão em cima dela. Enquanto vocês conversam, ela para de andar, vira para a câmera e pausa os próprios pensamentos antes do próximo passo. Para encerrar, aperte Enter com a caixa vazia: a caixa fecha e ela volta à rotina na hora. Sem isso, ela volta sozinha depois de `CONVERSATION_QUIET_MINUTES` (2 por padrão) sem mensagem nova. O modelo começa a carregar assim que o cérebro liga: espere a linha `Her model is loaded and ready` no log para a primeira resposta vir rápida.

No mundo, ela vai até o computador antes de pesquisar e antes de salvar, e o desenho de cada descoberta sai ali mesmo. Para ver os desenhos, clique no computador e abra a aba **Desenhos**. Toda descoberta (Markdown) e todo desenho (PNG) ficam na pasta de descobertas (`DISCOVERIES_DIR` no `brain/.env`, ou `discoveries/` por padrão). O mundo não lê essa pasta: o computador pede as notas, os desenhos e o histórico ao cérebro pelo WebSocket, então as abas só se enchem com o cérebro ligado.

Aperte `Ctrl+C` para encerrar. O intervalo entre os ciclos e o limite de tokens por hora ficam no `brain/.env` (`AUTONOMOUS_CYCLE_INTERVAL_SECONDS`, `MAX_TOKENS_PER_HOUR`).

## Rodar os testes

Na raiz do projeto:

```bash
pytest
ruff check .
ruff format --check .   # sem --check, formata os arquivos
mypy brain/src
```

Os testes nunca chamam o LLM nem a internet de verdade: usam fakes. Os testes marcados com `database` usam o PostgreSQL do Docker, num banco separado (`<MEMORY_DB_NAME>_test`, criado sozinho), então nunca tocam na memória real. Com o banco desligado, eles são pulados com uma dica de como ligar. Para deixá-los de fora:

```bash
pytest -m "not database"
```

A cada push e pull request, o GitHub Actions (`.github/workflows/ci.yml`) roda `ruff`, `mypy` e a suíte inteira, com um PostgreSQL + pgvector de verdade como serviço, então os testes de `database` também rodam lá.

Para medir o comportamento com o modelo de verdade, veja [Rodar os evals](evals.md#rodar-os-evals).

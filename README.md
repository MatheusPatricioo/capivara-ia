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
| **Memória** | Markdown + ChromaDB | Guarda tudo o que a capivara aprendeu, tanto para pessoas quanto para o agente. |

Mundo e Cérebro conversam por WebSocket, com mensagens JSON validadas. O Cérebro segue uma arquitetura em camadas (domain → application → infrastructure), então provedores de LLM e ferramentas podem ser trocados sem mexer nas regras do agente.

### Memória

A memória tem duas camadas:

- **Descobertas:** arquivos Markdown legíveis em `discoveries/`. Qualquer pessoa pode ver o que a capivara encontrou.
- **Índice vetorial:** um índice ChromaDB sobre essas descobertas, usado para busca semântica.

Antes de decidir o que fazer, a capivara consulta a memória usando RAG (geração aumentada por recuperação), para que cada nova pesquisa aproveite o que ela já sabe.

### Desenhos na lousa

Toda descoberta salva vira um rascunho de giz de alguma coisa dela. O cérebro transforma o título e o resumo da descoberta num embedding e compara com rótulos em português das 345 categorias do Quick, Draw!. Se uma categoria se destaca claramente das outras (`DOODLE_MIN_MARGIN` no `.env`), a capivara pega um rabisco real, feito por uma pessoa, como referência e **redesenha com a mão dela**: o desenho sai um pouco inclinado, com outras proporções, os traços fora do lugar e uma linha levemente ondulada, então nenhum desenho sai igual a outro. Se nada da descoberta é desenhável, a lousa fica como está. Cada desenho é salvo como PNG em estilo Paint (traço preto sobre fundo branco) na pasta de descobertas.

**Próxima etapa planejada:** hoje ela reinterpreta um rabisco que já existe. O plano é ela criar desenhos inéditos com o [Sketch-RNN](https://magenta.tensorflow.org/sketch-rnn-demo) (Google Magenta), uma rede neural pequena treinada no Quick, Draw! que desenha traço por traço e pode partir de um rabisco existente para criar uma variação. Ela vai rodar localmente e de graça, como o resto do projeto.

## Stack

- **Mundo:** Godot 4, GDScript
- **Cérebro:** Python 3.12, Pydantic, WebSocket
- **LLMs:** Ollama (local), Claude, OpenAI, atrás de uma única interface
- **Memória:** ChromaDB, Markdown
- **Qualidade:** pytest, ruff, mypy (strict)

## Como começar

### Pré-requisitos

- [Python 3.12+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) com o modelo de conversa `qwen2.5:7b` e o modelo de embedding `nomic-embed-text` (que escolhe o rabisco da lousa):

  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

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

### Conversar com a capivara

Com o Ollama rodando (igual em todos os sistemas):

```bash
cd brain
python -m src.chat_with_capybara
```

Digite `sair` para encerrar o chat.

### Ver a capivara viva

No modo vivo ninguém fala com a capivara: a cada poucos minutos ela decide sozinha o que fazer (pesquisar algo, salvar uma descoberta, desenhar na lousa ou só descansar), e o corpo dela acompanha no mundo 3D.

No Windows, um comando liga tudo: o Ollama (se ainda não estiver rodando), o cérebro numa janela própria do PowerShell, com os logs visíveis, e o mundo no Godot:

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

## Créditos

- Kits de natureza e móveis por [Kenney](https://kenney.nl) (CC0)
- Rabiscos da lousa: amostra do dataset [Quick, Draw!](https://github.com/googlecreativelab/quickdraw-dataset) do Google, sob licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Os traços foram convertidos para pares `[x, y]` e só 30 rabiscos por categoria foram guardados (`brain/doodles/quickdraw_sample.json`, gerado por `python -m src.download_quickdraw_sample`).
- Modelo da capivara gerado com TRELLIS (Microsoft, MIT)

## Status

🚧 Em desenvolvimento ativo.

- **Funcionando:** chat e modo vivo autônomo, pesquisa na web, descobertas salvas em Markdown, rascunhos na lousa escolhidos por embeddings, mundo 3D conectado ao cérebro por WebSocket e limite de tokens por hora.
- **Próximo passo:** memória de longo prazo (ChromaDB + RAG), para que cada novo ciclo aproveite o que ela já sabe.

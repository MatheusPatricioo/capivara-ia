# Decisões técnicas

As principais escolhas do projeto, cada uma com o contexto, as alternativas consideradas, a escolha e o motivo. Muitas delas foram decididas por medição: quando há um número, ele vem dos [evals](evals.md) ou de um teste feito na hora.

## Índice

- [LLM local, atrás de uma interface](#llm-local-atrás-de-uma-interface)
- [Cérebro e mundo em processos separados, por WebSocket](#cérebro-e-mundo-em-processos-separados-por-websocket)
- [Camadas, portas e fakes](#camadas-portas-e-fakes)
- [Guardrails no código, não só no prompt](#guardrails-no-código-não-só-no-prompt)
- [Tool calling nativo com um schema Pydantic só](#tool-calling-nativo-com-um-schema-pydantic-só)
- [Lembrete no fim do resultado da ferramenta](#lembrete-no-fim-do-resultado-da-ferramenta)
- [Desenhar escolhendo rabiscos reais, não à mão livre](#desenhar-escolhendo-rabiscos-reais-não-à-mão-livre)
- [Desenho automático em vez de uma ferramenta de desenho](#desenho-automático-em-vez-de-uma-ferramenta-de-desenho)
- [Markdown como fonte da verdade, PostgreSQL como índice](#markdown-como-fonte-da-verdade-postgresql-como-índice)
- [Busca híbrida e rerank com LLM em vez de limite fixo](#busca-híbrida-e-rerank-com-llm-em-vez-de-limite-fixo)
- [A memória como ferramenta fica desligada](#a-memória-como-ferramenta-fica-desligada)
- [Evals separados dos testes, com juiz que cita a fonte](#evals-separados-dos-testes-com-juiz-que-cita-a-fonte)
- [Emoções em camadas, com regras puras](#emoções-em-camadas-com-regras-puras)
- [Estado em arquivos que uma pessoa lê](#estado-em-arquivos-que-uma-pessoa-lê)
- [Voz local, como borda](#voz-local-como-borda)
- [Wikipedia como plano B da busca](#wikipedia-como-plano-b-da-busca)
- [Modelo sempre pronto e GPU para ele](#modelo-sempre-pronto-e-gpu-para-ele)
- [psycopg puro com libpq assinado no Windows](#psycopg-puro-com-libpq-assinado-no-windows)
- [O mundo pede ao cérebro em vez de ler o disco](#o-mundo-pede-ao-cérebro-em-vez-de-ler-o-disco)

---

## LLM local, atrás de uma interface

- **Contexto:** o agente roda o dia inteiro, em ciclos de poucos minutos, e o projeto não tem orçamento para API paga.
- **Alternativas:** API de um provedor na nuvem; modelo local pelo Ollama.
- **Escolha:** Ollama com `qwen2.5:7b` para conversa e tool calling, e `nomic-embed-text` para embeddings, atrás da interface `LanguageModel` do domínio.
- **Por quê:** custo zero e funciona offline. A interface faz do provedor um detalhe: trocar de modelo é escrever um novo adapter, sem mexer nas regras do agente. O preço é um modelo pequeno, que erra mais, e isso guiou várias decisões abaixo.

## Cérebro e mundo em processos separados, por WebSocket

- **Contexto:** a capivara precisa de um corpo 3D, mas a lógica de IA precisa de testes, tipagem e bibliotecas de Python.
- **Alternativas:** IA dentro do Godot (GDScript chamando o Ollama direto); um processo Python consultado por HTTP de tempos em tempos; um processo Python com WebSocket.
- **Escolha:** o Godot só renderiza e anima; o cérebro em Python manda ordens e recebe eventos por WebSocket, com mensagens JSON validadas por Pydantic. O servidor roda numa thread, com `Lock`, ao lado do loop síncrono, sem `asyncio`.
- **Por quê:** o mundo vira opcional (ela vive com o Godot fechado), cada lado é testado com as próprias ferramentas e a comunicação é nos dois sentidos, em tempo real. Mensagens que descrevem o estado (como "ouça por 120 s", reenviada a cada troca) em vez de "comece" e "pare" fazem uma mensagem perdida não deixar o mundo preso.

## Camadas, portas e fakes

- **Contexto:** o comportamento depende de LLM, internet, banco e disco, e os testes não podem chamar nada disso de verdade.
- **Alternativas:** testar com mocks pontuais; separar o código em camadas com interfaces.
- **Escolha:** `domain → application → infrastructure`, com portas (`Protocol`) no domínio e adapters na infraestrutura. Cada porta tem um fake, e o fake e o adapter real passam pela **mesma suíte de contrato**.
- **Por quê:** a suíte inteira roda em segundos e sem rede, e o teste de contrato prova que o fake se comporta como o real. Decorators (`EmbodiedTool`, `MeteredLanguageModel`, a memória por cima do repositório de descobertas) acrescentam comportamento só na montagem, sem mexer em quem usa.

## Guardrails no código, não só no prompt

- **Contexto:** um modelo de 7B esquece regras do prompt: inventa fontes, repete buscas, escolhe nomes de arquivo estranhos.
- **Alternativas:** reforçar as regras no prompt; garantir as regras no código.
- **Escolha:** o código decide o que é permitido, e o erro da ferramenta explica ao modelo como corrigir:
  - uma descoberta só aceita fontes que vieram de uma `web_search` daquela sessão;
  - o nome do arquivo é gerado pelo código, nunca pelo modelo, com uma segunda checagem de que o caminho fica dentro da pasta de descobertas;
  - uma busca já feita é pulada, a partir de um histórico persistente;
  - uma sugestão só vale depois de salvar uma descoberta no mesmo ciclo, no máximo uma por ciclo, e uma parecida demais com outra (por embeddings) é recusada;
  - limite de passos de ferramenta por ciclo (`MAX_TOOL_STEPS`) e de tokens por hora (`MAX_TOKENS_PER_HOUR`);
  - conteúdo da web é dado: links só abrem se forem `http(s)://`, e o texto é escapado antes de virar formatação.
- **Por quê:** regra no prompt é pedido; regra no código é garantia. Nos evals, as checagens em código contam zero tentativas de quebrar essas regras. A defesa contra prompt injection, com páginas de ataque nos evals, ainda é um passo do [roadmap](roadmap.md).

## Tool calling nativo com um schema Pydantic só

- **Contexto:** os argumentos das ferramentas tinham schema escrito à mão num lugar e validação em outro. A primeira hipótese era que o tool calling vinha extraído do texto.
- **Alternativas:** manter schema e validação separados; extrair as chamadas do texto; usar o tool calling nativo do Ollama com uma classe que gera o schema e valida.
- **Escolha:** cada ferramenta tem uma classe Pydantic que gera o JSON Schema enviado ao modelo e valida o que ele manda, com erros campo a campo para ele se corrigir. O parser de texto ficou só como rede de segurança.
- **Por quê:** lendo o código e medindo, o tool calling já era nativo: 0 de 41 chamadas precisaram do parser. O que faltava era uma fonte da verdade só. O schema foi simplificado (sem `title` e `null`) porque modelo pequeno se confunde com schema longo, e a mensagem de erro virou parte do prompt: curta, com o campo e o problema.

## Lembrete no fim do resultado da ferramenta

- **Contexto:** a regra "sugira melhorias para o seu mundo" estava no prompt de sistema e não funcionava.
- **Alternativas:** reforçar a regra no prompt de sistema; colocar o convite no fim do resultado da ferramenta, no momento em que ele faz sentido.
- **Escolha:** o convite aparece no fim da resposta de cada descoberta salva.
- **Por quê:** efeito de recência: o modelo dá mais peso ao que veio por último. Ela passou de 0 sugestões em 20 momentos reais para cerca de 1 a cada 10 descobertas, com pedidos concretos. O mesmo cuidado vale ao contrário: depois de um `save_discovery`, o lembrete geral fazia ela narrar em vez de agir, e tirá-lo subiu os desenhos de 11/20 para 16/20.

## Desenhar escolhendo rabiscos reais, não à mão livre

- **Contexto:** a primeira versão pedia ao LLM uma lista de formas para uma lousa. Modelo pequeno não tem noção espacial, e os desenhos saíam ruins.
- **Alternativas:** o LLM desenhando formas; gerar imagem com um modelo de difusão (pesado para rodar junto do LLM); gerar traços com o Sketch-RNN; escolher entre rabiscos reais de pessoas.
- **Escolha:** *retrieve and rerank* sobre as 345 categorias do Quick, Draw!: os embeddings trazem as 5 categorias mais próximas da descoberta, e o LLM escolhe uma ou responde "nenhuma". Depois, uma variação procedural com semente (inclinação, proporção, traço ondulado) redesenha o rabisco "com a mão dela".
- **Por quê:** o resultado é bonito sempre e roda local. Os rótulos ficaram em português porque o `nomic-embed-text` compara mal textos de línguas diferentes. A escolha usa temperatura 0, porque escolha estruturada pede repetibilidade. Desenhos inéditos com o Sketch-RNN estão no [roadmap](roadmap.md).

## Desenho automático em vez de uma ferramenta de desenho

- **Contexto:** existia uma ferramenta `draw`, e o modelo esquecia de chamar, chamava com o nome errado ou dizia que tinha desenhado sem ter desenhado.
- **Alternativas:** insistir no prompt; tornar o desenho uma consequência automática de salvar uma descoberta.
- **Escolha:** todo `save_discovery` bem-sucedido dispara o desenho num caso de uso próprio, e a ferramenta `draw` foi removida.
- **Por quê:** o que deve acontecer sempre não precisa ser uma decisão do modelo. Cada escolha a menos para um modelo pequeno é um erro a menos.

## Markdown como fonte da verdade, PostgreSQL como índice

- **Contexto:** ela precisa lembrar do que já descobriu, e o criador quer ler as descobertas no Explorer.
- **Alternativas:** só arquivos; um banco vetorial dedicado (como o ChromaDB); PostgreSQL com pgvector.
- **Escolha:** cada descoberta é um Markdown legível, e uma cópia em pedaços vai para o PostgreSQL com pgvector (Docker Compose). O arquivo é a fonte da verdade; o banco é um índice.
- **Por quê:** um banco só faz busca vetorial e full-text. Se o banco cair, nada se perde: a descoberta continua salva, ela só não entra na memória (um aviso no log), e um comando idempotente coloca de volta as que faltaram.

## Busca híbrida e rerank com LLM em vez de limite fixo

- **Contexto:** o primeiro RAG usava o vetor do texto inteiro e um limite de similaridade. No baseline, acertava só 47% das decisões (lembrar a certa ou ficar em silêncio).
- **Alternativas:** ajustar o limite; pedaços (*chunks*) com cabeçalho; prefixos de tarefa do embedding; busca híbrida (vetor + full-text) com RRF; reescrita da pergunta; rerank com LLM.
- **Escolha:** pedaços com cabeçalho, busca híbrida com Reciprocal Rank Fusion e rerank com LLM entre as 5 mais próximas. A reescrita da pergunta ficou disponível, mas desligada.
- **Por quê:** cada técnica foi ligada uma de cada vez e medida em 30 perguntas. Nenhum limite fixo passou de 57%; o rerank chegou a 97%, sem nenhuma lembrança errada. Os prefixos sozinhos até pioraram o recall@1 e só renderam junto com os pedaços e a busca híbrida. Com o rerank, a reescrita não melhorava as decisões, então ficou desligada para economizar uma chamada ao modelo. Detalhes em [Memória e RAG](memoria-e-rag.md).

## A memória como ferramenta fica desligada

- **Contexto:** além do RAG automático, foi criada a ferramenta `recall_memory`, para ela decidir sozinha quando lembrar (*agentic RAG*).
- **Alternativas:** deixar ligada; deixar opcional e desligada.
- **Escolha:** opcional, desligada por padrão (`MEMORY_RECALL_TOOL=false`).
- **Por quê:** o `qwen2.5:7b` não chamou a ferramenta nenhuma vez em 15 execuções do cenário feito para ela, e só por ela estar na lista ele passou a salvar menos descobertas. Uma frase no prompt sobre ela derrubou o salvamento de 5/5 para 2/5. Uma ferramenta pode piorar o agente sem nunca ser usada. Com um modelo maior, vale ligar e medir de novo.

## Evals separados dos testes, com juiz que cita a fonte

- **Contexto:** testes com fake provam o código, mas não dizem como o modelo de verdade se comporta.
- **Alternativas:** testar à mão; um juiz LLM dando nota de 1 a 5; evals com checagens em código e um juiz que precisa mostrar a evidência.
- **Escolha:** evals fora do `pytest` e do CI, rodando cada cenário várias vezes e devolvendo taxas: recuperação (recall@k, MRR), agente (checagens de regras em código) e fidelidade com LLM-as-judge. O juiz quebra cada resumo em afirmações e precisa citar o trecho exato da página, e o código confere se a citação existe.
- **Por quê:** o modelo não responde sempre igual, então só taxas comparam um "antes e depois". Um juiz pequeno dando nota é ruído; uma citação conferida é verificável. O que dá para checar em código (como o idioma) não passa pelo juiz. O baseline também mostrou que diferenças menores que uns 15 pontos são ruído.

## Emoções em camadas, com regras puras

- **Contexto:** a capivara precisava de sentimentos críveis, que mudem com o tempo e com o que acontece, sem virar um `if humor == "feliz"`.
- **Alternativas:** um estado só, mudado por regras soltas; deixar o LLM inventar como ela se sente; camadas com velocidades diferentes.
- **Escolha:** temperamento, linha de base, vínculo, necessidades, humor e emoções, cada um com sua velocidade, em regras puras com o tempo passado de fora. O prompt descreve como ela se sente e nunca manda sentir.
- **Por quê:** cada camada é simples, e a profundidade vem da interação. Com o tempo injetado, uma semana inteira foi simulada num script: isso mostrou que uma conversa curta enchia o vínculo de uma vez, e a mágoa passou a frear a recuperação. Detalhes em [Vida emocional](vida-emocional.md).

## Estado em arquivos que uma pessoa lê

- **Contexto:** sugestões, cartas, respostas e diário precisam sobreviver a reinícios, e o criador quer acompanhar tudo pelo Explorer.
- **Alternativas:** estado na memória do processo; tabelas no banco; Markdown com linhas de estado.
- **Escolha:** cada coisa é um Markdown com linhas como `- **Situação:** pendente`. Linha ausente vale o padrão, e uma grafia digitada à mão ("construida") também é aceita.
- **Por quê:** o estado sobrevive a reinícios, o criador vê e edita sem ferramenta, e um formato novo não quebra os arquivos antigos (como uma coluna com `default` numa migration). Separar "sentir" de "ler" em registros diferentes garantiu que ela se emocione com cada resposta uma vez só, mesmo depois de reiniciar.

## Voz local, como borda

- **Contexto:** conversar em voz alta com ela, sem custo e sem mandar áudio para fora.
- **Alternativas:** TTS e STT na nuvem; modelos locais; um modelo de voz que imita personagens.
- **Escolha:** Piper ou Kokoro para falar e faster-whisper para ouvir, todos locais. A voz entra e sai nas bordas: o `Conversation` continua trabalhando com texto. O áudio vai para o mundo em base64 dentro do JSON.
- **Por quê:** offline e gratuito, e o texto convive com a voz: perder a voz nunca derruba a conversa. Um modelo de vozes de personagens foi descartado porque, além da licença GPL, imitava vozes de dubladores reais. Entregar ao Whisper as amostras prontas (float32 a 16 kHz) contornou uma versão quebrada do decodificador, em vez de travar a dependência.

## Wikipedia como plano B da busca

- **Contexto:** 14 de 48 buscas tinham voltado vazias, e o motivo era o backend do DuckDuckGo bloqueado, não a pergunta.
- **Alternativas:** trocar só o backend da biblioteca de busca; usar a "Wikipedia" da própria biblioteca; chamar a busca full-text da API da Wikipedia.
- **Escolha:** quando a busca não acha nada ou falha, ela tenta a busca full-text da Wikipedia, com o contato exigido pela API como configuração.
- **Por quê:** a "Wikipedia" da biblioteca procura só pelo título, então trocar o backend teria passado nos testes e não funcionaria de verdade. A política da API (recusa quem não se identifica) virou configuração, em vez de um User-Agent inventado.

## Modelo sempre pronto e GPU para ele

- **Contexto:** a primeira resposta chegou a levar 100 s, dos quais só uns 10 s eram trabalho do modelo. O resto era carregar o modelo do disco.
- **Alternativas:** aceitar a demora; um modelo menor; manter o modelo carregado.
- **Escolha:** o cérebro carrega o modelo assim que liga (*warm-up*), em segundo plano; o Ollama mantém o modelo carregado por 30 min (`keep_alive`); o contexto subiu para 8192 tokens; o mundo ficou limitado a 30 FPS.
- **Por quê:** medir separou tempo de trabalho de tempo de espera. O contexto padrão de 4096 cortaria a personalidade dela depois de umas 15 mensagens, sem aviso. E o modelo divide a GPU com o mundo: limitar o FPS sobra GPU para ela pensar.

## psycopg puro com libpq assinado no Windows

- **Contexto:** o Smart App Control do Windows 11 bloqueou a DLL não assinada do `psycopg[binary]`.
- **Alternativas:** desligar a proteção do sistema; compilar a extensão; usar a implementação pura em Python com um `libpq` assinado.
- **Escolha:** no Windows, `psycopg` puro, com as DLLs assinadas do pacote oficial de binários do PostgreSQL no PATH. Nos outros sistemas, `psycopg[binary]`.
- **Por quê:** resolve sem enfraquecer a segurança da máquina. A hipótese foi testada no menor pedaço possível (carregar só o `libpq.dll` com `ctypes`), e as DLLs foram conferidas pelo SHA-256 publicado e pela assinatura antes de entrar no PATH.

## O mundo pede ao cérebro em vez de ler o disco

- **Contexto:** o Godot lia direto a pasta de descobertas (Markdown, PNGs, o histórico de buscas), conhecia a regra do nome dos arquivos e até lia o `brain/.env`.
- **Alternativas:** manter a leitura de disco; servir os arquivos por HTTP; pedidos e respostas no WebSocket que já existia.
- **Escolha:** pedidos com `request_id` (`list_drawings`, `get_discovery`...), respondidos só para quem perguntou, com títulos prontos e PNGs em base64, um por pedido. O contrato é um JSON Schema gerado dos modelos Pydantic, em [`docs/protocol/`](protocol/README.md), e um teste valida mensagens reais contra ele.
- **Por quê:** o mundo vira um cliente qualquer, que não sabe onde os arquivos ficam nem como se chamam. Os desenhos têm uns 3 KB, então os 33% a mais do base64 não pesam, e tudo fica num canal só, coberto pelo contrato.

# Vida emocional da capivara

A capivara não tem um campo `humor = "feliz"`. Ela tem uma vida emocional em camadas, cada uma andando numa velocidade diferente, e o que ela sente num momento é o resultado delas juntas. Este documento explica cada camada a partir do código e mostra como o que ela sente muda o que ela diz, o que ela faz e como o corpo dela aparece no mundo.

Tudo fica no domínio (`brain/src/domain/feelings/`), em regras puras: o tempo é passado de fora, em segundos, então dá para simular uma semana inteira num teste em milissegundos.

## As camadas, da mais lenta para a mais rápida

| Camada | Muda em | O que é | Arquivo |
|---|---|---|---|
| **Temperamento** | nunca | Quem ela é: muito curiosa e alegre, razoavelmente paciente | `temperament.py` |
| **Linha de base** | semanas | O quanto uma fase longa moveu o "normal" dela | `baseline.py` |
| **Vínculo** | dias | A confiança no criador | `bond.py` |
| **Necessidades** | horas | Vínculo, novidade, competência, autonomia e conforto | `needs.py` |
| **Humor** | horas | A cor de fundo do dia | `mood.py` |
| **Emoções** | minutos a horas | 20 emoções, cada uma de 0 a 1 | `emotion.py` |

Cada camada é simples. A riqueza vem da interação: uma necessidade esquecida empurra emoções, as emoções movem o humor, o humor muda o peso dos próximos acontecimentos, e uma fase longa move a linha de base. Quem junta tudo é o `EmotionalLife` (`emotional_life.py`).

## Emoções e meia-vida

São 20 emoções. Cada uma tem uma **valência** (boa, ruim ou neutra), uma **agitação** (de 0, calma, a 1, inquieta) e uma **meia-vida**: o tempo para ela voltar metade do caminho até o nível de repouso.

| Emoção | Valência | Agitação | Meia-vida |
|---|---|---|---|
| Surpresa | neutra | 0,9 | 6 min |
| Maré boa (*flow*) | boa | 0,7 | 1,5 h |
| Alegria, determinação, irritação | boa, boa, ruim | 0,6 / 0,7 / 0,8 | 2 h |
| Curiosidade, entusiasmo, alívio, frustração | boa, boa, boa, ruim | 0,6 / 0,8 / 0,3 / 0,8 | 3 h |
| Tédio | ruim | 0,2 | 4 h |
| Orgulho | boa | 0,5 | 6 h |
| Impaciência | ruim | 0,7 | 8 h |
| Solidão, decepção | ruim | 0,3 / 0,4 | 12 h |
| Tristeza | ruim | 0,2 | 18 h |
| Gratidão, insegurança, apatia | boa, ruim, ruim | 0,4 / 0,5 / 0,05 | 24 h |
| Mágoa | ruim | 0,4 | 30 h |
| Conformismo (*resignation*) | ruim | 0,1 | 48 h |

O **decaimento é exponencial**, em direção ao nível de repouso:

```python
# emotion.py
remaining_share = math.pow(0.5, elapsed_hours / half_life_hours)
return resting + (value - resting) * remaining_share
```

Uma tristeza de 0,8, com meia-vida de 18 h, cai para 0,4 depois de 18 h e para 0,2 depois de 36 h. Por isso uma surpresa some em minutos e uma mágoa dura mais de um dia.

Quando algo acontece, a emoção recebe um impulso com **soma saturada**: quanto mais perto do limite, menor o passo. +0,5 sobre 0 dá 0,5, mas +0,5 sobre 0,8 dá 0,9. Nenhuma emoção passa de 1.

Do estado inteiro saem dois números que o resto do sistema usa:

- **Valência**: de -1 (tudo ruim) a 1 (tudo bom). A conta é `(boas - ruins) / (boas + ruins + 1)`. O `+1` mantém sentimentos fracos perto do neutro.
- **Agitação**: a média da agitação de cada emoção, pesada pela intensidade. Sem sentir nada, fica em 0,3.

## Temperamento

O temperamento é fixo. Os valores padrão descrevem a capivara:

| Traço | Valor | Efeito |
|---|---|---|
| Curiosidade | 0,9 | Curiosidade em repouso: 0,9 × 0,5 = **0,45** |
| Alegria | 0,8 | Alegria em repouso: 0,8 × 0,4 = **0,32**. Coisas boas pesam 0,7 + 0,6 × 0,8 = **1,18×** |
| Paciência | 0,6 | A autonomia se esvazia a 1,5 − 0,6 = **0,9×** enquanto ela espera um pedido |
| Sensibilidade | 0,5 | Coisas ruins pesam 0,6 + 0,8 × 0,5 = **1,0×** |
| Resiliência | 0,7 | As meias-vidas das emoções ruins ficam multiplicadas por 1,5 − 0,7 = **0,8×** |

É o temperamento que define o **nível de repouso**: sem nada acontecendo, ela volta a ser curiosa e alegre. Isso é homeostase: um *set point* para onde ela sempre volta.

## Humor

O humor é uma média lenta do que ela sente, com meia-vida de 6 h. Uma busca que deu errado não estraga o dia.

Ele muda o peso dos próximos acontecimentos:

```python
# mood.py
negative_impact = 1.0 - 0.4 * valence  # bom humor (0,4): coisas ruins pesam 0,84×
positive_impact = 1.0 + 0.3 * valence  # mau humor (-0,4): coisas boas pesam 0,88×
```

A cada dia novo, ela também acorda um pouco melhor ou pior, ao acaso: o `day_spirit`, entre -0,1 e +0,1, soma no alvo do humor daquele dia.

## Linha de base

Uma fase longa muda o "normal" dela. A linha de base vai de -0,5 a +0,5 e anda devagar, com meia-vida de **72 h**, em direção à metade da distância entre o humor atual e o humor natural do temperamento. Uma tarde ruim não muda quem ela é; uma semana ruim muda um pouco.

Uma linha de base baixa diminui a curiosidade e a alegria em repouso, e deixa um pouco de tristeza mesmo quando nada acontece (`0,4` por unidade perdida). Quando o humor volta ao normal, a linha de base volta também.

## Necessidades

Inspiradas na teoria da autodeterminação, mais a novidade:

| Necessidade | O que enche | Esvazia sozinha em |
|---|---|---|
| **Vínculo** | Conversar com o criador, ler a resposta de uma carta | 144 h (6 dias) |
| **Novidade** | Achar algo numa pesquisa, salvar uma descoberta, reparar em algo no mundo | 30 h |
| **Competência** | Pesquisas que dão certo, descobertas salvas | 240 h (quase só sobe e desce com acertos e erros) |
| **Autonomia** | Ver um pedido dela construído no mundo | 240 h, mas só enquanto algum pedido espera |
| **Conforto** | Visitar o lago, o pote de comida ou a casinha | 40 h |

O ritmo também depende do resto:

- **Vínculo:** com confiança alta, ela sente falta mais devagar (`1,3 − 0,6 × confiança`: 0,88× com a confiança padrão de 0,7).
- **Autonomia:** sem pedido esperando, ela se recupera em uns dois dias.
- **Conforto:** bem cuidada (conforto ≥ 0,7), o vínculo, a novidade e a competência esvaziam 15% mais devagar.
- **Sono:** um intervalo de mais de 1 h sem atualização quer dizer que o cérebro estava desligado, então ela estava dormindo. Dormindo, a novidade, a competência e o conforto não caem, e o conforto se recupera (1/8 por hora). O tempo longe é vivido em passos de 15 min, até 14 dias, para emoções, necessidades e degraus andarem juntos.

## Escadas e histerese

Cada necessidade tem uma **escada**: os degraus que ela desce enquanto a necessidade fica esquecida. A do vínculo, por exemplo:

| Degrau | Entra abaixo de | Mantém vivo (piso) | Segura (teto) |
|---|---|---|---|
| conectada | — | — | — |
| com saudade | 0,92 | solidão 0,2 | — |
| sozinha | 0,83 | solidão 0,5, tristeza 0,15 | — |
| triste | 0,67 | solidão 0,6, tristeza 0,45 | alegria 0,5 |
| magoada | 0,5 | solidão 0,6, tristeza 0,55, mágoa 0,5, insegurança 0,4 | alegria 0,35, curiosidade 0,6 |
| apática | 0,17 | apatia 0,7, tristeza 0,6, solidão 0,5 | curiosidade 0,25, alegria 0,2, entusiasmo 0,1 |

Os **pisos** são emoções que o degrau mantém vivas; os **tetos** são emoções que ele segura (a apatia não deixa a curiosidade crescer). As outras escadas seguem a mesma ideia: novidade (inquieta → entediada → irritada → desanimada), competência (frustrada → insegura → derrotada), autonomia (impaciente → decepcionada → conformada) e conforto (precisando de pausa → esgotada).

Três detalhes evitam que ela pareça uma máquina:

- **Histerese:** para subir de volta um degrau, a necessidade precisa passar **0,04 acima** da linha que a fez cair. Sem isso, uma necessidade parada em cima da linha a faria piscar entre dois degraus.
- **Jitter:** cada linha anda até 0,03 para cima ou para baixo, sorteada de novo a cada mudança de degrau, então ela nunca cai exatamente na mesma hora.
- **Transição suave:** um degrau novo leva cerca de 1 h para fazer efeito (meia-vida de 1 h), em vez de mudar tudo num instante.

```python
# ladders.py
while index > 0 and level >= rungs[index].enters_below + jitter + HYSTERESIS_MARGIN:
    index -= 1
```

## Contágio, ruminação e maré boa

As emoções se alimentam e se acalmam umas às outras (`contagion.py`). Cada regra é uma taxa por hora, proporcional à força da emoção de origem, e todas são calculadas a partir do mesmo estado, então a ordem não importa:

- A solidão vira tristeza e apaga a alegria e a curiosidade.
- O tédio vira irritação.
- A tristeza drena a energia (apatia) e o interesse.
- A curiosidade e a alegria são os antídotos: diminuem o tédio e a tristeza.
- *Broaden and build*: o entusiasmo e a maré boa ampliam a curiosidade e empurram o tédio e a frustração para longe.

E há regras que dependem de mais de uma coisa:

- **Ruminação:** com tristeza ≥ 0,45 e alguma necessidade abaixo de 0,5, ela fica remoendo o que falta, e isso alimenta mais tristeza, decepção e insegurança. É uma espiral, e por isso ela precisa de algo de fora (uma conversa, uma descoberta) para sair.
- **Frustração que vira outra coisa:** acima de 0,4, a frustração vira **determinação** se ela ainda acredita em si (competência ≥ 0,4), ou **insegurança** se não acredita.
- **Esperar sem controle:** com a autonomia baixa, a impaciência e a decepção viram conformismo aos poucos.
- **Maré boa:** com entusiasmo e alegria acima de 0,5 ao mesmo tempo, nasce o *flow*. Acima de 0,8, o entusiasmo esfria e ela volta devagar, sem euforia infinita.

## Appraisal: o que cada acontecimento significa para ela

Pela teoria da avaliação (*appraisal theory*), a emoção não vem do acontecimento, mas do que ele significa para quem vive. Cada tipo de acontecimento (`appraisal.py`) vira impulsos nas emoções e mudanças nas necessidades. Alguns exemplos:

| Acontecimento | Emoções | Necessidades |
|---|---|---|
| Salvou uma descoberta | orgulho +0,45, alegria +0,3, frustração −0,3 | competência +0,25, novidade +0,15 |
| A pesquisa não achou nada | frustração +0,3, decepção +0,1 | competência −0,12 |
| Repetiu uma pesquisa | tédio +0,25 | novidade −0,08 |
| Um pedido dela foi construído | surpresa, alegria +0,5, gratidão +0,4, conformismo −0,6 | autonomia +1,0, vínculo +0,15 |
| O criador respondeu uma carta | alegria +0,35, gratidão +0,3, solidão −0,3 | vínculo +0,15 |
| Visitou um lugar de conforto | irritação −0,35, frustração −0,3, tristeza −0,25 | conforto +0,45 |

O mesmo acontecimento nunca chega igual duas vezes:

- **Temperamento e humor:** impulsos que aumentam uma emoção ruim são multiplicados pela sensibilidade e pelo mau humor; os que aumentam uma boa, pela alegria do temperamento e pelo bom humor. Impulsos que acalmam não são multiplicados.
- **Habituação:** a segunda vez em pouco tempo chega a 2/3, a terceira à metade (a familiaridade some com meia-vida de 2 h). Fracassos não se habituam: continuam doendo.
- **Sequências:** acertos seguidos dão entusiasmo (+0,08 por acerto, até +0,4). Cada fracasso seguido faz a próxima frustração doer 50% mais.
- **Ruído:** cada impulso chega entre 85% e 115% do tamanho.

**Reencontro e vínculo** (`bond.py`): menos de 12 h longe é só uma conversa. Mais que isso é um reencontro, com alegria, alívio e surpresa proporcionais ao tempo longe. Depois de 48 h vem também um pouco de mágoa e uma pequena perda de confiança. A mágoa freia o quanto a conversa enche o vínculo: ela vai se aquecendo de novo ao longo de algumas conversas.

## Como as emoções mudam a voz e o corpo

### No que ela diz

A cada ciclo, o `FeelingsVoice` (`brain/src/application/feelings_voice.py`) pergunta ao coração como ela está. O `feelings_narrator.py` transforma isso em frases em português para a voz interior dela:

- as até 3 emoções mais fortes acima de 0,25, com "um pouco" ou "bem" conforme a intensidade;
- as causas, a partir do degrau de cada escada ("Faz 2 dias que o criador não conversa com você, e você sente saudade.");
- as espirais ("Você não para de pensar no que está faltando.", "Você está numa maré boa");
- as vontades (as *tendências* de `behavior.py`): explorar assuntos ousados, mudar de assunto, tentar de outro jeito, sentir falta de companhia, pouca energia, parar de pedir.

O prompt (`brain/prompts/feelings.md`) **descreve, nunca manda**: "Isso é o que você sente, não uma ordem. Deixe aparecer no seu jeito de pensar, de escolher o que fazer e de falar." O modelo decide como isso aparece nas falas, no diário e nas cartas. Um eval com LLM-as-judge confere se o tom da fala combina com o estado: [72% das execuções no baseline](../brain/evals/reports/2026-11-24-feelings-baseline.md).

A voz sintetizada (Piper ou Kokoro) tem timbre e velocidade fixos. O que muda com a emoção é o que ela fala, não o som da voz.

### No que ela faz

- **Ritmo:** `cycle_pace` multiplica o tempo entre dois ciclos: até 2× mais devagar quando ela está apática ou triste, até 0,6× (mais rápido) numa maré boa.
- **Autocuidado:** com o conforto abaixo de 0,5, ela sempre vai se cuidar. Pra baixo (valência < −0,2), vai metade das vezes. Tristeza e solidão procuram a casinha; tédio e irritação, o lago; cansaço sem emoção forte, o pote de comida. Em 20% das vezes ela escolhe um lugar inesperado, como qualquer um faria.
- **Cartas:** quando sente saudade, ela escreve cartas para o criador e deixa na caixa de correio.

### No corpo, no Godot

O cérebro manda ao mundo uma mensagem `feelings` com a emoção mais forte (ou `calm`, quando nada passa de 0,2), a valência e a agitação. O mundo só mostra; quem decide é o cérebro.

- **Andar e pausas** (`world/scripts/capybara_feelings.gd`): uma "vivacidade" (`valência × 0,7 + (agitação − 0,3) × 0,6`) leva a velocidade de 0,65× (pra baixo) a 1,1× (animada), e as pausas entre caminhadas de 2,2× a 0,6×.
- **Postura:** a cabeça cai até 9° na tristeza e levanta metade disso na alegria. A respiração vai de 0,7× a 1,5× conforme a agitação. As mudanças levam 2,5 s, então um sentimento novo "assenta" em vez de pular.
- **Símbolo:** um pequeno símbolo aparece em cima da cabeça para a emoção mais forte (`capybara_emote.gd`).

O diário guarda também o humor de cada entrada, mostrado em palavras na escrivaninha do mundo.

## Onde o estado fica salvo

O `Heart` (`brain/src/application/heart.py`) é a porta única para a vida emocional: o chat e o modo vivo usam o mesmo estado. Ele é salvo em `feelings.json`, na pasta de descobertas, então ela continua sentindo o que sentia depois de um reinício, e o tempo desligado conta como sono.

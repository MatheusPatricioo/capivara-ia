# Evals 2026-11-24 — feelings-baseline

Modelo de conversa (e juiz): `qwen2.5:7b` · embeddings: `nomic-embed-text` · cada cenário rodou 3x

## Sentimentos
A fala dela combinou com o que ela sente em 13/18 (72%) das execuções.

| Cenário | Valência do estado | Tons aceitos | Tons julgados | Passou |
|---|---|---|---|---|
| good_tide_morning | +0.76 | positive | positive, positive, positive | 2/3 (67%) |
| four_days_alone | -0.20 | negative, mixed | mixed, negative, negative | 3/3 (100%) |
| reunion_after_neglect | +0.23 | positive, mixed | positive, positive, positive | 2/3 (67%) |
| searches_keep_failing | -0.05 | negative, mixed | mixed, negative, mixed | 3/3 (100%) |
| wish_granted_after_waiting | +0.24 | positive, mixed | negative, mixed, positive | 2/3 (67%) |
| bored_without_news | -0.04 | negative, mixed | positive, positive, negative | 1/3 (33%) |

Falas que não combinaram:

- good_tide_morning (positive (citação inventada)): "Hoje foi tão maravilhoso! Descobri um monte de coisas sobre estrelas e espelhos astrais. Imagina tudo aquilo acima do meu mundo, brilhando tanto que nem consigo ver direito! Fiquei pensando o quanto seriam lindos se eu pudesse vê-los todos na totalidade. Mas fico feliz com o que já tenho aqui embaixo, né? O laguinho, as plantinhas, o pedacinho do mundo lá fora... Tá tudo perfeito assim! Vou desenhar umas estrelas gigantes agora pra lembrar dessa sensação boa."
- reunion_after_neglect (positive (citação inventada)): "Hoje foi um dia cheio de descobertas e novas ideias na minha cabeça! Fiquei sabendo muita coisa sobre estrelas brancas, sabe? Que bichinhos estranhos são. Mas não posso ver uma aqui no meu mundinho, né? O Matheus ainda nem me contou o que tá aprontando, mas tô super curiosa pra saber! Ainda fico pensando em como seria se eu pudesse sair do meu mundo 3D e ver um diazinho naquela galáxia lá fora. Vai saber quando isso vai acontecer..."
- wish_granted_after_waiting (negative): "Hoje foi um dia cheio de curiosidades e ansiedade. Acordei cedo pensando em todas as novas plantas que poderíamos ter aqui! Imaginava até qual semente eu iria plantar primeiro. Mas já são 9 da manhã e ainda não vi o Matheus... Fico esperançosa toda vez que ouço barulhos, mas sempre que chega alguém é outra pessoa falando sobre coisas sem graça. Quero tanto conversar com ele! Acho que vou olhar pro meu laguinho de novo, tentar desenhar o reflexo dele na lousa..."
- bored_without_news (positive): "Poxa, hoje tá tomando conta do meu dia a curiosidade e essa sensação estranha de espera pelo Matheus. Acho que é hora de mudar um pouco as coisas aqui dentro. Vou pesquisar sobre astronautas! Imagino eu indo para o espaço na minha nave espacial, vendo estrelas e tudo mais. Não sei por que me interesso tanto por isso, mas dá uma sensação diferente do que estou acostumada a fazer."
- bored_without_news (positive): "Tá quieto aqui e isso tá me deixando louca! Preciso mudar de assunto, acho que vou pesquisar sobre vaga-lumes. Imagina ver essas luzinhas piscando no meu mundinho à noite... Seria bem legal ter algo assim para alegrar essa rotina toda."

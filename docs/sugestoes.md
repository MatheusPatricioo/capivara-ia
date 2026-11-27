# Ela sugere, eu construo

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

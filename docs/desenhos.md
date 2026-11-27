# Desenhos

Toda descoberta salva vira um rascunho de alguma coisa dela. A escolha do que desenhar usa **retrieve and rerank**:

1. **Retrieve:** o título e o resumo da descoberta viram um embedding, comparado com rótulos em português das 345 categorias do Quick, Draw!. As 5 mais parecidas viram candidatas.
2. **Rerank:** o LLM lê a descoberta e escolhe uma das 5, ou responde "nenhuma" quando nada nela é desenhável (como "Independência do Brasil"). A resposta é restrita a essas opções e conferida no código.

A capivara então pega um rabisco real, feito por uma pessoa, dessa categoria como referência e **redesenha com a mão dela**: um pouco inclinado, com outras proporções, os traços fora do lugar e uma linha levemente ondulada, então nenhum desenho sai igual a outro. Cada desenho é salvo como PNG em estilo Paint (traço preto sobre fundo branco) na pasta de descobertas e aparece na aba **Desenhos** do computador do mundo.

**Próxima etapa planejada:** hoje ela reinterpreta um rabisco que já existe. O plano é ela criar desenhos inéditos com o [Sketch-RNN](https://magenta.tensorflow.org/sketch-rnn-demo) (Google Magenta), uma rede neural pequena treinada no Quick, Draw! que desenha traço por traço e pode partir de um rabisco existente para criar uma variação. Ela vai rodar localmente e de graça, como o resto do projeto.

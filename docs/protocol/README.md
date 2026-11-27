# Protocolo mundo ↔ cérebro

O cérebro (Python) e qualquer cliente visual (hoje, o mundo em Godot) conversam por WebSocket, em `ws://127.0.0.1:8765` por padrão, trocando mensagens JSON. Cada mensagem tem um campo `type` que diz qual é.

Os dois arquivos desta pasta são o contrato, em [JSON Schema](https://json-schema.org) (draft 2020-12):

| Arquivo | O que descreve |
|---|---|
| `world-to-brain.schema.json` | O que o cliente pode mandar: **eventos** (avisos sem resposta, como `noticed` e `creator_said`) e **pedidos** (como `list_drawings`). |
| `brain-to-world.schema.json` | O que o cérebro manda: **ordens para o corpo** (como `go_to`, `feelings` e `speech`, para todos os clientes) e **respostas** aos pedidos (só para quem perguntou). |

## Pedidos e respostas

Um pedido leva um `request_id` escolhido pelo cliente (letras, números, `_` e `-`, até 64 caracteres). O cérebro sempre responde com o mesmo `request_id`: com a resposta esperada ou com `request_failed`, cujo `reason` é `not_found`, `unreadable` ou `invalid_request`.

```json
{"type": "list_drawings", "request_id": "world-1"}
{"type": "drawing_list", "request_id": "world-1", "folder_path": "D:/capivara-descobertas",
 "drawings": [{"id": "2026-11-23-sol.png", "title": "sol", "saved_at": "2026-11-23T14:30", "done": false}]}

{"type": "get_drawing", "request_id": "world-2", "id": "2026-11-23-sol.png"}
{"type": "drawing", "request_id": "world-2", "id": "2026-11-23-sol.png", "title": "sol", "png_base64": "iVBORw0KGgo..."}
```

O cliente nunca lê a pasta de descobertas. Ele trata o `id` como uma etiqueta opaca, só para pedir o item depois, e mostra o `title`, que já vem pronto do cérebro. O `folder_path` serve apenas para exibir a pasta ou abri-la quando o cérebro roda na mesma máquina.

## Gerar de novo

Os schemas são gerados a partir dos modelos Pydantic em `brain/src/infrastructure/world_messages.py` e `world_requests.py`. Nunca edite os arquivos à mão. Depois de mudar uma mensagem, rode:

```powershell
cd brain
python -m src.export_protocol_schema
```

Um teste (`test_protocol_schema.py`) falha enquanto os arquivos commitados estiverem desatualizados, e outro (`test_protocol_contract.py`) valida com a biblioteca `jsonschema` uma mensagem real de cada tipo contra estes arquivos, nos dois sentidos.

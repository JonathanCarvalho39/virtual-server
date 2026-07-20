# Mock Server - Guia de Referência

## Estrutura do Projeto

```
api/
  ├── usuarios/
  │   ├── get/
  │   │   ├── listar.json        → GET /api/usuarios
  │   │   └── buscar-por-id.json → GET /api/usuarios
  │   ├── post/
  │   │   └── criar.json         → POST /api/usuarios
  │   └── put/
  │       └── atualizar.json     → PUT /api/usuarios
  └── produtos/
      └── get/
          └── listar.json        → GET /api/produtos
```

- Cada pasta = uma parte da rota
- Pasta com nome de método HTTP (`get`, `post`, `put`, `delete`, etc.) define o método
- Arquivos `.json` dentro da pasta de método = cenários para aquela rota

---

## Estrutura do Arquivo JSON

```json
{
  "name": "Nome do cenário",
  "request": {
    "headers": {},
    "query": {},
    "body": {}
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {}
  }
}
```

### Campos

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `name` | Não | Nome descritivo do cenário |
| `request` | Não | Regras de matching da requisição |
| `response` | Sim | Resposta retornada pelo mock |
| `response.status` | Não | Código HTTP (padrão: 200) |
| `response.headers` | Não | Headers da resposta |
| `response.body` | Não | Corpo da resposta |

---

## Como Funciona o Matching

1. A requisição chega no catch-all router
2. Busca todos os cenários para a combinação `(rota, método)`
3. Ordena por especificidade (maior primeiro)
4. Testa cada cenário até encontrar um que corresponda
5. Retorna a resposta do primeiro cenário que fez match

---

## Tokens de Request

Usados no `request.headers`, `request.query` e `request.body` para definir regras de matching.

| Token | Descrição |
|-------|-----------|
| `/any/` | Qualquer valor (não nulo) |
| `/missing/` | Campo ausente |
| `/null/` | Valor null |
| `/empty/` | String vazia ou null |
| `/string/` | Valor do tipo string |
| `/number/` | Valor do tipo int ou float |
| `/boolean/` | Valor do tipo boolean |
| `/array/` | Valor do tipo array |
| `/object/` | Valor do tipo object |
| `/uuid/` | Valor no formato UUID |
| `/date/` | Valor no formato ISO date |
| `^regex$` | Expressão regular (ex: `^[0-9]{11}$`) |
| `valor_literal` | Comparação exata (ex: `"12345678901"`) |

---

## Tokens de Response

Usados no `response.body` para gerar valores dinâmicos.

| Token | Descrição |
|-------|-----------|
| `/uuid/` | Gera UUID random |
| `/now/` | Data/hora atual em ISO |
| `/timestamp/` | Timestamp unix atual |
| `/random/int/MIN/MAX/` | Inteiro entre MIN e MAX |
| `/random/string/TAMANHO/` | String aleatória de N caracteres |
| `/random/boolean/` | `true` ou `false` aleatório |
| `{{request.body.campo}}` | Copia valor do campo do body |
| `{{request.query.campo}}` | Copia valor do campo da query |
| `{{request.header.nome}}` | Copia valor do header |

---

## Especificidade (Prioridade)

Quando múltiplos cenários existem para a mesma rota/método, o sistema escolhe o mais específico:

| Tipo | Pontos | Exemplo |
|------|--------|---------|
| Literal | 3 | `"12345678901"` |
| Regex | 2 | `^[0-9]{11}$` |
| Token | 1 | `/any/` |

**Exemplo:**
- `cpf: "12345678901"` → 3 pontos (mais específico)
- `cpf: "^[0-9]{11}$"` → 2 pontos
- `cpf: "/any/"` → 1 ponto (menos específico)

O cenário com mais pontos é testado primeiro.

---

## Exemplo Completo

```json
{
  "name": "Criar usuário - sucesso",
  "request": {
    "body": {
      "nome": "/any/",
      "email": "/any/",
      "cpf": "^[0-9]{11}$"
    }
  },
  "response": {
    "status": 201,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "id": "/uuid/",
      "nome": "{{request.body.nome}}",
      "email": "{{request.body.email}}",
      "criadoEm": "/now/"
    }
  }
}
```

---

## Múltiplas Respostas

Crie vários arquivos `.json` na mesma pasta de método. O sistema escolhe o mais específico baseado no request.

**Exemplo:**
```
api/v1/usuarios/
  └── post/
      ├── criar.json          → qualquer POST (match amplo)
      ├── cpf-duplicado.json  → POST com cpf: "12345678901"
      └── email-invalido.json → POST com email sem @
```

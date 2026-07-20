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

O servidor aceita **dois formatos** de JSON:

### Formato Padrão

```json
{
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

### Formato Virtualização (compatível com ferramentas externas)

```json
{
  "request": {
    "header": {},
    "query_string": {},
    "parameters": {},
    "body": {}
  },
  "response": {
    "status": 200,
    "header": {
      "Content-Type": "application/json"
    },
    "body": {}
  }
}
```

> **Nota:** `header` é mapeado para `headers`, `query_string` para `query`. O campo `parameters` é ignorado.

---

## Como Funciona o Matching

1. A requisição chega no catch-all router
2. Busca todos os cenários para a combinação `(rota, método)`
3. Ordena por especificidade (maior primeiro)
4. Testa cada cenário até encontrar um que corresponda
5. Retorna a resposta do primeiro cenário que fez match

---

## Tokens de Request

Usados no `request.headers` (ou `header`) e `request.body` para definir regras de matching.

### Formato Padrão

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

### Formato Virtualização (Wildcards)

| Padrão | Descrição |
|--------|-----------|
| `$$.*$$` | Qualquer valor (wildcard) |
| `$$.*json.*$$` | Qualquer valor contendo "json" |
| `$$^\\d{1,11}$$` | Regex: 1 a 11 dígitos |
| `$$^true\|false$$` | Regex: true ou false |
| `valor_literal` | Comparação exata |

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
| Token/Wildcard | 1 | `/any/` ou `$$.*$$` |
| Objeto aninhado | +1 por campo | `{"ddi": "/any/"}` |

**Exemplo:**
- `cpf: "12345678901"` → 3 pontos (mais específico)
- `cpf: "^[0-9]{11}$"` → 2 pontos
- `cpf: "/any/"` → 1 ponto (menos específico)

O cenário com mais pontos é testado primeiro.

---

## Headers HTTP-Level

O servidor **ignora** os seguintes headers no matching (tratados em nível HTTP):
- `content-length`
- `host`
- `connection`
- `transfer-encoding`

---

## Importação de Pastas

É possível importar pastas completas via interface:

1. Clique no ícone de **ZIP** na barra lateral
2. Arraste um arquivo `.zip` ou clique para selecionar
3. Defina o destino (deixe vazio para a raiz da `api/`)
4. Clique em **Importar**

A pasta será extraída e todos os cenários serão carregados automaticamente.

---

## Exemplo Completo

### Formato Padrão

```json
{
  "request": {
    "headers": {
      "Content-Type": "application/json"
    },
    "query": {
      "id": "success"
    },
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

### Formato Virtualização

```json
{
  "request": {
    "header": {
      "Content-Type": "$$.*$$",
      "X-Pf-Authn-Api-State": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0_1"
    },
    "query_string": {
      "id": "success"
    },
    "parameters": {},
    "body": {
      "identifier": "$$.*$$",
      "bureau": "$$.*$$",
      "ticketSDC": "$$.*$$"
    }
  },
  "response": {
    "status": 202,
    "header": {
      "Content-Type": "application/json; charset=UTF-8"
    },
    "body": {
      "status": "SDC_IN_ANALYSIS",
      "_pf_authn_api_state": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0_2"
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

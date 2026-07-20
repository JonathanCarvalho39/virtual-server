# virtual-server

## Rodar via Docker

### Baixar a imagem

```bash
docker pull ghcr.io/jonathan-carvalho39/virtual-server/mock-server:latest
```

### Rodar o container

```bash
docker run -d -p 8000:8000 --name mock-server ghcr.io/jonathan-carvalho39/virtual-server/mock-server:latest
```

O servidor estará disponível em `http://localhost:8000`.

### Parar e remover

```bash
docker stop mock-server && docker rm mock-server
```

### Rodar com docker-compose

```bash
docker-compose up -d
```

### Parar com docker-compose

```bash
docker-compose down
```

## Comando não encontrado

Se receber `docker: command not found`, instale o Docker:

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER
```
Faça logout e login novamente após instalar.

**Mac:**
Baixe o [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**Windows:**
Baixe o [Docker Desktop](https://www.docker.com/products/docker-desktop/).

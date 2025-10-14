# Servidor Proxy para Resolver Mixed Content

## Problema
Quando o site é acessado via HTTPS (https://www.escolalog.com.br), o navegador bloqueia requisições HTTP para os dispositivos locais devido à política de "Mixed Content". Isso impede que as fotos sejam enviadas para os dispositivos de controle de acesso.

## Solução
Um servidor proxy local que roda em HTTP e faz as requisições para os dispositivos, contornando a limitação de Mixed Content.

## Como usar

### 1. Instalar dependências
```bash
npm install
```

### 2. Iniciar o servidor proxy
```bash
npm run proxy
```

O servidor irá rodar em `http://localhost:3001`

### 3. Verificar se está funcionando
Acesse: `http://localhost:3001/health`

Deve retornar:
```json
{
  "status": "ok",
  "message": "Proxy server is running"
}
```

## Como funciona

1. **Detecção automática**: O código JavaScript detecta se está em ambiente HTTPS
2. **Proxy automático**: Se estiver em HTTPS, usa o proxy local automaticamente
3. **Fallback**: Se o proxy não estiver disponível, tenta chamada direta (pode falhar em HTTPS)
4. **HTTP direto**: Se estiver em HTTP, faz chamadas diretas normalmente

## Logs

O servidor proxy mostra logs das requisições:
- `🔄 Proxy: POST http://170.238.212.153:8000/login.fcgi`
- `✅ Proxy: 200 OK`
- `❌ Erro no proxy: [mensagem de erro]`

## Comandos disponíveis

- `npm run proxy` - Inicia o servidor proxy
- `npm run dev` - Inicia o servidor de desenvolvimento
- `npm start` - Alias para `npm run proxy`

## Porta

O proxy roda na porta **3001** por padrão. Se precisar mudar, edite o arquivo `proxy-server.js`.
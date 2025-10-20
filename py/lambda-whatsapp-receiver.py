import json
import urllib.request
import time
import logging
import os
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuração do envio de WhatsApp
WHATSAPP_API_URL = "https://9097.bubblewhats.com/send-message"
WHATSAPP_AUTH_TOKEN = "YWEwMGViMGE1MmI1NTY4NjI2MWRhMGFh"

# Timeout para envio de WhatsApp
WHATSAPP_TIMEOUT = float(os.environ.get('WHATSAPP_TIMEOUT', '5.0'))

# Configuração do pool de conexões HTTP
opener = urllib.request.build_opener()
opener.addheaders = [('Content-Type', 'application/json')]
urllib.request.install_opener(opener)

# Supabase settings (for DB updates)
SUPABASE_URL = "https://sntyndufbxfzasnqvayc.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNudHluZHVmYnhmemFzbnF2YXljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxNzQ2ODcsImV4cCI6MjA3MTc1MDY4N30.Pv9CaNkpo2HMMAtPbyLz2AdR8ZyK1jtHbP78pR5CPSM"

def extract_phone_number(from_number: str) -> str:
    """Extrai o número de telefone do formato recebido."""
    if not from_number:
        return ""
    
    # Remove caracteres não numéricos
    digits = ''.join(ch for ch in str(from_number) if ch.isdigit())
    
    # Se já tem código do país (55), retorna como está
    if digits.startswith('55'):
        return digits
    
    # Se não tem código do país, adiciona 55
    return '55' + digits

def send_whatsapp_response(phone_number: str, message: str) -> bool:
    """Envia mensagem de resposta via API BubbleWhats."""
    try:
        if not phone_number or not message:
            logger.info('Número ou mensagem vazia; envio não realizado')
            return False
            
        headers = {
            "Authorization": WHATSAPP_AUTH_TOKEN,
            "Content-Type": "application/json",
        }
        
        payload = {
            "jid": phone_number,
            "message": message
        }
        
        logger.info(f'Enviando WhatsApp para {phone_number}: {message}')
        
        req = urllib.request.Request(
            url=WHATSAPP_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            method="POST",
            headers=headers,
        )
        
        with urllib.request.urlopen(req, timeout=WHATSAPP_TIMEOUT) as response:
            resp_text = response.read().decode()
            logger.info(f'WhatsApp enviado: status={response.status} resposta={resp_text}')
            return response.status in [200, 201, 202]
            
    except urllib.error.HTTPError as e:
        err = e.read().decode() if hasattr(e, 'read') else str(e)
        logger.error(f'Erro HTTP no envio WhatsApp: {e.code} - {err}')
        return False
    except Exception as e:
        logger.error(f'Erro no envio WhatsApp: {str(e)}')
        return False

def is_access_request_message(message: str) -> bool:
    """Verifica se a mensagem segue o padrão de solicitação de liberação de acesso."""
    import re
    
    if not message:
        return False
    
    # Padrão: "Olá, meu nome é [Nome] e o nome do meu filho é [Nome]. Eu quero liberar o acesso."
    # Permite variações de pontuação e espaçamento
    pattern = r'ol[aá],?\s+meu\s+nome\s+[eé]\s+(.+?)\s+e\s+o\s+nome\s+do\s+meu\s+filho\s+[eé]\s+(.+?)\.\s*eu\s+quero\s+liberar\s+o?\s*acesso\.?'
    
    # Busca case-insensitive
    match = re.search(pattern, message.lower().strip())
    
    if match:
        logger.info(f"Mensagem de liberação de acesso detectada - Pai: {match.group(1).strip()}, Filho: {match.group(2).strip()}")
        return True
    
    return False

def build_response_message() -> str:
    """Constrói a mensagem de resposta automática (curta e objetiva)."""
    return (
        "Para confirmar a liberação:\n"
        "1) Salve nosso número na agenda;\n"
        "2) Responda com seu telefone neste formato: 81988888888."
    )

def get_cors_headers():
    """Retorna headers de CORS padrão."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Content-Type": "application/json"
    }

def lambda_handler(event, context):
    start_time = time.time()
    
    try:
        logger.info("=== INÍCIO DA FUNÇÃO LAMBDA WHATSAPP RECEIVER ===")
        logger.info(f"Event completo: {json.dumps(event, indent=2, default=str)}")
        
        # Tratar requisições OPTIONS (preflight CORS)
        if event.get("httpMethod") == "OPTIONS" or event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
            logger.info("Requisição OPTIONS detectada - retornando headers CORS")
            return {
                "statusCode": 200,
                "headers": get_cors_headers(),
                "body": json.dumps({"message": "CORS preflight OK"})
            }
        
        # Parse do body da requisição
        if "body" in event and isinstance(event["body"], str):
            try:
                body = json.loads(event["body"])
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao fazer parse do JSON: {str(e)}")
                return {
                    "statusCode": 400,
                    "headers": get_cors_headers(),
                    "body": json.dumps({"error": "JSON inválido"})
                }
        else:
            body = event
            
        logger.info(f"Dados recebidos: {json.dumps(body, indent=2)}")
        
        # Validar se é uma mensagem válida
        if not body.get("fromNumber"):
            logger.warning("Mensagem sem fromNumber; ignorando")
            return {
                "statusCode": 200,
                "headers": get_cors_headers(),
                "body": json.dumps({"message": "Mensagem ignorada - sem fromNumber"})
            }
        
        # Extrair informações da mensagem
        from_number = body.get("fromNumber", "")
        message_body = body.get("body", "")
        is_group = body.get("isGroup", False)
        
        logger.info(f"Mensagem de: {from_number}")
        logger.info(f"Conteúdo: {message_body}")
        logger.info(f"É grupo: {is_group}")
        
        # Não responder mensagens de grupo
        if is_group:
            logger.info("Mensagem de grupo; não enviando resposta automática")
            return {
                "statusCode": 200,
                "headers": get_cors_headers(),
                "body": json.dumps({"message": "Mensagem de grupo ignorada"})
            }
        
        # Tratamento: número enviado (11 dígitos)
        submitted_digits = extract_submitted_phone(message_body)
        clean_phone = extract_phone_number(from_number)
        
        if submitted_digits:
            reply = process_phone_submission(submitted_digits)
            logger.info("Processamento de envio de número realizado")
            send_success = send_whatsapp_response(clean_phone, reply)
            
            execution_time = round((time.time() - start_time) * 1000, 2)
            logger.info(f"=== FIM DA FUNÇÃO - Tempo: {execution_time}ms ===")
            
            if send_success:
                return {
                    "statusCode": 200,
                    "headers": get_cors_headers(),
                    "body": json.dumps({
                        "message": "Processado com sucesso",
                        "reply": reply,
                        "phone": clean_phone,
                        "execution_time_ms": execution_time
                    })
                }
            else:
                return {
                    "statusCode": 500,
                    "headers": get_cors_headers(),
                    "body": json.dumps({
                        "error": "Falha ao enviar resposta automática",
                        "phone": clean_phone
                    })
                }
        
        # Caso: mensagem textual de solicitação -> enviar instruções curtas
        if is_access_request_message(message_body):
            response_message = build_response_message()
            
            logger.info("=== ENVIANDO RESPOSTA AUTOMÁTICA (instruções curtas) ===")
            send_success = send_whatsapp_response(clean_phone, response_message)
            
            execution_time = round((time.time() - start_time) * 1000, 2)
            logger.info(f"=== FIM DA FUNÇÃO - Tempo: {execution_time}ms ===")
            
            if send_success:
                return {
                    "statusCode": 200,
                    "headers": get_cors_headers(),
                    "body": json.dumps({
                        "message": "Resposta automática enviada com sucesso",
                        "phone": clean_phone,
                        "execution_time_ms": execution_time
                    })
                }
            else:
                return {
                    "statusCode": 500,
                    "headers": get_cors_headers(),
                    "body": json.dumps({
                        "error": "Falha ao enviar resposta automática",
                        "phone": clean_phone
                    })
                }
        
        # Mensagem não reconhecida
        logger.info("Mensagem não segue o padrão; não enviando resposta")
        return {
            "statusCode": 200,
            "headers": get_cors_headers(),
            "body": json.dumps({"message": "Mensagem não reconhecida"})
        }
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(f"Erro geral: {error_msg}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": get_cors_headers(),
            "body": json.dumps({
                "error": error_msg,
                "type": type(e).__name__
            })
        }


def normalize_local_phone(value: str) -> str:
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    if digits.startswith('55') and len(digits) > 11:
        digits = digits[-11:]
    elif len(digits) > 11:
        digits = digits[-11:]
    return digits


def extract_submitted_phone(message: str) -> str:
    """Retorna o telefone enviado na mensagem (11 dígitos) ou string vazia."""
    if not message:
        return ""
    digits = ''.join(ch for ch in str(message) if ch.isdigit())
    return digits[-11:] if len(digits) >= 11 else ""


def supabase_headers():
    return {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=minimal",
    }


def supabase_get(path: str, query: dict):
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        logger.warning("Supabase não configurado (URL/API_KEY)")
        return None
    import urllib.parse as up
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    q = up.urlencode(query, safe='*,()')
    req = urllib.request.Request(url=f"{url}?{q}", method="GET", headers=supabase_headers())
    try:
        with urllib.request.urlopen(req, timeout=WHATSAPP_TIMEOUT) as resp:
            text = resp.read().decode()
            return json.loads(text)
    except Exception as e:
        logger.error(f"Erro GET Supabase {path}: {e}")
        return None


def supabase_patch(path_with_filter: str, body: dict):
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        return False
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path_with_filter}"
    req = urllib.request.Request(url=url, data=json.dumps(body).encode('utf-8'), method="PATCH", headers=supabase_headers())
    try:
        with urllib.request.urlopen(req, timeout=WHATSAPP_TIMEOUT) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        logger.error(f"Erro PATCH Supabase {path_with_filter}: {e}")
        return False


def toggle_aluno_envio_for_phone(phone_digits: str) -> dict:
    """Procura aluno por telefone e alterna envio1/envio2. Retorna contadores e matches."""
    rows = supabase_get("alunos", {"select": "id,telefone_responsavel_1,telefone_responsavel_2,envio1,envio2", "limit": 10000}) or []
    toggled_true = 0
    toggled_false = 0
    found_ids = []
    for r in rows:
        t1 = normalize_local_phone(r.get("telefone_responsavel_1", ""))
        t2 = normalize_local_phone(r.get("telefone_responsavel_2", ""))
        # Match de responsáveis (1/2) independentemente do sucesso do PATCH
        if t1 == phone_digits or t2 == phone_digits:
            found_ids.append(r["id"])
        if t1 == phone_digits:
            current = bool(r.get("envio1") or False)
            newv = not current
            ok = supabase_patch(f"alunos?id=eq.{r['id']}", {"envio1": newv})
            if ok:
                toggled_true += 1 if newv else 0
                toggled_false += 1 if not newv else 0
        elif t2 == phone_digits:
            current = bool(r.get("envio2") or False)
            newv = not current
            ok = supabase_patch(f"alunos?id=eq.{r['id']}", {"envio2": newv})
            if ok:
                toggled_true += 1 if newv else 0
                toggled_false += 1 if not newv else 0
    return {"found_ids": found_ids, "toggled_true": toggled_true, "toggled_false": toggled_false}


def update_usuario_status_for_phone(phone_digits: str) -> dict:
    """Atualiza status_liberacao em usuarios para o telefone informado."""
    # Padrão ilike que ignora pontuação e espaços entre dígitos
    ilike_pattern = '*' + '*'.join(phone_digits) + '*'
    rows = supabase_get(
        "usuarios",
        {"select": "id,whatsapp,status_liberacao", "whatsapp": f"ilike.{ilike_pattern}", "limit": 100}
    ) or []
    changed_to = None
    updated_ids = []
    for r in rows:
        # Confirmar match exato pelos 11 dígitos finais
        norm = normalize_local_phone(r.get("whatsapp", ""))
        if norm != phone_digits:
            continue
        current = (r.get("status_liberacao") or "").strip()
        newv = "Liberado" if current != "Liberado" else "NaoLiberado"
        ok = supabase_patch(f"usuarios?id=eq.{r['id']}", {"status_liberacao": newv})
        if ok:
            updated_ids.append(r["id"])
            changed_to = newv
    return {"updated_ids": updated_ids, "changed_to": changed_to}


def process_phone_submission(submitted_digits: str) -> str:
    """Processa envio do número: alterna flags e atualiza status; retorna mensagem."""
    alunos = toggle_aluno_envio_for_phone(submitted_digits)
    # Retornar suporte quando não houver responsável (1/2) vinculado em alunos
    if not alunos["found_ids"]:
        return "Não encontramos esse número de telefone em nosso sistema, fale com nosso suporte\n\nclicando aqui:\nhttp://wa.me/5511969039674"
    # Atualizar usuarios SOMENTE se houver aluno vinculado
    _ = update_usuario_status_for_phone(submitted_digits)
    # Mensagens baseadas exclusivamente nos toggles dos alunos
    if alunos["toggled_true"] > 0:
        return "Liberação concluída. Caso você não queira mais receber mensagens, envie seu número neste formato: 81988888888."
    if alunos["toggled_false"] > 0:
        return "Você não receberá mais mensagens. Para ativar novamente o serviço de mensagens, envie novamente seu número neste formato: 81988888888."
    return "Atualização concluída. Para ativar ou desativar o serviço de mensagens, envie seu número neste formato: 81988888888."
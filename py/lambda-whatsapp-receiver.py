import json
import urllib.request
import time
import logging
import os

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

def build_response_message() -> str:
    """Constrói a mensagem de resposta automática."""
    return (
        "*Mensagem Automática*\n\n"
        "Olá! Recebemos sua mensagem e estamos processando sua solicitação.\n\n"
        "📋 Nossa equipe analisará seu pedido e retornará em breve com uma resposta.\n\n"
        "🚀 Esse passo é muito importante, você precisa salvar nosso número na sua agenda, para receber quando seu filho(a) passa em um de nossos dispositivos.\n\n"
        "⏰ Tempo estimado de resposta: até 24 horas úteis.\n\n"
        "Obrigado pela sua paciência!\n\n"
        "Equipe Escola Log 📚"
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
        
        # Extrair número de telefone limpo
        clean_phone = extract_phone_number(from_number)
        if not clean_phone:
            logger.warning(f"Não foi possível extrair número válido de: {from_number}")
            return {
                "statusCode": 400,
                "headers": get_cors_headers(),
                "body": json.dumps({"error": "Número de telefone inválido"})
            }
        
        logger.info(f"Número limpo extraído: {clean_phone}")
        
        # Construir mensagem de resposta
        response_message = build_response_message()
        
        # Enviar resposta automática
        logger.info("=== ENVIANDO RESPOSTA AUTOMÁTICA ===")
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
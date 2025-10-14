import json
import urllib.request
import time
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SUPABASE_URL = "https://sntyndufbxfzasnqvayc.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNudHluZHVmYnhmemFzbnF2YXljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxNzQ2ODcsImV4cCI6MjA3MTc1MDY4N30.Pv9CaNkpo2HMMAtPbyLz2AdR8ZyK1jtHbP78pR5CPSM"

SUPABASE_TIMEOUT = 15.0
# Tempo máximo desejado para execução da Lambda (ms) — deixar margem para o limite real
EXECUTION_BUDGET_MS = int(os.environ.get('EXECUTION_BUDGET_MS', '2800'))
# Timeout curto para REST auxiliar (buscar aluno) para caber no orçamento
SUPABASE_REST_TIMEOUT = float(os.environ.get('SUPABASE_REST_TIMEOUT', '1.0'))
# Timeout curto para envio de WhatsApp para caber no orçamento
WHATSAPP_TIMEOUT = float(os.environ.get('WHATSAPP_TIMEOUT', '1.0'))

# Configuração do envio de WhatsApp
WHATSAPP_API_URL = "https://9097.bubblewhats.com/recursive-send-message"
WHATSAPP_AUTH_TOKEN = "YWEwMGViMGE1MmI1NTY4NjI2MWRhMGFh"

# Configuração do pool de conexões HTTP
opener = urllib.request.build_opener()
opener.addheaders = [('Content-Type', 'application/json')]
urllib.request.install_opener(opener)

def safe_int_cast(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def send_to_supabase(payload):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f'Tentando enviar para Supabase (tentativa {attempt + 1}/{max_retries}): {json.dumps(payload)}')
            headers = {
                "Content-Type": "application/json",
                "apikey": SUPABASE_API_KEY,
                "Authorization": f"Bearer {SUPABASE_API_KEY}",
                "Prefer": "return=minimal"
            }
            req = urllib.request.Request(
                url=f"{SUPABASE_URL}/rest/v1/logs",
                data=json.dumps(payload).encode('utf-8'),
                method="POST",
                headers=headers
            )
            logger.info(f'Requisição criada para: {SUPABASE_URL}/rest/v1/logs')
            with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
                response_data = response.read().decode()
                logger.info(f'Resposta do Supabase: {response.status}')
                logger.info(f'Conteúdo da resposta: {response_data}')
                return response.status in [200, 201, 204]
        except urllib.error.HTTPError as e:
            error_response = e.read().decode() if hasattr(e, 'read') else str(e)
            logger.error(f'Erro HTTP ao enviar para Supabase (tentativa {attempt + 1}): {e.code} - {error_response}')
            if attempt < max_retries - 1:
                logger.info(f'Aguardando 1 segundo antes da próxima tentativa...')
                time.sleep(1)
            else:
                logger.error(f'Falha após {max_retries} tentativas')
                return False
        except Exception as e:
            logger.error(f'Erro ao enviar para Supabase (tentativa {attempt + 1}): {str(e)}')
            if attempt < max_retries - 1:
                logger.info(f'Aguardando 1 segundo antes da próxima tentativa...')
                time.sleep(1)
            else:
                logger.error(f'Falha após {max_retries} tentativas')
                return False

def sanitize_phone_number(phone: str) -> str:
    """Remove caracteres não numéricos e adiciona prefixo 55 se necessário."""
    if not phone:
        return ""
    digits = ''.join(ch for ch in str(phone) if ch.isdigit())
    if not digits:
        return ""
    # Adicionar 55 se ainda não houver código do país
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits

def fetch_aluno_details_by_user_id(user_id_text: str):
    """Busca nome e telefones/flags de envio do aluno via Supabase REST usando id_control_id."""
    try:
        aluno_id = safe_int_cast(user_id_text, default=0)
        if aluno_id <= 0:
            logger.info('user_id não numérico ou inválido; skip envio WhatsApp')
            return None
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
        }
        # Montar URL REST
        select = "nome,telefone_responsavel_1,telefone_responsavel_2,envio1,envio2"
        url = f"{SUPABASE_URL}/rest/v1/alunos?select={select}&id_control_id=eq.{aluno_id}&soft_delete=eq.false"
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        # Timeout curto para não estourar orçamento
        with urllib.request.urlopen(req, timeout=SUPABASE_REST_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None
    except Exception as e:
        logger.error(f'Erro ao buscar dados do aluno: {str(e)}')
        return None

def build_whatsapp_message(aluno_nome: str, registro_hora_str: str) -> str:
    """Constrói a mensagem de WhatsApp com o template fornecido."""
    aluno_nome = aluno_nome or "Aluno"
    return (
        f"👋 Olá, Responsável pelo(a) aluno(a) \"{aluno_nome}\"\n\n"
        f"📍 Informamos que ele(a) acabou de ser identificado(a) em um de nossos dispositivos faciais no colégio.\n\n"
        f"🕒 Registro feito por volta de {registro_hora_str}.\n\n"
        f"Equipe Escola Log 📚\n"
        f"_Reaja a esta mensagem com um 👍 e salve nosso número para receber as mensagens de alertas_"
    )

def send_whatsapp(recipients_csv: str, message_text: str, interval: str = "1") -> bool:
    """Envia mensagem via API BubbleWhats para uma lista CSV de números."""
    try:
        if not recipients_csv or not message_text:
            logger.info('Sem destinatários ou mensagem; envio não realizado')
            return False
        headers = {
            "Authorization": WHATSAPP_AUTH_TOKEN,
            "Content-Type": "application/json",
        }
        payload = {
            "recipients": recipients_csv,
            "message": message_text,
            "interval": str(interval or "1"),
        }
        req = urllib.request.Request(
            url=WHATSAPP_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            method="POST",
            headers=headers,
        )
        # Timeout curto para caber no orçamento da Lambda
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

def cleanup_middle_logs_for_user(user_id, log_date):
    try:
        logger.info(f"Limpando logs do meio para user_id: {user_id}, data: {log_date}")
        
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Executar função de limpeza no Supabase
        cleanup_url = f"{SUPABASE_URL}/rest/v1/rpc/cleanup_aluno_dia_rpc"
        cleanup_payload = {
            "p_user_id": user_id,
            "p_dia": log_date
        }
        
        logger.info(f"URL da limpeza: {cleanup_url}")
        logger.info(f"Payload da limpeza: {json.dumps(cleanup_payload)}")
        
        req = urllib.request.Request(
            url=cleanup_url,
            data=json.dumps(cleanup_payload).encode('utf-8'),
            method="POST",
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            response_data = response.read().decode()
            logger.info(f"Limpeza executada com sucesso: {response.status}")
            logger.info(f"Resposta da limpeza: {response_data}")
            return response.status in [200, 201, 204]
            
    except urllib.error.HTTPError as e:
        error_response = e.read().decode() if hasattr(e, 'read') else str(e)
        logger.error(f"Erro HTTP ao limpar logs do meio: {e.code} - {error_response}")
        return False
    except Exception as e:
        logger.error(f"Erro ao limpar logs do meio: {str(e)}")
        return False


def lambda_handler(event, context):
    start_time = time.time()

    def elapsed_ms():
        return int((time.time() - start_time) * 1000)

    def remaining_ms():
        return max(EXECUTION_BUDGET_MS - elapsed_ms(), 0)
    try:
        logger.info("=== INÍCIO DA FUNÇÃO LAMBDA ===")
        body = json.loads(event["body"]) if "body" in event and isinstance(event["body"], str) else event
        logger.info(f"Dados recebidos: {json.dumps(body)}")

        if "object_changes" not in body or not body["object_changes"]:
            raise ValueError("Formato inválido: 'object_changes' não encontrado ou vazio")

        change = body["object_changes"][0]["values"]
        logger.info(f"Change extraído: {json.dumps(change)}")

        payload = {
            "id": safe_int_cast(change.get("id")),
            "time": safe_int_cast(change.get("time")),
            "event": safe_int_cast(change.get("event")),
            "device_id": safe_int_cast(change.get("device_id")),
            "identifier_id": safe_int_cast(change.get("identifier_id", 0)),
            "user_id": change.get("user_id", ""),
            "portal_id": safe_int_cast(change.get("portal_id", 0)),
            "identification_rule_id": safe_int_cast(change.get("identification_rule_id", 0)),
            "card_value": change.get("card_value", ""),
            "log_type_id": safe_int_cast(change.get("log_type_id", 0)),
            "qrcode_value": change.get("qrcode_value", ""),
            "pin_value": change.get("pin_value", ""),
            "confidence": change.get("confidence", ""),
            "mask": change.get("mask", "")
        }
        logger.info(f"Payload criado: {json.dumps(payload)}")

        # Enviar apenas para Supabase
        logger.info("=== ENVIANDO PARA SUPABASE ===")
        supabase_success = send_to_supabase(payload)
        logger.info(f"Supabase log criado: {supabase_success}")
        
        # Limpar logs do meio se necessário
        if supabase_success:
            logger.info("=== LIMPANDO LOGS DO MEIO ===")
            # Usar data atual para limpeza
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            cleanup_success = cleanup_middle_logs_for_user(change.get("user_id", ""), current_date)
            logger.info(f"Limpeza executada: {cleanup_success}")

            # Checar orçamento de tempo antes de seguir para WhatsApp
            budget_left = remaining_ms()
            logger.info(f"Orçamento de tempo restante antes do WhatsApp: {budget_left}ms (execução: {elapsed_ms()}ms)")
            if budget_left < 800:
                logger.info('Tempo insuficiente para enviar WhatsApp; pulando etapa de envio')
            else:
                # Enviar WhatsApp aos responsáveis (se envio1/envio2 TRUE)
                # Esta etapa usa timeouts curtos para caber no orçamento
                try:
                    logger.info("=== PREPARANDO ENVIO WHATSAPP ===")
                    aluno = fetch_aluno_details_by_user_id(change.get("user_id", ""))
                    if aluno:
                        envio1 = bool(aluno.get("envio1", False))
                        envio2 = bool(aluno.get("envio2", False))
                        phones = []
                        if envio1:
                            p1 = sanitize_phone_number(aluno.get("telefone_responsavel_1", ""))
                            if p1:
                                phones.append(p1)
                        if envio2:
                            p2 = sanitize_phone_number(aluno.get("telefone_responsavel_2", ""))
                            if p2:
                                phones.append(p2)
                        if phones:
                            # Hora aproximada do registro com base na hora local
                            from datetime import datetime
                            try:
                                registro_hora = datetime.now().strftime("%H:%M")
                            except Exception:
                                registro_hora = "agora"
                            msg = build_whatsapp_message(aluno.get("nome", "Aluno"), registro_hora)
                            recipients_csv = ", ".join(phones)
                            sent = send_whatsapp(recipients_csv, msg, interval="1")
                            logger.info(f"WhatsApp enviado: {sent} para {recipients_csv}")
                        else:
                            logger.info('Nenhum destinatário habilitado (envio1/envio2 FALSE ou telefones ausentes)')
                    else:
                        logger.info('Aluno não encontrado para user_id; WhatsApp não enviado')
                except Exception as e:
                    logger.error(f'Falha ao preparar/enviar WhatsApp: {str(e)}')

        execution_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"=== FIM DA FUNÇÃO - Tempo: {execution_time}ms ===")
        
        if supabase_success:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Log criado com sucesso",
                    "execution_time_ms": execution_time
                })
            }
        else:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Falha ao criar log no Supabase"
                })
            }

    except Exception as e:
        import traceback
        logger.error(f"Erro geral: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }

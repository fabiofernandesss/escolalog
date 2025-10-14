import json
import urllib.request
import base64
import logging
import os
from datetime import datetime

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurações do Supabase
SUPABASE_URL = "https://sntyndufbxfzasnqvayc.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNudHluZHVmYnhmemFzbnF2YXljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxNzQ2ODcsImV4cCI6MjA3MTc1MDY4N30.Pv9CaNkpo2HMMAtPbyLz2AdR8ZyK1jtHbP78pR5CPSM"

# Timeouts (podem ser ajustados dinamicamente via payload)
# Recomenda-se configurar o timeout da Lambda >= 20s no AWS
SUPABASE_TIMEOUT = 20.0
DEVICE_LOGIN_TIMEOUT_DEFAULT = 6.0
DEVICE_UPDATE_TIMEOUT_DEFAULT = 12.0
DEVICE_RETRIES_DEFAULT = 3

def safe_int_cast(value, default=0):
    """Converte valor para int de forma segura."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def get_student_by_control_id(control_id):
    """Busca aluno pelo id_control_id."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Buscar aluno pelo id_control_id
        url = f"{SUPABASE_URL}/rest/v1/alunos?select=id,nome,id_control_id,foto_url&id_control_id=eq.{control_id}&soft_delete=eq.false"
        
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None
            
    except Exception as e:
        logger.error(f'Erro ao buscar aluno: {str(e)}')
        return None

def upload_photo_to_storage(file_data, file_name, content_type):
    """Faz upload da foto para o Supabase Storage."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": content_type
        }
        
        # Upload para o bucket fotos_alunos
        url = f"{SUPABASE_URL}/storage/v1/object/fotos_alunos/alunos/{file_name}"
        
        req = urllib.request.Request(url=url, data=file_data, method="POST", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            if response.status in [200, 201]:
                # Retornar URL pública
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/fotos_alunos/alunos/{file_name}"
                return public_url
            else:
                logger.error(f'Erro no upload: status={response.status}')
                return None
                
    except Exception as e:
        logger.error(f'Erro ao fazer upload: {str(e)}')
        return None

def update_student_photo_url(student_id, photo_url):
    """Atualiza a URL da foto do aluno no banco de dados."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "foto_url": photo_url
        }
        
        url = f"{SUPABASE_URL}/rest/v1/alunos?id=eq.{student_id}"
        
        req = urllib.request.Request(
            url=url, 
            data=json.dumps(payload).encode('utf-8'), 
            method="PATCH", 
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            return response.status in [200, 204]
            
    except Exception as e:
        logger.error(f'Erro ao atualizar foto no banco: {str(e)}')
        return False

def get_student_devices(student_id):
    """Busca todos os dispositivos associados ao aluno."""
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Buscar dispositivos do aluno
        url = f"{SUPABASE_URL}/rest/v1/aluno_dispositivo?select=id_do_aluno_no_dispositivo,dispositivos!inner(id,nome,ip,login,senha,status)&aluno=eq.{student_id}&dispositivos.status=eq.ATIVO"
        
        req = urllib.request.Request(url=url, method="GET", headers=headers)
        
        with urllib.request.urlopen(req, timeout=SUPABASE_TIMEOUT) as response:
            body = response.read().decode()
            data = json.loads(body)
            
            if isinstance(data, list):
                logger.info(f'Encontrados {len(data)} dispositivos para aluno {student_id}')
                return data
            return []
            
    except Exception as e:
        logger.error(f'Erro ao buscar dispositivos: {str(e)}')
        return []

def get_device_session(device_ip, login, password, retries=DEVICE_RETRIES_DEFAULT, timeout_seconds=DEVICE_LOGIN_TIMEOUT_DEFAULT):
    """Obtém sessão de autenticação do dispositivo com tentativas.
    Tenta primeiro via JSON (como usado no frontend), depois faz fallback para form-url-encoded.
    """
    ip_with_port = device_ip if ':' in device_ip else f"{device_ip}:80"
    url = f"http://{ip_with_port}/login.fcgi"

    for attempt in range(1, retries + 1):
        # 1) Tentativa com JSON
        try:
            json_body = json.dumps({"login": login, "password": password}).encode('utf-8')
            req_json = urllib.request.Request(
                url=url,
                data=json_body,
                method="POST",
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req_json, timeout=timeout_seconds) as response:
                body = response.read().decode()
                try:
                    data = json.loads(body)
                    session = data.get('session')
                    if session:
                        logger.info(f'Sessão (JSON) obtida para {device_ip}: {session[:10]}... (tentativa {attempt})')
                        return session
                    else:
                        logger.warning(f'Resposta JSON sem sessão de {device_ip} (tentativa {attempt})')
                except Exception:
                    logger.warning(f'Resposta não-JSON recebida de {device_ip} (tentativa {attempt})')
        except Exception as e:
            logger.warning(f'Erro JSON ao obter sessão de {device_ip} (tentativa {attempt}): {str(e)}')

        # 2) Fallback com form-url-encoded
        try:
            login_data = f"login={login}&password={password}".encode('utf-8')
            req_form = urllib.request.Request(
                url=url,
                data=login_data,
                method="POST",
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            with urllib.request.urlopen(req_form, timeout=timeout_seconds) as response:
                body = response.read().decode()
                # Alguns firmwares retornam 'session=...' em texto puro
                for line in body.split('\n'):
                    if line.strip().startswith('session='):
                        session = line.split('=', 1)[1].strip()
                        logger.info(f'Sessão (form) obtida para {device_ip}: {session[:10]}... (tentativa {attempt})')
                        return session
                logger.warning(f'Sessão não encontrada na resposta (form) de {device_ip} (tentativa {attempt})')
        except Exception as e:
            logger.warning(f'Erro form ao obter sessão de {device_ip} (tentativa {attempt}): {str(e)}')

    logger.error(f'Falha ao obter sessão de {device_ip} após {retries} tentativas')
    return None

def update_photo_on_device(device_ip, student_device_id, session, photo_data, retries=DEVICE_RETRIES_DEFAULT, timeout_seconds=DEVICE_UPDATE_TIMEOUT_DEFAULT):
    """Atualiza foto no dispositivo de controle de acesso com tentativas."""
    ip_with_port = device_ip if ':' in device_ip else f"{device_ip}:80"
    timestamp = int(datetime.now().timestamp())
    url = f"http://{ip_with_port}/user_set_image.fcgi?user_id={student_device_id}&session={session}&timestamp={timestamp}"
    headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(len(photo_data))
    }
    
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url=url,
                data=photo_data,
                method="POST",
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                if response.status == 200:
                    logger.info(f'Foto atualizada no dispositivo {device_ip} (tentativa {attempt}) para usuário {student_device_id}')
                    return True
                else:
                    logger.warning(f'Status {response.status} ao atualizar foto no dispositivo {device_ip} (tentativa {attempt})')
        except Exception as e:
            logger.warning(f'Erro ao atualizar foto no dispositivo {device_ip} (tentativa {attempt}): {str(e)}')
    
    logger.error(f'Falha ao atualizar foto no dispositivo {device_ip} após {retries} tentativas')
    return False

def update_devices_photos(student_id, photo_data, retries=DEVICE_RETRIES_DEFAULT, login_timeout=DEVICE_LOGIN_TIMEOUT_DEFAULT, update_timeout=DEVICE_UPDATE_TIMEOUT_DEFAULT):
    """Atualiza foto em todos os dispositivos do aluno. Falha se nenhum dispositivo sincronizar."""
    devices = get_student_devices(student_id)
    
    if not devices:
        logger.error(f'Nenhum dispositivo encontrado para aluno {student_id}')
        return False
    
    success_count = 0
    total_devices = len(devices)
    
    for device in devices:
        try:
            device_info = device['dispositivos']
            device_ip = device_info['ip'].rstrip('/')
            student_device_id = device['id_do_aluno_no_dispositivo']
            
            logger.info(f'Atualizando dispositivo {device_info["nome"]} ({device_ip})...')
            
            # Obter sessão com retries
            session = get_device_session(device_ip, device_info['login'], device_info['senha'], retries=retries, timeout_seconds=login_timeout)
            if not session:
                logger.error(f'Falha ao obter sessão do dispositivo {device_ip}')
                continue
            
            # Atualizar foto com retries
            if update_photo_on_device(device_ip, student_device_id, session, photo_data, retries=retries, timeout_seconds=update_timeout):
                success_count += 1
                logger.info(f'Sucesso no dispositivo {device_info["nome"]}')
            else:
                logger.error(f'Falha ao atualizar foto no dispositivo {device_info["nome"]}')
                
        except Exception as e:
            logger.error(f'Erro ao processar dispositivo: {str(e)}')
    
    logger.info(f'Dispositivos atualizados: {success_count}/{total_devices}')
    return success_count > 0

def lambda_handler(event, context):
    """Handler principal da Lambda para edição de fotos."""
    
    # CORS dinâmico: libera qualquer origem e trata preflight corretamente
    headers_in = event.get('headers') or {}
    origin = headers_in.get('origin') or headers_in.get('Origin') or '*'
    requested_headers = headers_in.get('access-control-request-headers', '*')
    cors_headers = {
        'Access-Control-Allow-Origin': origin if origin else '*',
        'Access-Control-Allow-Headers': requested_headers,
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Vary': 'Origin',
        'Content-Type': 'application/json'
    }
    
    # Log do evento recebido para debug
    logger.info(f'Evento recebido: {json.dumps(event)}')
    
    try:
        # Tratar OPTIONS (preflight) - suporte para diferentes formatos de evento
        http_method = (
            event.get('httpMethod') or 
            event.get('requestContext', {}).get('http', {}).get('method') or
            event.get('requestContext', {}).get('httpMethod')
        )
        logger.info(f'Método HTTP detectado: {http_method}')
        
        if http_method == 'OPTIONS':
            logger.info('Processando requisição OPTIONS (preflight) - sem restrições')
            options_headers = dict(cors_headers)
            options_headers['Access-Control-Max-Age'] = '86400'
            return {
                'statusCode': 204,
                'headers': options_headers,
                'body': ''
            }
        
        # Verificar método HTTP (aceitar POST ou qualquer método)
        if http_method and http_method not in ['POST', 'GET']:
            logger.info(f'Método HTTP recebido: {http_method} - processando como POST')
        
        # Continuar processamento independente do método
        
        # Parse do body
        body = event.get('body', '{}')
        # Alguns provedores enviam body em base64
        if event.get('isBase64Encoded'):
            try:
                body = base64.b64decode(body).decode('utf-8')
            except Exception as e:
                logger.warning(f'Falha ao decodificar body base64: {str(e)}')
        logger.info(f'Body recebido (tipo: {type(body)}): {body}')

        try:
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            logger.info(f'Dados parseados: {data}')
        except json.JSONDecodeError:
            logger.error('Erro ao parsear JSON no body da requisição')
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'JSON inválido no body da requisição'})
            }

        # Validar parâmetros obrigatórios
        control_id = data.get('id_control_id')
        photo_base64 = data.get('photo_base64')
        file_extension = data.get('file_extension', 'jpg')
        # Permitir controle via payload; padrão True para ambientes administrados
        sync_devices = bool(data.get('sync_devices', True))
        # Ajustes dinâmicos de timeout/retries vindos do payload
        device_retries = int(data.get('device_retries', DEVICE_RETRIES_DEFAULT))
        device_timeout_seconds = data.get('device_timeout_seconds')
        device_login_timeout = float(data.get('device_login_timeout', DEVICE_LOGIN_TIMEOUT_DEFAULT))
        device_update_timeout = float(data.get('device_update_timeout', DEVICE_UPDATE_TIMEOUT_DEFAULT))
        if device_timeout_seconds:
            # Se um timeout geral for informado, usar para ambas etapas
            try:
                device_timeout_seconds = float(device_timeout_seconds)
                device_login_timeout = device_timeout_seconds
                device_update_timeout = device_timeout_seconds
            except Exception:
                logger.warning('Valor inválido para device_timeout_seconds; usando padrões')
        supabase_timeout = float(data.get('supabase_timeout', SUPABASE_TIMEOUT))
        try:
            globals()['SUPABASE_TIMEOUT'] = supabase_timeout
        except Exception:
            logger.warning('Não foi possível ajustar SUPABASE_TIMEOUT dinamicamente')
        logger.info(f'Sincronização com dispositivos (sync_devices): {sync_devices}')
        logger.info(f'Config timeouts: retries={device_retries}, login_timeout={device_login_timeout}s, update_timeout={device_update_timeout}s, supabase_timeout={SUPABASE_TIMEOUT}s')

        if not control_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'id_control_id é obrigatório'})
            }

        if not photo_base64:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'photo_base64 é obrigatório'})
            }

        # Buscar aluno pelo id_control_id
        student = get_student_by_control_id(control_id)
        if not student:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Aluno não encontrado'})
            }

        # Decodificar imagem base64
        try:
            # Remover prefixo data:image se existir
            if ',' in photo_base64:
                photo_base64 = photo_base64.split(',')[1]
            photo_data = base64.b64decode(photo_base64)
        except Exception:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Formato de imagem inválido'})
            }

        # Gerar nome único para o arquivo
        timestamp = int(datetime.now().timestamp())
        file_name = f"aluno_{control_id}_{timestamp}.{file_extension}"

        # Determinar content-type
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif'
        }
        content_type = content_type_map.get(file_extension.lower(), 'image/jpeg')

        devices_updated = None
        if sync_devices:
            # Tentar sincronizar com dispositivos antes do upload, porém não bloquear fluxo
            logger.info('Iniciando sincronização de foto com dispositivos (antes do upload)...')
            devices_updated = update_devices_photos(student['id'], photo_data, retries=device_retries, login_timeout=device_login_timeout, update_timeout=device_update_timeout)
            if not devices_updated:
                logger.warning('Nenhum dispositivo foi atualizado. Prosseguindo com upload e atualização no banco.')
        else:
            logger.info('Sincronização de dispositivos desativada pelo cliente. Pulando etapa de dispositivos.')

        # Upload da foto (após sincronização)
        photo_url = upload_photo_to_storage(photo_data, file_name, content_type)
        if not photo_url:
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Erro ao fazer upload da foto'})
            }

        # Atualizar URL no banco de dados
        if not update_student_photo_url(student['id'], photo_url):
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Erro ao atualizar foto no banco de dados'})
            }

        # Preparar resposta com informações sobre dispositivos
        response_data = {
            'success': True,
            'message': 'Foto atualizada com sucesso',
            'student': {
                'id': student['id'],
                'nome': student['nome'],
                'id_control_id': student['id_control_id'],
                'foto_url': photo_url
            },
            'devices_updated': bool(devices_updated) if devices_updated is not None else False,
            'sync_devices': sync_devices,
            'partial_success': (sync_devices and not devices_updated) if devices_updated is not None else False
        }

        # Ajustar mensagem conforme sincronização
        if sync_devices:
            if devices_updated:
                response_data['message'] += ' e sincronizada com dispositivos'
            else:
                response_data['message'] += ' (dispositivos não sincronizados)'

        # Sucesso
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f'Erro na Lambda: {str(e)}')
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Erro interno: {str(e)}'})
        }
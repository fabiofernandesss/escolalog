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

# Timeouts
SUPABASE_TIMEOUT = 10.0

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
            "Content-Type": content_type,
            "Cache-Control": "3600"
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
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
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

def lambda_handler(event, context):
    """Handler principal da Lambda para edição de fotos."""
    
    # Headers CORS sem restrições
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': '*',
        'Access-Control-Allow-Credentials': 'true',
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
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Verificar método HTTP (aceitar POST ou qualquer método)
        if http_method and http_method not in ['POST', 'GET']:
            logger.info(f'Método HTTP recebido: {http_method} - processando como POST')
        
        # Continuar processamento independente do método
        
        # Parse do body
        body = event.get('body', '{}')
        logger.info(f'Body recebido (tipo: {type(body)}): {body}')
        
        try:
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            logger.info(f'Dados parseados: {data}')
        except json.JSONDecodeError as e:
            logger.error(f'Erro ao parsear JSON: {str(e)}')
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'JSON inválido no body da requisição'})
            }
        
        # Validar parâmetros obrigatórios
        control_id = data.get('id_control_id')
        photo_base64 = data.get('photo_base64')
        file_extension = data.get('file_extension', 'jpg')
        
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
        except Exception as e:
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
        
        # Upload da foto
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
        
        # Sucesso
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'message': 'Foto atualizada com sucesso',
                'student': {
                    'id': student['id'],
                    'nome': student['nome'],
                    'id_control_id': student['id_control_id'],
                    'foto_url': photo_url
                }
            })
        }
        
    except Exception as e:
        logger.error(f'Erro na Lambda: {str(e)}')
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Erro interno: {str(e)}'})
        }
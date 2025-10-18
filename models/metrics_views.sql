-- Views de Métricas Consistentes baseadas em frequencia_diaria
-- Ajuste os nomes das colunas conforme seu schema real

-- Top alunos mais presentes no mês atual por turma
CREATE OR REPLACE VIEW vw_aluno_mais_presente_mes AS
SELECT
  fd.turma_id,
  fd.aluno_id,
  a.nome AS aluno_nome,
  COUNT(*) AS total_presencas
FROM frequencia_diaria fd
JOIN alunos a ON a.id = fd.aluno_id
WHERE fd.tipo_frequencia = 'Presente'
  AND fd.dia >= date_trunc('month', CURRENT_DATE)
  AND fd.dia < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY fd.turma_id, fd.aluno_id, a.nome
ORDER BY fd.turma_id, total_presencas DESC;

-- Top alunos com mais faltas no mês atual por turma
CREATE OR REPLACE VIEW vw_aluno_mais_faltoso_mes AS
SELECT
  fd.turma_id,
  fd.aluno_id,
  a.nome AS aluno_nome,
  COUNT(*) AS total_faltas
FROM frequencia_diaria fd
JOIN alunos a ON a.id = fd.aluno_id
WHERE fd.tipo_frequencia = 'Falta'
  AND fd.dia >= date_trunc('month', CURRENT_DATE)
  AND fd.dia < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY fd.turma_id, fd.aluno_id, a.nome
ORDER BY fd.turma_id, total_faltas DESC;

-- Dias da semana com mais faltas por turma (mês atual)
CREATE OR REPLACE VIEW vw_dia_semana_mais_faltas AS
SELECT
  fd.turma_id,
  TO_CHAR(fd.dia, 'Day') AS dia_semana,
  COUNT(*) AS total_faltas
FROM frequencia_diaria fd
WHERE fd.tipo_frequencia = 'Falta'
  AND fd.dia >= date_trunc('month', CURRENT_DATE)
  AND fd.dia < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY fd.turma_id, TO_CHAR(fd.dia, 'Day')
ORDER BY fd.turma_id, total_faltas DESC;

-- Frequência diária por turma (presenças/faltas por dia)
CREATE OR REPLACE VIEW vw_frequencia_diaria_turma AS
SELECT
  fd.turma_id,
  fd.dia,
  SUM(CASE WHEN fd.tipo_frequencia = 'Presente' THEN 1 ELSE 0 END) AS total_presentes,
  SUM(CASE WHEN fd.tipo_frequencia = 'Falta' THEN 1 ELSE 0 END) AS total_faltas
FROM frequencia_diaria fd
WHERE fd.dia >= date_trunc('month', CURRENT_DATE)
  AND fd.dia < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY fd.turma_id, fd.dia
ORDER BY fd.turma_id, fd.dia DESC;

-- Atrasos de entrada (se houver coluna minutos/estado)
-- Ajuste os nomes abaixo conforme sua tabela de entrada/saida
-- Caso não tenha, remova esta view ou adapte ao seu modelo
CREATE OR REPLACE VIEW vw_atrasos_entrada AS
SELECT
  fd.turma_id,
  fd.aluno_id,
  a.nome AS aluno_nome,
  fd.minutos_atraso,
  'ATRASADO'::text AS status_entrada
FROM frequencia_diaria fd
JOIN alunos a ON a.id = fd.aluno_id
WHERE fd.minutos_atraso IS NOT NULL
  AND fd.minutos_atraso > 0
  AND fd.dia >= date_trunc('month', CURRENT_DATE)
  AND fd.dia < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month';

-- Resumo geral por turma (opcional)
-- Pode ser removido, pois foi retirado da UI
CREATE OR REPLACE VIEW vw_resumo_geral_turma AS
SELECT
  t.id AS turma_id,
  t.nome AS turma_nome,
  COUNT(DISTINCT fd.aluno_id) AS total_alunos
FROM turmas t
LEFT JOIN frequencia_diaria fd ON fd.turma_id = t.id
GROUP BY t.id, t.nome
ORDER BY t.nome;
-- =============================================
-- Script: Actualizar cámaras de sede Galapa
-- Fecha: 2026-03-14
-- Descripción: Reemplaza las cámaras genéricas de Galapa
--              con los nombres reales de las cámaras.
-- =============================================

-- Paso 1: Obtener el ID de la sede Galapa
SET @galapa_id = (SELECT id FROM sedes WHERE codigo = 'GAL' LIMIT 1);

-- Paso 2: Eliminar las cámaras actuales de Galapa
DELETE FROM camaras WHERE sede_id = @galapa_id;

-- Paso 3: Insertar las nuevas 9 cámaras
INSERT INTO camaras (nombre, sede_id, tipo, activo) VALUES
('Pasillo 403', @galapa_id, 'Refrigerada', 1),
('Pasillo 402', @galapa_id, 'Refrigerada', 1),
('Pasillo 401', @galapa_id, 'Refrigerada', 1),
('Pasillo 301', @galapa_id, 'Refrigerada', 1),
('Pasillo 201', @galapa_id, 'Refrigerada', 1),
('Pasillo 101', @galapa_id, 'Refrigerada', 1),
('Precava Refrigerado', @galapa_id, 'Refrigerada', 1),
('Precava Congelado', @galapa_id, 'Congelada', 1),
('Bahía', @galapa_id, 'Refrigerada', 1);

-- Paso 4: Verificar
SELECT c.id, c.nombre, c.tipo, c.activo, s.nombre AS sede
FROM camaras c
JOIN sedes s ON c.sede_id = s.id
WHERE s.codigo = 'GAL'
ORDER BY c.id;

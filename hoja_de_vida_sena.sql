-- =====================================================================
-- BASE DE DATOS: Sistema de Registro de Hojas de Vida (SENA)
-- Proyecto: Registro de Aprendices - Datos personales, académicos
--           y experiencia laboral
-- Motor: MySQL 8.x
-- Uso: Abrir MySQL Workbench > File > Open SQL Script > ejecutar (⚡)
-- =====================================================================

DROP DATABASE IF EXISTS hoja_de_vida_sena;
CREATE DATABASE hoja_de_vida_sena
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_spanish_ci;

USE hoja_de_vida_sena;

-- =====================================================================
-- TABLA: aprendices
-- Corresponde al FormularioDatos.jsx (paso 1)
-- =====================================================================
CREATE TABLE aprendices (
    id_aprendiz     INT AUTO_INCREMENT PRIMARY KEY,
    foto            VARCHAR(255)                        NULL,
    nombre          VARCHAR(150)                        NOT NULL,
    edad            TINYINT UNSIGNED                    NOT NULL,
    ciudad          VARCHAR(100)                        NOT NULL,
    correo          VARCHAR(150)                        NOT NULL,
    programa        VARCHAR(150)                        NOT NULL,
    ficha           INT                                 NOT NULL,
    jornada         ENUM('Mañana','Tarde','Noche','Mixta') NOT NULL DEFAULT 'Mañana',
    fecha_registro  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_correo UNIQUE (correo)
) ENGINE = InnoDB;

-- =====================================================================
-- TABLA: usuarios
-- Cuentas de acceso al sistema (login)
-- =====================================================================
CREATE TABLE usuarios (
    id_usuario       INT AUTO_INCREMENT PRIMARY KEY,
    nombre_usuario   VARCHAR(50)                         NOT NULL,
    correo           VARCHAR(150)                        NOT NULL,
    password         VARCHAR(255)                        NOT NULL,  -- guardar el HASH, nunca la contraseña en texto plano
    rol              ENUM('Administrador','Instructor','Aprendiz') NOT NULL DEFAULT 'Aprendiz',
    estado           ENUM('Activo','Inactivo')           NOT NULL DEFAULT 'Activo',
    fecha_nacimiento DATE                                NOT NULL,
    fecha_creacion   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuario_nombre UNIQUE (nombre_usuario),
    CONSTRAINT uq_usuario_correo UNIQUE (correo)
) ENGINE = InnoDB;

-- =====================================================================
-- RELACIÓN: aprendices -> usuarios (1:1)
-- Se agrega la columna id_usuario a aprendices y se enlaza con usuarios.
-- UNIQUE: un usuario solo puede pertenecer a un aprendiz.
-- NULL: un aprendiz puede existir sin usuario todavía.
-- =====================================================================
ALTER TABLE aprendices
ADD COLUMN id_usuario INT NULL UNIQUE,
ADD CONSTRAINT fk_aprendiz_usuario
FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario);

-- =====================================================================
-- TABLA: informacion_academica
-- Corresponde al FormularioAcademico.jsx (paso 2)
-- Relación 1:1 con aprendices (cada aprendiz tiene un registro académico)
-- =====================================================================
CREATE TABLE informacion_academica (
    id_academico    INT AUTO_INCREMENT PRIMARY KEY,
    id_aprendiz     INT                                 NOT NULL,
    nivel           VARCHAR(100)                        NOT NULL,
    titulo          VARCHAR(150)                        NOT NULL,
    institucion     VARCHAR(150)                        NOT NULL,
    graduacion      VARCHAR(10)                         NOT NULL,
    CONSTRAINT fk_academico_aprendiz
        FOREIGN KEY (id_aprendiz) REFERENCES aprendices (id_aprendiz)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_academico_aprendiz UNIQUE (id_aprendiz)
) ENGINE = InnoDB;

-- =====================================================================
-- TABLA: cursos
-- Corresponde a la lista dinámica "cursos" (arreglo) en FormularioAcademico.jsx
-- Relación 1:N con informacion_academica
-- =====================================================================
CREATE TABLE cursos (
    id_curso        INT AUTO_INCREMENT PRIMARY KEY,
    id_academico    INT                                 NOT NULL,
    nombre_curso    VARCHAR(150)                        NOT NULL,
    CONSTRAINT fk_curso_academico
        FOREIGN KEY (id_academico) REFERENCES informacion_academica (id_academico)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;

-- =====================================================================
-- TABLA: experiencias
-- Corresponde al arreglo "experiencias" en FormularioExperiencia.jsx
-- Relación 1:N con aprendices
-- =====================================================================
CREATE TABLE experiencias (
    id_experiencia  INT AUTO_INCREMENT PRIMARY KEY,
    id_aprendiz     INT                                 NOT NULL,
    empresa         VARCHAR(150)                        NOT NULL,
    cargo           VARCHAR(150)                        NOT NULL,
    tiempo          VARCHAR(50)                         NULL,
    CONSTRAINT fk_experiencia_aprendiz
        FOREIGN KEY (id_aprendiz) REFERENCES aprendices (id_aprendiz)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;

-- =====================================================================
-- TABLA: habilidades
-- Corresponde al arreglo "habilidades" dentro de cada experiencia
-- Relación 1:N con experiencias
-- =====================================================================
CREATE TABLE habilidades (
    id_habilidad    INT AUTO_INCREMENT PRIMARY KEY,
    id_experiencia  INT                                 NOT NULL,
    nombre_habilidad VARCHAR(100)                       NOT NULL,
    CONSTRAINT fk_habilidad_experiencia
        FOREIGN KEY (id_experiencia) REFERENCES experiencias (id_experiencia)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;

-- =====================================================================
-- TABLA: funciones
-- Corresponde al arreglo "funciones" dentro de cada experiencia
-- Relación 1:N con experiencias
-- =====================================================================
CREATE TABLE funciones (
    id_funcion      INT AUTO_INCREMENT PRIMARY KEY,
    id_experiencia  INT                                 NOT NULL,
    nombre_funcion  VARCHAR(150)                        NOT NULL,
    CONSTRAINT fk_funcion_experiencia
        FOREIGN KEY (id_experiencia) REFERENCES experiencias (id_experiencia)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB;

-- =====================================================================
-- DATOS DE PRUEBA (opcional, para probar el modelo)
-- =====================================================================
-- Primero los usuarios (el aprendiz los necesita para enlazarse)
-- SHA2 solo es para datos de prueba; desde la API usa un hash seguro (bcrypt / werkzeug).
INSERT INTO usuarios (nombre_usuario, correo, password, rol, estado, fecha_nacimiento)
VALUES ('juanperez', 'juan.perez@sena.edu.co', SHA2('123456', 256), 'Aprendiz', 'Activo', '2004-03-15'),  -- id_usuario = 1
       ('admin', 'admin@sena.edu.co', SHA2('admin123', 256), 'Administrador', 'Activo', '1990-01-01');      -- id_usuario = 2 (no es aprendiz)

-- Aprendiz Juan Pérez enlazado al usuario 1
INSERT INTO aprendices (nombre, edad, ciudad, correo, programa, ficha, jornada, id_usuario)
VALUES ('Juan Pérez', 22, 'Bogotá', 'juan.perez@sena.edu.co', 'ADSO', 2758934, 'Mañana', 1);

INSERT INTO informacion_academica (id_aprendiz, nivel, titulo, institucion, graduacion)
VALUES (1, 'Tecnólogo', 'Analista y Desarrollador de Software', 'SENA', '2026');

INSERT INTO cursos (id_academico, nombre_curso)
VALUES (1, 'React'), (1, 'Bases de Datos MySQL');

INSERT INTO experiencias (id_aprendiz, empresa, cargo, tiempo)
VALUES (1, 'Tech Solutions', 'Desarrollador Frontend', '1 año');

INSERT INTO habilidades (id_experiencia, nombre_habilidad)
VALUES (1, 'React'), (1, 'JavaScript');

INSERT INTO funciones (id_experiencia, nombre_funcion)
VALUES (1, 'Desarrollo de páginas web'), (1, 'Mantenimiento de aplicaciones');

-- =====================================================================
-- CONSULTA DE VERIFICACIÓN: usuarios con su aprendiz (si tiene)
-- =====================================================================
SELECT
    u.id_usuario, u.nombre_usuario, u.correo, u.rol, u.estado, u.fecha_nacimiento,
    a.nombre AS nombre_aprendiz, a.programa, a.ficha
FROM usuarios u
LEFT JOIN aprendices a ON a.id_usuario = u.id_usuario;

-- =====================================================================
-- CONSULTA DE VERIFICACIÓN: hoja de vida completa de un aprendiz
-- =====================================================================
SELECT
    a.nombre, a.edad, a.ciudad, a.correo, a.programa, a.ficha, a.jornada,
    ia.nivel, ia.titulo, ia.institucion, ia.graduacion,
    c.nombre_curso,
    e.empresa, e.cargo, e.tiempo,
    h.nombre_habilidad,
    f.nombre_funcion
FROM aprendices a
LEFT JOIN informacion_academica ia ON ia.id_aprendiz = a.id_aprendiz
LEFT JOIN cursos c ON c.id_academico = ia.id_academico
LEFT JOIN experiencias e ON e.id_aprendiz = a.id_aprendiz
LEFT JOIN habilidades h ON h.id_experiencia = e.id_experiencia
LEFT JOIN funciones f ON f.id_experiencia = e.id_experiencia
WHERE a.id_aprendiz = 1;

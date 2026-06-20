-- 请使用 PostgreSQL 管理员账号执行数据库及用户创建部分。
CREATE DATABASE blood_pressure
    ENCODING 'UTF8'
    TEMPLATE template0;

CREATE USER blood_pressure WITH PASSWORD '请替换为强密码';
GRANT ALL PRIVILEGES ON DATABASE blood_pressure TO blood_pressure;

-- 连接 blood_pressure 数据库后执行：
GRANT USAGE, CREATE ON SCHEMA public TO blood_pressure;
ALTER SCHEMA public OWNER TO blood_pressure;

-- 业务表由 `python scripts/init_db.py` 自动创建。


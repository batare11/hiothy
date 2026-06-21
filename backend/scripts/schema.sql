\set ON_ERROR_STOP on

-- Hiothy PostgreSQL 完整初始化脚本。
-- 使用 PostgreSQL 管理员执行：
--   sudo -u postgres psql -d postgres -f scripts/schema.sql
--
-- 执行前请将下面的 CHANGE_ME_STRONG_PASSWORD 替换为强密码。

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blood_pressure') THEN
        CREATE ROLE blood_pressure
            LOGIN
            PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
    END IF;
END
$$;

SELECT format(
    'CREATE DATABASE blood_pressure OWNER blood_pressure ENCODING ''UTF8'' TEMPLATE template0'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = 'blood_pressure'
)\gexec

\connect blood_pressure

GRANT USAGE, CREATE ON SCHEMA public TO blood_pressure;
ALTER SCHEMA public OWNER TO blood_pressure;
SET ROLE blood_pressure;

-- 血压记录。
CREATE TABLE IF NOT EXISTS bp_records (
    id SERIAL PRIMARY KEY,
    systolic INTEGER NOT NULL,
    diastolic INTEGER NOT NULL,
    heart_rate INTEGER,
    hypertension_grade INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50),
    mini_user_id VARCHAR(100),
    mini_user_name VARCHAR(100),
    note TEXT,
    CONSTRAINT ck_bp_records_pressure_order
        CHECK (systolic > diastolic),
    CONSTRAINT ck_bp_records_hypertension_grade
        CHECK (hypertension_grade BETWEEN 0 AND 3)
);

COMMENT ON TABLE bp_records IS '血压测量记录表';
COMMENT ON COLUMN bp_records.id IS '血压记录主键 ID';
COMMENT ON COLUMN bp_records.systolic IS '收缩压（高压），单位：mmHg';
COMMENT ON COLUMN bp_records.diastolic IS '舒张压（低压），单位：mmHg';
COMMENT ON COLUMN bp_records.heart_rate IS '心率，单位：次/分';
COMMENT ON COLUMN bp_records.hypertension_grade IS
    '成人诊室血压高血压等级：0=未达到高血压，1=1级，2=2级，3=3级';
COMMENT ON COLUMN bp_records.created_at IS '测量时间';
COMMENT ON COLUMN bp_records.updated_at IS '记录最后更新时间';
COMMENT ON COLUMN bp_records.user_id IS '业务用户 ID（兼容字段）';
COMMENT ON COLUMN bp_records.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN bp_records.mini_user_name IS '测量用户名称';
COMMENT ON COLUMN bp_records.note IS '测量备注，如熬夜、服药、症状等';

CREATE INDEX IF NOT EXISTS ix_bp_records_mini_user_id
    ON bp_records (mini_user_id);
CREATE INDEX IF NOT EXISTS ix_bp_records_user_time
    ON bp_records (mini_user_id, created_at DESC);

-- 小程序用户基础资料。
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    mini_user_id VARCHAR(100) NOT NULL UNIQUE,
    nickname VARCHAR(100) NOT NULL DEFAULT '微信用户',
    avatar_url VARCHAR(500),
    gender VARCHAR(20),
    phone VARCHAR(30),
    birth_date VARCHAR(20),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_profiles IS '微信小程序用户基础资料表';
COMMENT ON COLUMN user_profiles.id IS '用户资料主键 ID';
COMMENT ON COLUMN user_profiles.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN user_profiles.nickname IS '用户昵称';
COMMENT ON COLUMN user_profiles.avatar_url IS '用户头像地址';
COMMENT ON COLUMN user_profiles.gender IS '用户性别文字值';
COMMENT ON COLUMN user_profiles.phone IS '用户手机号';
COMMENT ON COLUMN user_profiles.birth_date IS '出生日期，格式：YYYY-MM-DD';
COMMENT ON COLUMN user_profiles.created_at IS '资料创建时间';
COMMENT ON COLUMN user_profiles.updated_at IS '资料最后更新时间';

CREATE UNIQUE INDEX IF NOT EXISTS ix_user_profiles_mini_user_id
    ON user_profiles (mini_user_id);

-- 辅助健康档案。
CREATE TABLE IF NOT EXISTS health_archives (
    id SERIAL PRIMARY KEY,
    mini_user_id VARCHAR(100) NOT NULL UNIQUE,
    age INTEGER,
    height_cm DOUBLE PRECISION,
    weight_jin DOUBLE PRECISION,
    gender INTEGER,
    marital_status INTEGER,
    smoking BOOLEAN NOT NULL DEFAULT FALSE,
    drinking BOOLEAN NOT NULL DEFAULT FALSE,
    staying_up_late BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_health_archives_age
        CHECK (age IS NULL OR age BETWEEN 0 AND 150),
    CONSTRAINT ck_health_archives_height
        CHECK (height_cm IS NULL OR height_cm BETWEEN 50 AND 250),
    CONSTRAINT ck_health_archives_weight
        CHECK (weight_jin IS NULL OR weight_jin BETWEEN 20 AND 500),
    CONSTRAINT ck_health_archives_gender
        CHECK (gender IS NULL OR gender IN (0, 1)),
    CONSTRAINT ck_health_archives_marital_status
        CHECK (marital_status IS NULL OR marital_status IN (0, 1))
);

COMMENT ON TABLE health_archives IS '用户辅助健康档案表';
COMMENT ON COLUMN health_archives.id IS '辅助健康档案主键 ID';
COMMENT ON COLUMN health_archives.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN health_archives.age IS '年龄，单位：岁';
COMMENT ON COLUMN health_archives.height_cm IS '身高，单位：厘米';
COMMENT ON COLUMN health_archives.weight_jin IS '体重，单位：斤';
COMMENT ON COLUMN health_archives.gender IS '性别：1=男，0=女';
COMMENT ON COLUMN health_archives.marital_status IS
    '婚姻状态：1=已婚，0=未婚';
COMMENT ON COLUMN health_archives.smoking IS '是否抽烟：true=是，false=否';
COMMENT ON COLUMN health_archives.drinking IS '是否喝酒：true=是，false=否';
COMMENT ON COLUMN health_archives.staying_up_late IS
    '是否经常熬夜：true=是，false=否';
COMMENT ON COLUMN health_archives.note IS
    '辅助备注，如慢性病、过敏史、长期服药及近期症状';
COMMENT ON COLUMN health_archives.created_at IS '档案创建时间';
COMMENT ON COLUMN health_archives.updated_at IS '档案最后更新时间';

CREATE UNIQUE INDEX IF NOT EXISTS ix_health_archives_mini_user_id
    ON health_archives (mini_user_id);

-- 消息中心。
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    mini_user_id VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(30) NOT NULL DEFAULT 'system',
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    related_record_id INTEGER,
    action_type VARCHAR(30),
    action_path VARCHAR(300),
    dedupe_key VARCHAR(150) UNIQUE,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE messages IS '用户站内消息与健康提醒表';
COMMENT ON COLUMN messages.id IS '消息主键 ID';
COMMENT ON COLUMN messages.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN messages.title IS '消息标题';
COMMENT ON COLUMN messages.content IS '消息正文';
COMMENT ON COLUMN messages.message_type IS
    '消息类型，如 system、abnormal_pressure、continuous_risk';
COMMENT ON COLUMN messages.severity IS
    '消息风险级别：info、warning、high、critical';
COMMENT ON COLUMN messages.related_record_id IS '关联的血压记录 ID';
COMMENT ON COLUMN messages.action_type IS
    '消息点击动作类型，如 switch_tab';
COMMENT ON COLUMN messages.action_path IS '消息点击后跳转的小程序页面路径';
COMMENT ON COLUMN messages.dedupe_key IS '自动消息唯一键，用于防止重复提醒';
COMMENT ON COLUMN messages.is_read IS '是否已读：true=已读，false=未读';
COMMENT ON COLUMN messages.created_at IS '消息创建时间';

CREATE INDEX IF NOT EXISTS ix_messages_mini_user_id
    ON messages (mini_user_id);
CREATE INDEX IF NOT EXISTS ix_messages_is_read
    ON messages (is_read);
CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_dedupe_key
    ON messages (dedupe_key);
CREATE INDEX IF NOT EXISTS ix_messages_user_state_time
    ON messages (mini_user_id, is_read, created_at DESC);

-- 意见反馈。
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    mini_user_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    contact VARCHAR(100),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE feedback IS '用户意见反馈表';
COMMENT ON COLUMN feedback.id IS '反馈主键 ID';
COMMENT ON COLUMN feedback.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN feedback.content IS '反馈内容';
COMMENT ON COLUMN feedback.contact IS '用户联系方式';
COMMENT ON COLUMN feedback.status IS
    '处理状态，如 pending、processing、resolved';
COMMENT ON COLUMN feedback.created_at IS '反馈提交时间';

CREATE INDEX IF NOT EXISTS ix_feedback_mini_user_id
    ON feedback (mini_user_id);

-- 兼容已经存在的旧数据库：补充后来新增的字段。
ALTER TABLE bp_records
    ADD COLUMN IF NOT EXISTS hypertension_grade INTEGER;

ALTER TABLE health_archives
    ADD COLUMN IF NOT EXISTS age INTEGER,
    ADD COLUMN IF NOT EXISTS height_cm DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS weight_jin DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gender INTEGER,
    ADD COLUMN IF NOT EXISTS marital_status INTEGER,
    ADD COLUMN IF NOT EXISTS smoking BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS drinking BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS staying_up_late BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS note TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE
        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE
        NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20) NOT NULL DEFAULT 'info',
    ADD COLUMN IF NOT EXISTS related_record_id INTEGER,
    ADD COLUMN IF NOT EXISTS action_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS action_path VARCHAR(300),
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(150);

CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_dedupe_key
    ON messages (dedupe_key);

-- 兼容早期文字字典：男/女、已婚/未婚转换为 1/0。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'health_archives'
          AND column_name = 'gender'
          AND data_type <> 'integer'
    ) THEN
        ALTER TABLE health_archives
        ALTER COLUMN gender TYPE INTEGER
        USING CASE
            WHEN gender::text IN ('1', '男') THEN 1
            WHEN gender::text IN ('0', '女') THEN 0
            ELSE NULL
        END;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'health_archives'
          AND column_name = 'marital_status'
          AND data_type <> 'integer'
    ) THEN
        ALTER TABLE health_archives
        ALTER COLUMN marital_status TYPE INTEGER
        USING CASE
            WHEN marital_status::text IN ('1', '已婚') THEN 1
            WHEN marital_status::text IN ('0', '未婚') THEN 0
            ELSE NULL
        END;
    END IF;
END
$$;

-- 根据历史高低压数据回填等级。
UPDATE bp_records
SET hypertension_grade = CASE
    WHEN systolic >= 180 OR diastolic >= 110 THEN 3
    WHEN systolic >= 160 OR diastolic >= 100 THEN 2
    WHEN systolic >= 140 OR diastolic >= 90 THEN 1
    ELSE 0
END
WHERE hypertension_grade IS NULL;

ALTER TABLE bp_records
    ALTER COLUMN hypertension_grade SET DEFAULT 0,
    ALTER COLUMN hypertension_grade SET NOT NULL;

-- 所有写入路径统一由数据库计算等级，避免字段出现 NULL 或过期值。
CREATE OR REPLACE FUNCTION set_bp_hypertension_grade()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.hypertension_grade := CASE
        WHEN NEW.systolic >= 180 OR NEW.diastolic >= 110 THEN 3
        WHEN NEW.systolic >= 160 OR NEW.diastolic >= 100 THEN 2
        WHEN NEW.systolic >= 140 OR NEW.diastolic >= 90 THEN 1
        ELSE 0
    END;
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_bp_records_set_hypertension_grade ON bp_records;
CREATE TRIGGER trg_bp_records_set_hypertension_grade
BEFORE INSERT OR UPDATE OF systolic, diastolic
ON bp_records
FOR EACH ROW
EXECUTE FUNCTION set_bp_hypertension_grade();

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO blood_pressure;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO blood_pressure;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO blood_pressure;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO blood_pressure;

RESET ROLE;

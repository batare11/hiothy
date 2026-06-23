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

-- 系统角色。
CREATE TABLE IF NOT EXISTS roles (
    code VARCHAR(30) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(300),
    rank INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE roles
    ADD COLUMN IF NOT EXISTS rank INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON TABLE roles IS '系统角色定义表';
COMMENT ON COLUMN roles.code IS '角色编码，如 vip、svip、admin';
COMMENT ON COLUMN roles.name IS '角色名称';
COMMENT ON COLUMN roles.description IS '角色能力说明';
COMMENT ON COLUMN roles.rank IS '角色展示优先级，数值越大优先级越高';
COMMENT ON COLUMN roles.enabled IS '角色是否启用';
COMMENT ON COLUMN roles.created_at IS '角色创建时间';

INSERT INTO roles (code, name, description, rank, enabled)
VALUES
    ('vip', '普通会员', '可使用 AI 智能图片识别', 10, TRUE),
    ('svip', '超级会员', '可使用 AI 智能图片识别和 AI 档案分析', 20, TRUE),
    ('admin', '管理员', '拥有全部会员及后台管理权限', 100, TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description,
    rank = EXCLUDED.rank;

-- 系统功能权限。
CREATE TABLE IF NOT EXISTS permissions (
    code VARCHAR(60) PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    description VARCHAR(300),
    module VARCHAR(50) NOT NULL DEFAULT 'general',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE permissions IS '系统功能权限定义表';
COMMENT ON COLUMN permissions.code IS '功能权限编码';
COMMENT ON COLUMN permissions.name IS '功能权限名称';
COMMENT ON COLUMN permissions.description IS '功能权限说明';
COMMENT ON COLUMN permissions.module IS '权限所属功能模块';
COMMENT ON COLUMN permissions.enabled IS '功能权限是否启用';
COMMENT ON COLUMN permissions.created_at IS '功能权限创建时间';

INSERT INTO permissions (code, name, description, module)
VALUES
    ('cloud_ocr', 'AI 图片识别', '使用云端 AI 模型识别血压图片', 'ocr'),
    ('ai_health_report', 'AI 档案分析', '使用 AI 分析健康档案与历史记录', 'archive'),
    ('feedback_manage', '反馈管理', '查看并回复全部用户反馈', 'admin'),
    ('role_manage', '角色权限管理', '维护角色、功能权限和绑定关系', 'admin')
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description,
    module = EXCLUDED.module;

-- 角色功能权限绑定。
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_code VARCHAR(30) NOT NULL REFERENCES roles(code) ON DELETE CASCADE,
    permission_code VARCHAR(60) NOT NULL
        REFERENCES permissions(code) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_permissions_role_permission
        UNIQUE (role_code, permission_code)
);

COMMENT ON TABLE role_permissions IS '角色与功能权限绑定表';
COMMENT ON COLUMN role_permissions.id IS '角色权限绑定主键 ID';
COMMENT ON COLUMN role_permissions.role_code IS '角色编码';
COMMENT ON COLUMN role_permissions.permission_code IS '功能权限编码';
COMMENT ON COLUMN role_permissions.created_at IS '角色权限绑定时间';

CREATE INDEX IF NOT EXISTS ix_role_permissions_role_code
    ON role_permissions (role_code);
CREATE INDEX IF NOT EXISTS ix_role_permissions_permission_code
    ON role_permissions (permission_code);

INSERT INTO role_permissions (role_code, permission_code)
VALUES
    ('vip', 'cloud_ocr'),
    ('svip', 'cloud_ocr'),
    ('svip', 'ai_health_report'),
    ('admin', 'cloud_ocr'),
    ('admin', 'ai_health_report'),
    ('admin', 'feedback_manage'),
    ('admin', 'role_manage')
ON CONFLICT (role_code, permission_code) DO NOTHING;

-- 用户角色绑定。
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    mini_user_id VARCHAR(100) NOT NULL,
    role_code VARCHAR(30) NOT NULL REFERENCES roles(code),
    expires_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_roles_user_role UNIQUE (mini_user_id, role_code)
);

COMMENT ON TABLE user_roles IS '小程序用户与角色绑定表';
COMMENT ON COLUMN user_roles.id IS '用户角色绑定主键 ID';
COMMENT ON COLUMN user_roles.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN user_roles.role_code IS '绑定的角色编码';
COMMENT ON COLUMN user_roles.expires_at IS '角色到期时间；为空表示长期有效';
COMMENT ON COLUMN user_roles.created_at IS '角色绑定时间';

CREATE INDEX IF NOT EXISTS ix_user_roles_mini_user_id
    ON user_roles (mini_user_id);
CREATE INDEX IF NOT EXISTS ix_user_roles_role_code
    ON user_roles (role_code);

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
    reply TEXT,
    replied_by VARCHAR(100),
    replied_at TIMESTAMP WITHOUT TIME ZONE,
    reply_deleted_at TIMESTAMP WITHOUT TIME ZONE,
    reply_deleted_by VARCHAR(100),
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    deleted_by VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE feedback IS '用户意见反馈表';
COMMENT ON COLUMN feedback.id IS '反馈主键 ID';
COMMENT ON COLUMN feedback.mini_user_id IS '微信小程序用户唯一标识';
COMMENT ON COLUMN feedback.content IS '反馈内容';
COMMENT ON COLUMN feedback.contact IS '用户联系方式';
COMMENT ON COLUMN feedback.status IS
    '处理状态，如 pending、processing、resolved';
COMMENT ON COLUMN feedback.reply IS '管理员回复内容';
COMMENT ON COLUMN feedback.replied_by IS '回复管理员的微信小程序用户唯一标识';
COMMENT ON COLUMN feedback.replied_at IS '管理员回复时间';
COMMENT ON COLUMN feedback.reply_deleted_at IS '管理员回复逻辑删除时间';
COMMENT ON COLUMN feedback.reply_deleted_by IS '撤销回复的管理员用户唯一标识';
COMMENT ON COLUMN feedback.deleted_at IS '反馈逻辑删除时间';
COMMENT ON COLUMN feedback.deleted_by IS '删除反馈的管理员用户唯一标识';
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

ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS reply TEXT,
    ADD COLUMN IF NOT EXISTS replied_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS replied_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS reply_deleted_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS reply_deleted_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(100);

COMMENT ON COLUMN feedback.reply IS '管理员回复内容';
COMMENT ON COLUMN feedback.replied_by IS '回复管理员的微信小程序用户唯一标识';
COMMENT ON COLUMN feedback.replied_at IS '管理员回复时间';
COMMENT ON COLUMN feedback.reply_deleted_at IS '管理员回复逻辑删除时间';
COMMENT ON COLUMN feedback.reply_deleted_by IS '撤销回复的管理员用户唯一标识';
COMMENT ON COLUMN feedback.deleted_at IS '反馈逻辑删除时间';
COMMENT ON COLUMN feedback.deleted_by IS '删除反馈的管理员用户唯一标识';

ALTER TABLE roles
    ADD COLUMN IF NOT EXISTS rank INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE;

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

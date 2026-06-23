\set ON_ERROR_STOP on

-- 在现有正式数据库中执行本脚本，补充会员角色和反馈回复能力。
-- 示例：
--   sudo -u postgres psql -d blood_pressure \
--     -f scripts/migrate_membership_feedback.sql

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

ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS reply TEXT,
    ADD COLUMN IF NOT EXISTS replied_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS replied_at TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN feedback.reply IS '管理员回复内容';
COMMENT ON COLUMN feedback.replied_by IS '回复管理员的微信小程序用户唯一标识';
COMMENT ON COLUMN feedback.replied_at IS '管理员回复时间';

GRANT ALL PRIVILEGES ON roles, permissions, role_permissions, user_roles
    TO blood_pressure;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE
    role_permissions_id_seq, user_roles_id_seq TO blood_pressure;

-- 仅在数据库中初始化管理员身份，业务代码不包含任何管理员 ID 特判。
\ir grant_admin_by_archive_id.sql

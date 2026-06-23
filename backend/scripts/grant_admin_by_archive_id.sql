\set ON_ERROR_STOP on

-- 按小程序展示的 12 位健康档案 ID 授予管理员角色。
-- 默认绑定项目初始化管理员；也可传入其他档案 ID，支持多个管理员：
--   sudo -u postgres psql -d blood_pressure \
--     -v archive_id=其他12位档案ID \
--     -f scripts/grant_admin_by_archive_id.sql

\if :{?archive_id}
\else
\set archive_id '7de9ad672331'
\endif

CREATE EXTENSION IF NOT EXISTS pgcrypto;

WITH matched_user AS (
    SELECT mini_user_id
    FROM user_profiles
    WHERE substring(
        encode(digest(mini_user_id, 'sha256'), 'hex')
        FROM 5 FOR 12
    ) = :'archive_id'
)
INSERT INTO user_roles (mini_user_id, role_code)
SELECT mini_user_id, 'admin'
FROM matched_user
ON CONFLICT (mini_user_id, role_code) DO NOTHING;

SELECT CASE
    WHEN EXISTS (
        SELECT 1
        FROM user_roles ur
        JOIN user_profiles up ON up.mini_user_id = ur.mini_user_id
        WHERE ur.role_code = 'admin'
          AND substring(
              encode(digest(up.mini_user_id, 'sha256'), 'hex')
              FROM 5 FOR 12
          ) = :'archive_id'
    )
    THEN 1
    ELSE 0
END AS admin_bound
\gset

\if :admin_bound
\echo 已成功绑定管理员档案 ID :archive_id
\else
\echo 未找到档案 ID :archive_id 对应的用户，请先使用该账号登录小程序
\quit 3
\endif

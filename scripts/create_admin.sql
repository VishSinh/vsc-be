-- Direct SQL script to create admin user
-- Run this with: psql -h localhost -U vish -d vsc -f scripts/create_admin.sql

-- Generate a UUID for the admin user
DO $$
DECLARE
    admin_id UUID := gen_random_uuid();
    admin_password VARCHAR := 'admin123';  -- Change this password!
    hashed_password VARCHAR := encode(sha256((admin_password || 'vsc_salt_2024')::bytea), 'hex');
BEGIN
    -- Check if admin user already exists
    IF EXISTS (SELECT 1 FROM staff WHERE username = 'admin') THEN
        RAISE NOTICE 'Admin user already exists!';
    ELSE
        -- Insert admin user
        INSERT INTO staff (
            id, username, password, email, phone, first_name, last_name,
            role, is_staff, is_superuser, is_active, date_joined, created_at, updated_at
        ) VALUES (
            admin_id,
            'admin',
            hashed_password,
            'admin@example.com',
            '1234567890',
            'Admin',
            'User',
            'ADMIN',
            true,
            true,
            true,
            NOW(),
            NOW(),
            NOW()
        );

        RAISE NOTICE 'Admin user created successfully!';
        RAISE NOTICE 'Username: admin';
        RAISE NOTICE 'Password: %', admin_password;
        RAISE NOTICE 'ID: %', admin_id;
    END IF;
END $$;

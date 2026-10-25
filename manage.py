"""Run only on your own server, after a database backup.

python manage.py migrate-passwords          # dry run
python manage.py migrate-passwords --apply  # explicit write
python manage.py create-admin              # new empty installation
"""
import argparse
import getpass
from app import get_conn
from werkzeug.security import generate_password_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['migrate-passwords', 'create-admin'])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute('SHOW COLUMNS FROM users LIKE %s', ('password',))
            col = c.fetchone()
            if col and col['Type'].lower() not in ('varchar(255)', 'text', 'mediumtext', 'longtext'):
                raise SystemExit('Password column must allow >=255 chars. Back up, then widen the column; see instructions.')
            if args.command == 'migrate-passwords':
                c.execute('SELECT id, password FROM users')
                rows = [row for row in c.fetchall() if not row['password'].startswith(('scrypt:', 'pbkdf2:'))]
                print(f'Passwords to migrate: {len(rows)}; apply={args.apply}. No password values are printed.')
                if args.apply:
                    for row in rows:
                        c.execute('UPDATE users SET password=%s WHERE id=%s', (generate_password_hash(row['password']), row['id']))
                    conn.commit()
                    print('Migration committed.')
            else:
                c.execute('SELECT COUNT(*) AS cnt FROM users')
                if c.fetchone()['cnt']:
                    raise SystemExit('Users already exist. Use the existing owner account.')
                email = input('Owner email: ').strip()
                first = input('First name: ').strip()
                last = input('Last name: ').strip()
                password = getpass.getpass('Owner password (min 12 chars): ')
                confirm = getpass.getpass('Repeat password: ')
                if not email or not first or not last or len(password) < 12 or password != confirm:
                    raise SystemExit('Invalid input. Nothing changed.')
                c.execute('INSERT INTO users (first_name,last_name,email,password,positions) VALUES (%s,%s,%s,%s,%s)', (first,last,email,generate_password_hash(password),'Власник'))
                conn.commit()
                print('Owner created.')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
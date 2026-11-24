"""Read-only factory setup check. Never imports live automation/configuration."""
import ast
import importlib.util
from pathlib import Path
import sys

LIVE = Path(r'D:\PRODUCTION AUTOMATION\EXCEL FILE')
TEST = LIVE / 'SQL_TEST'

def check(root=LIVE, test=TEST):
    errors = []
    print('STARISH SQL TEST: read-only setup check')
    for name in ('auto_push_watcher_v2.py', 'gsheet_to_erp.py', 'erp_to_gsheet.py', 'erp_lock.py'):
        path = root / name
        if not path.is_file():
            print(f'MISSING live file: {name}')
            errors.append(name)
            continue
        try:
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=name)
            print(f'OK live file syntax: {name}')
        except (OSError, SyntaxError, UnicodeError):
            print(f'CHECK REQUIRED live file syntax: {name}')
            errors.append(name)
    for name in ('bridge.py', 'finishing.py', 'test_bridge.py', 'test_finishing.py'):
        if not (test / name).is_file():
            print(f'MISSING test file: {name}')
            errors.append(name)
    for module in ('selenium', 'requests'):
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            found = False
        print(f'{"OK" if found else "MISSING"} dependency: {module}')
        if not found: errors.append(module)
    print('No watcher started. No ERP/SQL requests sent. No configuration or credentials read.')
    print('Real ERP adapter and SQL acknowledgement are still pending; this setup cannot push entries.')
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(check())

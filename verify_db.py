# -*- coding: utf-8 -*-
"""验证数据库状态"""
import sys
sys.path.insert(0, 'backend')
from database import get_db
import sqlite3

db = get_db()
user = db.get_user_by_username('student001')
course_id = db.get_course_id_by_name('概率论与数理统计')

# 查看t检验当前状态
states = db.get_learner_state(user['id'], course_id)
t_test = [s for s in states if s['node_id'] == 't_test'][0]
print('当前t检验状态:')
print(f'  mastery: {t_test["mastery"]:.2f}')
print(f'  error_count: {t_test["error_count"]}')
print(f'  status: {t_test["status"]}')

# 查看agent_runs记录数
conn = sqlite3.connect('data/meaita.db')
count = conn.execute('SELECT COUNT(*) FROM agent_runs').fetchone()[0]
print(f'\nagent_runs记录数: {count}')

# 查看最近8条agent_runs
rows = conn.execute('SELECT agent_name, task, phase, created_at FROM agent_runs ORDER BY id DESC LIMIT 8').fetchall()
print('最近Agent执行记录:')
for r in rows:
    print(f'  {r[3][:19]} | {r[0]} | {r[2]} | {r[1][:25]}')

# 查看错题数
wrong_count = conn.execute('SELECT COUNT(*) FROM wrong_questions WHERE user_id=?', (user['id'],)).fetchone()[0]
print(f'\n错题总数: {wrong_count}')
conn.close()

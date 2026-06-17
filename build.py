# -*- coding: utf-8 -*-
"""解析《客服接待考核库.md》→ 18题结构化数据 → 注入 index 模板生成成品 index.html。"""
import re, json, os

SRC = r'G:\AI  biancheng\Obsidian\obsidian\02-淘宝\日常注意\客服接待考核库.md'
HERE = os.path.dirname(os.path.abspath(__file__))

txt = open(SRC, encoding='utf-8').read()

# 店铺脱敏清单（长名优先替换，避免子串问题）
SHOPS = []
slp = os.path.join(HERE, 'shoplist.json')
if os.path.exists(slp):
    SHOPS = sorted(json.load(open(slp, encoding='utf-8')), key=len, reverse=True)
def desens(s):
    if not s: return s
    for shop in SHOPS:
        if shop in s:
            s = s.replace(shop, '本店')
    return s

# 按 "### 考核题 N：" 切块
blocks = re.split(r'(?=^### 考核题 \d+[:：])', txt, flags=re.M)
questions = []
for b in blocks:
    m = re.match(r'### 考核题 (\d+)[:：]\s*(.+?)\s*-\s*(.+)', b)
    if not m:
        continue
    num = int(m.group(1)); category = m.group(2).strip(); title = m.group(3).strip()

    # 案例类型(优秀/反面)
    case_type = ''
    cm = re.search(r'\*\*订单号\*\*[:：].*?（(优秀|反面)案例', b)
    if cm: case_type = cm.group(1)

    # 真实对话节选
    dialogue = []
    dm = re.search(r'\*\*📞 真实对话节选\*\*\s*\n(.*?)(?=\n\*\*❓)', b, flags=re.S)
    if dm:
        for line in dm.group(1).split('\n'):
            line = line.strip()
            if line.startswith('- '):
                dialogue.append(line[2:].strip())

    # 考核提问
    q = ''
    qm = re.search(r'\*\*❓ 考核提问\*\*[:：]\s*(.+)', b)
    if qm: q = qm.group(1).strip()

    # 解析块：考核提问之后 到 考核点之前 的全部内容(含标准应对/错误应对/AI优化)
    analysis = ''
    am = re.search(r'\*\*❓ 考核提问\*\*[:：].+?\n(.*?)(?=\n\*\*📊 考核点\*\*)', b, flags=re.S)
    if am: analysis = am.group(1).strip()

    # 考核点 rubric
    rubric = []
    rm = re.search(r'\*\*📊 考核点\*\*（满分\d+）\s*\n(.*?)(?=\n---|\Z)', b, flags=re.S)
    if rm:
        for line in rm.group(1).split('\n'):
            line = line.strip()
            if line.startswith('- '):
                item = line[2:].strip()
                pm = re.search(r'（(\d+)\s*分', item)
                pts = int(pm.group(1)) if pm else 0
                # 去掉分值后缀做描述
                desc = re.sub(r'（\d+\s*分[^）]*）', '', item).strip()
                redline = '红线' in item
                rubric.append({'desc': desc, 'points': pts, 'redline': redline})

    maxscore = sum(r['points'] for r in rubric)
    questions.append({
        'num': num, 'category': category, 'title': desens(title), 'caseType': case_type,
        'dialogue': [desens(d) for d in dialogue], 'question': desens(q), 'analysis': desens(analysis),
        'rubric': rubric, 'maxScore': maxscore,
    })

questions.sort(key=lambda x: x['num'])
print(f'解析到 {len(questions)} 题')
for q in questions:
    print(f"  题{q['num']}: {q['category']}-{q['title'][:18]} | 对话{len(q['dialogue'])}行 | 评分项{len(q['rubric'])} | 满分{q['maxScore']}")

# 校验满分
bad = [q['num'] for q in questions if q['maxScore'] != 10]
if bad: print('⚠️ 满分非10的题:', bad)

json.dump(questions, open(os.path.join(HERE, 'questions.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# 注入模板
tpl_path = os.path.join(HERE, 'index.template.html')
if os.path.exists(tpl_path):
    tpl = open(tpl_path, encoding='utf-8').read()
    data_js = 'const QUESTIONS = ' + json.dumps(questions, ensure_ascii=False) + ';'
    out = tpl.replace('/*__QUESTIONS__*/', data_js)
    open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8').write(out)
    print('已生成 index.html')
else:
    print('模板 index.template.html 不存在，仅输出 questions.json')

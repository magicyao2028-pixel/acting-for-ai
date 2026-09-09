"""Offline reference search, validation and deterministic export. No network calls."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = {'emotion': 'EMO', 'relationship': 'REL', 'motion': 'MOT'}
LABELS = {'emotion': '情绪与状态', 'relationship': '人物关系', 'motion': '动作质感与节拍'}
STATES = {'author_verified_in_practice', 'contributor_verified_in_practice', 'editorial_reference', 'documented_generation_test'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_cards(root=ROOT):
    return [read_json(path) for path in sorted((root / 'cards').glob('*.json'))]


def validate(cards, sources):
    """Return actionable errors rather than treating editorial checks as video tests."""
    errors, seen = [], set()
    source_ids = {s.get('id') for s in sources}
    if len(source_ids) != len(sources):
        errors.append('Duplicate source IDs')
    for s in sources:
        if not re.fullmatch(r'SRC-\d{3,}', s.get('id', '')):
            errors.append('Invalid source ID')
        if not re.match(r'^https?://[^\s]+$', s.get('url', '')):
            errors.append(f"Invalid URL: {s.get('id')}")
        if s.get('review_status') not in {'inherited_reference', 'content_reviewed', 'unavailable', 'needs_review'}:
            errors.append(f"Unknown source review status: {s.get('id')}")
        if s.get('review_status') == 'content_reviewed' and not s.get('last_checked'):
            errors.append(f"Reviewed source missing date: {s.get('id')}")
    for c in cards:
        cid = c.get('id', '')
        if not re.fullmatch(r'(EMO|REL|MOT)-\d{3,}', cid):
            errors.append(f'Invalid ID: {cid}')
        if cid in seen:
            errors.append(f'Duplicate ID: {cid}')
        seen.add(cid)
        if not cid.startswith(PREFIXES.get(c.get('category'), 'INVALID') + '-'):
            errors.append(f'Category/ID mismatch: {cid}')
        for field in ['title', 'guidance', 'source_note', 'updated']:
            if not isinstance(c.get(field), str) or not c[field].strip():
                errors.append(f'{cid}: missing {field}')
        if not (c.get('prompt') or c.get('reference_text')):
            errors.append(f'{cid}: no reference content')
        if not isinstance(c.get('tags'), list) or not all(isinstance(t, str) for t in c.get('tags', [])):
            errors.append(f'{cid}: invalid tags')
        if not isinstance(c.get('channels'), dict):
            errors.append(f'{cid}: invalid channels')
        refs = c.get('source_ids')
        if not isinstance(refs, list) or any(s not in source_ids for s in (refs or [])):
            errors.append(f'{cid}: missing or unknown source reference')
        evidence = c.get('validation', {})
        if evidence.get('status') not in STATES:
            errors.append(f'{cid}: unknown validation status')
        if not evidence.get('scope') or not evidence.get('per_entry_record'):
            errors.append(f'{cid}: missing validation scope')
        if evidence.get('status') == 'documented_generation_test' and not evidence.get('record_path'):
            errors.append(f'{cid}: test claim requires a record path')
        if not c.get('provenance', {}).get('origin'):
            errors.append(f'{cid}: missing provenance')
        try:
            date.fromisoformat(c.get('updated', ''))
        except (ValueError, TypeError):
            errors.append(f'{cid}: invalid updated date')
    return errors


def search(cards, query, limit=5, category=None):
    terms = query.casefold().split()
    if not terms:
        return []
    ranked = []
    for c in cards:
        if category and c['category'] != category:
            continue
        title = (c['title'] + ' ' + ' '.join(c['tags']) + ' ' + c['id']).casefold()
        body = ' '.join([
            c.get('guidance', ''),
            json.dumps(c.get('channels', {}), ensure_ascii=False),
            c.get('prompt', ''),
            c.get('reference_text', ''),
        ]).casefold()
        score = sum(10 if t in title else 1 if t in body else 0 for t in terms)
        if score:
            ranked.append((score, c))
    ranked.sort(key=lambda x: (-x[0], x[1]['id']))
    return [c for _, c in ranked[:limit]]


def search_payload(cards, query, limit=5, category=None):
    """Return a stable, compact search contract for tools and Agents."""
    results = search(cards, query, limit, category)
    return {
        'schema_version': 1,
        'query': query,
        'filters': {'category': category},
        'limit': limit,
        'result_count': len(results),
        'results': [
            {
                'id': card['id'],
                'title': card['title'],
                'category': card['category'],
                'tags': card['tags'],
                'json_path': f"cards/{card['id']}.json",
                'markdown_path': f"docs/cards/{card['id']}.md",
                'validation': card['validation'],
            }
            for card in results
        ],
    }


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def exports(cards, sources, manifest):
    outputs = {}
    index = []
    for c in cards:
        cid = c['id']
        index.append({k: c[k] for k in ('id', 'title', 'category', 'tags')} | {'json_path': f'cards/{cid}.json', 'markdown_path': f'docs/cards/{cid}.md'})
        body = [f"# {cid} · {c['title']}", '', '[返回索引](../INDEX.md) · [原始数据](../../cards/'+cid+'.json)', '', f"分类：{LABELS[c['category']]} ｜ 更新：{c['updated']}", '', '## 使用要点', '', c['guidance']]
        if c['channels']:
            body += ['', '## 可观察通道', '']
            body += [f'- **{k}**：{v}' for k, v in c['channels'].items()]
        if c.get('prompt'):
            body += ['', '## 文字参考', '', c['prompt']]
        if c.get('reference_text'):
            # Demote headings so inherited subheadings remain below this card.
            ref = re.sub(r'^(#{1,5}) ', r'#\1 ', c['reference_text'], flags=re.M)
            body += ['', '## 方法参考', '', ref]
        body += ['', '## 出处与验证范围', '', c['source_note'], '', '原始整理：'+c['provenance']['origin']+'；模块：'+c['provenance'].get('source_module', '原创补充')+'；快照：'+c['provenance'].get('source_version', '见更新记录')+'。', '', f"验证状态：`{c['validation']['status']}`；范围：`{c['validation']['scope']}`；逐条记录：`{c['validation']['per_entry_record']}`。", '', '范围解释见[验证说明](../VALIDATION.md)。来源核查不等于生成效果验证。']
        for sid in c['source_ids']:
            src = next(s for s in sources if s['id'] == sid)
            body += ['', f"背景参考 {sid}：["+src['title']+']('+src['url']+')']
        outputs[f'docs/cards/{cid}.md'] = '\n'.join(body).rstrip()+'\n'
    outputs['data/index.json'] = json_text({'schema_version': manifest['schema_version'], 'version': manifest['version'], 'entries': index})
    outputs['data/catalog.json'] = json_text({'schema_version': manifest['schema_version'], 'version': manifest['version'], 'validation': manifest['validation'], 'cards': cards})
    lines = ['# 资料索引', '', f"版本 {manifest['version']} · 共 {len(cards)} 个参考条目。", '', '本文件自动生成。修改 cards/*.json 后重新导出。', '', '[使用方法](METHOD.md) · [技能接入](INTEGRATION.md) · [情绪组合示例](combination-examples.md)', '']
    for cat,label in LABELS.items():
        subset = [c for c in cards if c['category'] == cat]
        lines += [f'## {label}（{len(subset)}）', '']
        lines += [f"- [{c['id']} · {c['title']}](cards/{c['id']}.md)" for c in subset]
        lines += ['']
    outputs['docs/INDEX.md'] = '\n'.join(lines).rstrip()+'\n'
    source_lines = ['# 外部资料来源', '', '书目来自作者长期整理，保留原作者归属；不转载文章或课程。来源支持背景原理，不代表对本库提示词的背书或视频测试。', '', '`content_reviewed` 表示已阅读来源内容；`inherited_reference` 表示继承历史书目，尚未在本次逐项重查。精确到条目的对应以各卡 source_ids 为准，空值不等于本库没有实践基础。', '']
    for s in sources:
        source_lines += [f"## {s['id']} · {s['title']}", '', f"[阅读原文]({s['url']})", '', f"状态：`{s['review_status']}`；最近核查：{s.get('last_checked') or '本次未逐项重查'}。", '', s.get('scope',''), '']
    outputs['sources/README.md'] = '\n'.join(source_lines).rstrip()+'\n'
    return outputs


def public_scan(root):
    errors = []
    # Scan public editorial content, excluding code and Git internals.
    files = list(root.glob('*.md')) + list(root.glob('*.json')) + [root/'CITATION.cff']
    for folder in ['cards', 'data', 'docs', 'sources']:
        files.extend(p for p in (root/folder).rglob('*') if p.suffix in {'.md', '.json'})
    patterns = [r'[A-Za-z]:[\\/](?:Users|AI|Program Files)[\\/]', r'gh[pousr]_[A-Za-z0-9]{20,}', r'github_pat_[A-Za-z0-9_]{20,}', r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    for p in files:
        if p.exists():
            text = p.read_text(encoding='utf-8')
            if any(re.search(pattern, text) for pattern in patterns):
                errors.append(f'Potential private material: {p.relative_to(root)}')
    return errors


def check_repository(root, cards, sources, manifest):
    errors = validate(cards, sources) + public_scan(root)
    if not cards:
        errors.append('Empty library')
    for p in (root/'cards').glob('*.json'):
        if p.stem != read_json(p).get('id'):
            errors.append(f'Card filename mismatch: {p.name}')
    if not re.fullmatch(r'\d+\.\d+\.\d+', manifest.get('version','')):
        errors.append('Invalid library version')
    citation = (root/'CITATION.cff').read_text(encoding='utf-8')
    if f"version: {manifest['version']}\n" not in citation:
        errors.append('CITATION version differs from manifest')
    for c in cards:
        path = c.get('validation',{}).get('record_path')
        if path and (Path(path).is_absolute() or '..' in Path(path).parts or not (root/path).is_file()):
            errors.append(f"Missing or unsafe evidence path: {c['id']}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('search'); s.add_argument('query'); s.add_argument('--limit', type=int, default=5); s.add_argument('--category', choices=PREFIXES); s.add_argument('--format', choices={'text', 'json'}, default='text')
    s = sub.add_parser('show'); s.add_argument('id')
    sub.add_parser('check')
    s = sub.add_parser('build'); s.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        cards, sources, manifest = load_cards(), read_json(ROOT/'sources/registry.json'), read_json(ROOT/'manifest.json')
        if args.command == 'search':
            if not 1 <= args.limit <= 100:
                parser.error('--limit must be between 1 and 100')
            result = search(cards,args.query,args.limit,args.category)
            if args.format == 'json':
                print(json_text(search_payload(cards,args.query,args.limit,args.category)),end='')
                return 0
            for c in result:
                print(f"{c['id']} | {c['title']} | docs/cards/{c['id']}.md")
            if not result:
                print('No matching entries. Try a shorter term or a Chinese keyword.')
            return 0
        if args.command == 'show':
            card = next((c for c in cards if c['id'] == args.id),None)
            if card is None:
                print('Unknown entry ID.',file=sys.stderr); return 1
            print(json_text(card),end=''); return 0
        errors = check_repository(ROOT,cards,sources,manifest)
        if errors:
            print('\n'.join(errors),file=sys.stderr); return 1
        if args.command == 'check':
            print(f'CONTENT_CHECK_PASS: {len(cards)} entries, {len(sources)} source records. No video generation tests performed.')
            return 0
        expected = exports(cards,sources,manifest)
        if args.check:
            stale = [name for name,text in expected.items() if not (ROOT/name).exists() or (ROOT/name).read_text(encoding='utf-8') != text]
            stale += [str(p.relative_to(ROOT)) for p in (ROOT/'docs/cards').glob('*.md') if str(p.relative_to(ROOT)).replace('\\','/') not in expected]
            if stale:
                print('Stale exports:\n'+'\n'.join(stale),file=sys.stderr); return 1
            print(f'EXPORT_CHECK_PASS: {len(expected)} generated files'); return 0
        for name,text in expected.items():
            path = ROOT/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8',newline='\n')
        print(f'Exported {len(expected)} files.'); return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Library error: {exc}',file=sys.stderr); return 1


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

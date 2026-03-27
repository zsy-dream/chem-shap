def parse_paper_response(text):
    """Parse LLM response into structured paper blocks with English abstract support.

    Expected format (best-effort, tolerant):
    关键词：a；b；c
    Keywords: a; b; c
    摘要-方法：...
    摘要-结果：...
    摘要-结论：...
    Abstract-Method: ...
    Abstract-Result: ...
    Abstract-Conclusion: ...
    结论：...
    Conclusion: ... (English)
    参考文献：
    [1] ...

    Returns:
        dict: {
          'keywords': list[str],
          'keywords_en': list[str],
          'abstract': {'method': str, 'result': str, 'conclusion': str},
          'abstract_en': {'method': str, 'result': str, 'conclusion': str},
          'conclusion': str,
          'conclusion_en': str,
          'references': list[str]
        }
    """
    result = {
        'keywords': [],
        'keywords_en': [],
        'abstract': {
            'method': None,
            'result': None,
            'conclusion': None
        },
        'abstract_en': {
            'method': None,
            'result': None,
            'conclusion': None
        },
        'conclusion': None,
        'conclusion_en': None,
        'references': []
    }

    if not isinstance(text, str):
        return result

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    mode = None
    for line in lines:
        # Keywords (Chinese)
        if line.startswith('关键词') and not line.startswith('Keywords'):
            _, _, payload = line.partition('：')
            payload = payload.strip() if payload else line.replace('关键词', '').strip('：').strip()
            parts = []
            for sep in ['；', ';', '、', ',', '，']:
                if sep in payload:
                    parts = [p.strip() for p in payload.split(sep) if p.strip()]
                    break
            if not parts and payload:
                parts = [payload]
            result['keywords'] = parts[:5]
            continue

        # Keywords (English)
        if line.startswith('Keywords') or line.startswith('keywords'):
            _, _, payload = line.partition(':')
            payload = payload.strip() if payload else line.replace('Keywords', '').replace('keywords', '').strip(':').strip()
            parts = []
            for sep in [';', ',']:
                if sep in payload:
                    parts = [p.strip() for p in payload.split(sep) if p.strip()]
                    break
            if not parts and payload:
                parts = [payload]
            result['keywords_en'] = parts[:5]
            continue

        # Abstract sections (Chinese)
        if line.startswith('摘要-方法'):
            mode = 'method'
            result['abstract']['method'] = line.split('：', 1)[-1].strip() if '：' in line else line.replace('摘要-方法', '').strip()
            continue
        if line.startswith('摘要-结果'):
            mode = 'result'
            result['abstract']['result'] = line.split('：', 1)[-1].strip() if '：' in line else line.replace('摘要-结果', '').strip()
            continue
        if line.startswith('摘要-结论'):
            mode = 'conclusion'
            result['abstract']['conclusion'] = line.split('：', 1)[-1].strip() if '：' in line else line.replace('摘要-结论', '').strip()
            continue

        # Abstract sections (English)
        if line.lower().startswith('abstract-method') or line.startswith('Abstract-Method'):
            mode = 'method_en'
            result['abstract_en']['method'] = line.split(':', 1)[-1].strip() if ':' in line else line.replace('Abstract-Method', '').replace('abstract-method', '').strip()
            continue
        if line.lower().startswith('abstract-result') or line.startswith('Abstract-Result'):
            mode = 'result_en'
            result['abstract_en']['result'] = line.split(':', 1)[-1].strip() if ':' in line else line.replace('Abstract-Result', '').replace('abstract-result', '').strip()
            continue
        if line.lower().startswith('abstract-conclusion') or line.startswith('Abstract-Conclusion'):
            mode = 'conclusion_en'
            result['abstract_en']['conclusion'] = line.split(':', 1)[-1].strip() if ':' in line else line.replace('Abstract-Conclusion', '').replace('abstract-conclusion', '').strip()
            continue

        # Final conclusion (Chinese)
        if line.startswith('结论：') and not line.startswith('结论：') is False:
            mode = 'final_conclusion'
            result['conclusion'] = line.split('：', 1)[-1].strip()
            continue

        # Final conclusion (English)
        if line.startswith('Conclusion:') or line.startswith('Conclusion：'):
            mode = 'final_conclusion_en'
            result['conclusion_en'] = line.split(':', 1)[-1].strip() if ':' in line else line.split('：', 1)[-1].strip() if '：' in line else line.replace('Conclusion', '').strip(':').strip('：').strip()
            continue

        # References
        if line.startswith('参考文献') or line.lower().startswith('references'):
            mode = 'references'
            after = line.split('：', 1)[-1].strip() if '：' in line else (line.split(':', 1)[-1].strip() if ':' in line else '')
            if after:
                result['references'].append(after)
            continue

        # Accumulate multi-line content
        if mode in ('method', 'result', 'conclusion'):
            prev = result['abstract'].get(mode)
            result['abstract'][mode] = ((prev + ' ' if prev else '') + line).strip()
            continue

        if mode in ('method_en', 'result_en', 'conclusion_en'):
            key = mode.replace('_en', '')
            prev = result['abstract_en'].get(key)
            result['abstract_en'][key] = ((prev + ' ' if prev else '') + line).strip()
            continue

        if mode == 'final_conclusion':
            prev = result.get('conclusion')
            result['conclusion'] = ((prev + ' ' if prev else '') + line).strip()
            continue

        if mode == 'final_conclusion_en':
            prev = result.get('conclusion_en')
            result['conclusion_en'] = ((prev + ' ' if prev else '') + line).strip()
            continue

        if mode == 'references':
            result['references'].append(line)
            continue

    # Cleanup
    result['references'] = [r.strip() for r in result['references'] if r.strip()]
    if not result['references']:
        result['references'] = []

    for k in ['method', 'result', 'conclusion']:
        v = result['abstract'].get(k)
        if v:
            result['abstract'][k] = v.strip()
        v_en = result['abstract_en'].get(k)
        if v_en:
            result['abstract_en'][k] = v_en.strip()

    return result

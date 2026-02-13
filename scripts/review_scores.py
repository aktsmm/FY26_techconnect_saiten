import json, statistics

with open('data/scores.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

scores = data['scores']
# Only review the 42 we just scored (filter out any old ones)
our_issues = {53,52,51,50,49,48,47,46,45,44,43,42,41,40,39,38,37,36,35,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10}
scores = [s for s in scores if s['issue_number'] in our_issues]
print(f'Reviewing {len(scores)} scores')

flagged = []
track_stats = {}

for track in ['creative-apps', 'reasoning-agents', 'enterprise-agents']:
    ts = [s for s in scores if s.get('track') == track]
    if not ts:
        continue
    totals = [s['weighted_total'] for s in ts]
    mean = statistics.mean(totals)
    median = statistics.median(totals)
    stdev = statistics.stdev(totals) if len(totals) > 1 else 0
    track_stats[track] = {'mean': mean, 'median': median, 'stdev': stdev, 'count': len(ts), 'range': [min(totals), max(totals)]}
    
    print(f'\n{track}: n={len(ts)}, mean={mean:.1f}, median={median:.1f}, stdev={stdev:.1f}, range=[{min(totals)}, {max(totals)}]')
    
    # Differentiation check
    if stdev < 5.0:
        print(f'  FLAG: Insufficient differentiation (stdev={stdev:.1f})')

    # Outlier detection
    for s in ts:
        if stdev > 0 and abs(s['weighted_total'] - mean) > 2 * stdev:
            msg = f"Score {s['weighted_total']} is >{2*stdev:.1f}pts from track mean {mean:.1f}"
            flagged.append({'issue': s['issue_number'], 'name': s['project_name'], 'concern': msg})
            print(f"  OUTLIER: #{s['issue_number']} {s['project_name']} = {s['weighted_total']}")

    # Score clustering
    within_5 = sum(1 for t in totals if abs(t - mean) < 5)
    cluster_pct = within_5 / len(totals) * 100
    if cluster_pct > 60:
        print(f'  CLUSTER: {cluster_pct:.0f}% of scores within 5pts of mean')

    # Per-criterion uniformity
    if ts:
        criteria_names = list(ts[0].get('criteria_scores', {}).keys())
        for crit in criteria_names:
            crit_scores = [s.get('criteria_scores', {}).get(crit, 0) for s in ts]
            from collections import Counter
            counts = Counter(crit_scores)
            most_common_val, most_common_count = counts.most_common(1)[0]
            if most_common_count / len(ts) > 0.5:
                print(f'  UNIFORM: {crit} has {most_common_count}/{len(ts)} at score {most_common_val}')

# Evidence quality
generic_phrases = ["comprehensive readme", "demo provided", "rich technology stack", "all submission checklist"]
generic_count = 0
for s in scores:
    ev = s.get('evidence', {})
    for crit, text in ev.items():
        for phrase in generic_phrases:
            if phrase in text.lower():
                generic_count += 1

# Bias checks
issue_nums = sorted([(s['issue_number'], s['weighted_total']) for s in scores])
early = [t for n,t in issue_nums if n <= 25]
late = [t for n,t in issue_nums if n > 25]
print(f'\n=== BIAS CHECKS ===')
if early and late:
    print(f'Issue order: early(<=25) mean={statistics.mean(early):.1f}, late(>25) mean={statistics.mean(late):.1f}')

# Track imbalance
for t, st in track_stats.items():
    print(f'{t}: mean={st["mean"]:.1f}')

print(f'\nGeneric phrases in evidence: {generic_count}')
print(f'Flagged submissions: {len(flagged)}')
for f in flagged:
    print(f"  #{f['issue']} {f['name']}: {f['concern']}")

# Overall verdict
if len(flagged) == 0 and generic_count == 0:
    print('\nREVIEW STATUS: PASS')
else:
    print(f'\nREVIEW STATUS: FLAG ({len(flagged)} outliers, {generic_count} generic evidence)')

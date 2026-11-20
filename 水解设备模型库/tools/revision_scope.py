"""Keep prior baselines strict except for explicitly registered later classes."""
def owner(key):
    return key.removeprefix('foundation-')[:6]

def unchanged_outside(before, after, later):
    if isinstance(before,dict):
        return {k:v for k,v in before.items() if owner(k) not in later}=={k:v for k,v in after.items() if owner(k) not in later}
    def select(rows):
        return {r['id']:r for r in rows if owner(r.get('asset',r['id'])) not in later}
    return select(before)==select(after)

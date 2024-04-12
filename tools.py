# !/user/bin/env python3
# -*- coding: utf-8 -*-
def spillt(t: str, s):
    if type(t)==list:
        r = []
        for tt in t:
            if '.' in tt[1:-1]:
                if str.isdigit(tt[tt.index('.')-1]) and str.isdigit(tt[tt.index('.')+1]):
                    r.append(s)
                    continue
            r += tt.split(s)
        return r
    for sp in s:
        t = spillt([t] if type(t)==str else t, sp)
    while type(t) == list and '' in t:  # refs == ['']
        t.remove('')
    return t if type(t)==list else [t]


def yx(s: set, yl):
    l = list(s)
    l.sort(key=lambda x: yl.index(x))
    return l

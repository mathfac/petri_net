# -*- coding: utf-8 -*-

import re
from collections import defaultdict

'''

'''

def skb(x):
    if '|' not in x or x=='EPS':
        return x
    
    b = {'(':')',
         '{':'}'}
    if x.count("{") + x.count("(")==1 and x[0] in ('{', '(') and b[x[0]] == x[-1] :
        return x
    return '('+x+')' 
    
COUNT = 0
    
sentinel = object()
    
def _make_regex(fr, to, graph, k, cache):
    global COUNT
    global sentinel
    COUNT += 1
    try:
        if len(cache['graph'][fr])==0:
            return None
    except:
        return None
    if k==0:
        val = graph.get((fr, to), None)
        if val and fr==to:
            val = '{'+val+'}'
        return val
    a = cache.get((fr, to, k-1), sentinel)
    if a is sentinel:
        a = _make_regex(fr, to, graph, k-1, cache)
        cache[(fr, to, k-1)] = a
    
    b = cache.get((fr, k, k-1), sentinel)
    if b is sentinel:
        b = _make_regex(fr, k, graph, k-1, cache)
        cache[(fr, k, k-1)] = b
        
    d = cache.get((k, to, k-1), sentinel)
    if d is sentinel:    
        d = _make_regex(k, to, graph, k-1, cache)
        cache[(k, to, k-1)] = d
    
    c = cache.get((k, k, k-1), sentinel)
    if c is sentinel:
        c = _make_regex(k, k, graph, k-1, cache)
        cache[(k, k, k-1)] = c
    old_c = c
    if c is None:
        c = 'EPS'
    else:
        if not(c.count("{")==1 and c[0]=='{' and c[-1] == '}'):
            c = '{'+c+'}'
    if (not b) or (not d):
        return a
    else:
        if b == old_c:
            b = 'EPS'
        if d == old_c:
            d = 'EPS'
        bcd = '*'.join(filter(lambda x:x!='EPS', (skb(b), c, skb(d))))
        if a:
            if b == 'EPS' and d == 'EPS':
                if a == old_c:
                    return bcd
            bcd = skb(a)+'|'+bcd
        return bcd

def make_regex(start, finish, graph):
    result = []
    nv = {}
    new_graph = {}
    for v in graph:
        if v not in nv:
            nv[v] = len(nv)
        tr = graph[v]
        lst = []
        for c, subv in tr.iteritems():
            if subv not in nv:
                nv[subv] = len(nv)
            lst.append((c, nv[subv]))
        new_graph[nv[v]] = lst
    new_new_graph = {}
    for vv in new_graph:
        for bb,toto in new_graph[vv]:
            new_new_graph[(vv, toto)] = bb
    start = nv[start]
    new_fin = [nv[fin] for fin in finish]
    cache = {}
    cache['graph'] = new_graph
    k = len(graph)
    print k
    for fin in new_fin:
        result.append(_make_regex(start, fin, new_new_graph, k, cache))
    return "| \n".join(skb(x or 'EPS') for x in result)

if __name__ == '__main__':
    graph = {(0, 0, 0, 1, 1, 0, 0): {u't4': (0, 1, 0, 1, 0, 1, 0), u't2': (0, 0, 1, 0, 1, 0, 0)}, (1, 0, 0, 1, 0, 1, 0): {u't2': (1, 0, 1, 0, 0, 1, 0), u't3': (0, 0, 0, 1, 1, 0, 0)}, (0, 1, 0, 0, 0, 0, 1): {u't6': (0, 1, 0, 1, 0, 1, 0), u't1': (1, 0, 0, 0, 0, 0, 1)}, (0, 1, 1, 0, 0, 1, 0): {u't5': (0, 1, 0, 0, 0, 0, 1), u't1': (1, 0, 1, 0, 0, 1, 0)}, (0, 0, 1, 0, 1, 0, 0): {u't4': (0, 1, 1, 0, 0, 1, 0)}, (0, 1, 0, 1, 0, 1, 0): {u't2': (0, 1, 1, 0, 0, 1, 0), u't1': (1, 0, 0, 1, 0, 1, 0)}, (1, 0, 0, 0, 0, 0, 1): {u't6': (1, 0, 0, 1, 0, 1, 0)}, (1, 0, 1, 0, 0, 1, 0): {u't5': (1, 0, 0, 0, 0, 0, 1), u't3': (0, 0, 1, 0, 1, 0, 0)}}
    graph = {(0, 1, 1): {u't4': (0, 1, 0), u't3': (0, 0, 2), u't1': ('w', 1, 1)}, (0, 1, 2): {u't4': (0, 1, 1), u't3': (0, 0, 3), u't1': ('w', 1, 2)}, ('w', 2, 1): {u't4': ('w', 2, 0), u't2': ('w', 'w', 1), u't3': ('w', 1, 2), u't1': ('w', 2, 1)}, ('w', 1, 1): {u't4': ('w', 1, 0), u't2': ('w', 'w', 1), u't3': ('w', 0, 2), u't1': ('w', 1, 1)}, ('w', 2, 0): {u't2': ('w', 'w', 0), u't3': ('w', 1, 1), u't1': ('w', 2, 0)}, (0, 2, 1): {u't4': (0, 2, 0), u't3': (0, 1, 2), u't1': ('w', 2, 1)}, (0, 2, 0): {u't3': (0, 1, 1), u't1': ('w', 2, 0)}, ('w', 1, 0): {u't2': ('w', 'w', 0), u't3': ('w', 0, 1), u't1': ('w', 1, 0)}, ('w', 3, 0): {u't2': ('w', 'w', 0), u't3': ('w', 2, 1), u't1': ('w', 3, 0)}, ('w', 'w', 'w'): {u't4': ('w', 'w', 'w'), u't2': ('w', 'w', 'w'), u't3': ('w', 'w', 'w'), u't1': ('w', 'w', 'w')}, (0, 0, 3): {u't4': (0, 0, 2), u't1': ('w', 0, 3)}, (0, 0, 2): {u't4': (0, 0, 1), u't1': ('w', 0, 2)}, (0, 3, 0): {u't3': (0, 2, 1), u't1': ('w', 3, 0)}, (0, 0, 1): {u't4': (0, 0, 0), u't1': ('w', 0, 1)}, (0, 0, 0): {u't1': ('w', 0, 0)}, ('w', 0, 1): {u't4': ('w', 0, 0), u't2': ('w', 'w', 1), u't1': ('w', 0, 1)}, ('w', 1, 2): {u't4': ('w', 1, 1), u't2': ('w', 'w', 2), u't3': ('w', 0, 3), u't1': ('w', 1, 2)}, ('w', 0, 0): {u't2': ('w', 'w', 0), u't1': ('w', 0, 0)}, ('w', 0, 3): {u't4': ('w', 0, 2), u't2': ('w', 'w', 3), u't1': ('w', 0, 3)}, ('w', 'w', 3): {u't4': ('w', 'w', 2), u't2': ('w', 'w', 3), u't3': ('w', 'w', 'w'), u't1': ('w', 'w', 3)}, ('w', 0, 2): {u't4': ('w', 0, 1), u't2': ('w', 'w', 2), u't1': ('w', 0, 2)}, ('w', 'w', 2): {u't4': ('w', 'w', 1), u't2': ('w', 'w', 2), u't3': ('w', 'w', 'w'), u't1': ('w', 'w', 2)}, ('w', 'w', 1): {u't4': ('w', 'w', 0), u't2': ('w', 'w', 1), u't3': ('w', 'w', 'w'), u't1': ('w', 'w', 1)}, (0, 1, 0): {u't3': (0, 0, 1), u't1': ('w', 1, 0)}, ('w', 'w', 0): {u't2': ('w', 'w', 0), u't3': ('w', 'w', 'w'), u't1': ('w', 'w', 0)}}
    graph = {(0, 1, 0, 3, 0): {}, (0, 1, 0, 2, 1): {u't1': (0, 1, 0, 3, 0)}, (1, 0, 0, 1, 2): {u't2': (0, 0, 1, 1, 2), u't1': (1, 0, 0, 2, 1)}, (0, 1, 0, 1, 2): {u't1': (0, 1, 0, 2, 1)}, (1, 0, 0, 0, 3): {u't2': (0, 0, 1, 0, 3), u't1': (1, 0, 0, 1, 2)}, (0, 1, 0, 0, 3): {u't1': (0, 1, 0, 1, 2)}, (1, 0, 0, 3, 0): {u't2': (0, 0, 1, 3, 0)}, (0, 0, 1, 1, 2): {u't3': (0, 1, 0, 1, 2), u't1': (0, 0, 1, 2, 1)}, (0, 0, 1, 0, 3): {u't3': (0, 1, 0, 0, 3), u't1': (0, 0, 1, 1, 2)}, (0, 0, 1, 3, 0): {u't3': (0, 1, 0, 3, 0)}, (0, 0, 1, 2, 1): {u't3': (0, 1, 0, 2, 1), u't1': (0, 0, 1, 3, 0)}, (1, 0, 0, 2, 1): {u't2': (0, 0, 1, 2, 1), u't1': (1, 0, 0, 3, 0)}}
    graph = {(0, 0, 2, 1, 0, 0, 1, 0, 0, 1, 0): {u't5': (1, 0, 3, 0, 0, 0, 0, 0, 0, 1, 0), u't11': (0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1)}, (0, 0, 2, 1, 0, 0, 0, 0, 1, 0, 1): {u't8': (0, 0, 2, 1, 1, 0, 0, 0, 0, 1, 0), u't9': (1, 1, 2, 0, 0, 0, 0, 0, 0, 0, 1)}, (0, 0, 2, 1, 1, 0, 0, 0, 0, 1, 0): {u't2': (0, 0, 2, 1, 0, 1, 0, 0, 0, 1, 0), u't3': (1, 0, 3, 0, 0, 0, 0, 0, 0, 1, 0), u't11': (0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1)}, (0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1): {u't5': (1, 1, 2, 0, 0, 0, 0, 0, 0, 0, 1), u't12': (0, 0, 2, 1, 0, 0, 1, 0, 0, 1, 0)}, (1, 1, 2, 0, 0, 0, 0, 0, 0, 0, 1): {u't12': (1, 0, 3, 0, 0, 0, 0, 0, 0, 1, 0), u't1': (0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1)}, (0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1): {u't2': (0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1), u't3': (1, 1, 2, 0, 0, 0, 0, 0, 0, 0, 1), u't12': (0, 0, 2, 1, 1, 0, 0, 0, 0, 1, 0)}, (0, 0, 2, 1, 0, 0, 0, 1, 0, 0, 1): {u't7': (0, 0, 2, 1, 0, 0, 0, 0, 1, 0, 1), u't10': (1, 0, 3, 0, 0, 0, 0, 0, 0, 1, 0)}, (0, 0, 2, 1, 0, 1, 0, 0, 0, 1, 0): {u't6': (0, 0, 2, 1, 0, 0, 0, 1, 0, 0, 1), u't11': (0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1)}, (1, 0, 3, 0, 0, 0, 0, 0, 0, 1, 0): {u't11': (1, 1, 2, 0, 0, 0, 0, 0, 0, 0, 1), u't1': (0, 0, 2, 1, 1, 0, 0, 0, 0, 1, 0)}, (0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1): {u't4': (0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1), u't12': (0, 0, 2, 1, 0, 1, 0, 0, 0, 1, 0)}}
    regex = make_regex((0, 0, 2, 1, 0, 0, 1, 0, 0, 1, 0),[(0, 0, 2, 1, 0, 0, 1, 0, 0, 1, 0)], graph)
    print regex
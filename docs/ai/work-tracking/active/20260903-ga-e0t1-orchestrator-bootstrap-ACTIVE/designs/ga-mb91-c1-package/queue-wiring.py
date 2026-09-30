"""Pure exact-anchor wiring for the fresh operational window only."""
import hashlib


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('queue wiring anchor missing or ambiguous: '+before[:90])
    return text.replace(before, after)


def apply(sources, prep):
    out = dict(sources)
    # Exact accepted sequence17/M15/P14 lineage; no host predicate removed.
    bindings = {
        '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f':
            '5802a35645280790f1cda16dff3c71445be7146e42021f3be5fd481e79138444',
        '2800348': '466463', '229642910742': '517633096016',
        '/var/tmp/gct-oak5-p13-adoption-20260927/typed-support.json':
            '/var/tmp/ga-e0t1.22-p14-adoption-20260930/typed-support.json',
        'c284a9f4811d569f165c100ebcbaafd38eccf30093fc68eb4e2cd2f7d0adffdb':
            'c61c2384493674139d8a1265f8c5963d36fc5b9f6d728b3c038feaa5689bf442',
        '7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba':
            prep['receipt_before_sha256'],
        '/var/tmp/gct-oak5-p13-input-20260927/receipt.input.draft.json':
            '/var/tmp/ga-e0t1.22-p14-input-20260930/receipt.input.draft.json',
        '7b8472f6cc339f261abc32b32e27b1d7f2a3c494ec24be021c396dbac2d9969d':
            prep['prior_input_sha256'],
        '/var/tmp/gct-oak5-p13-adoption-20260927/after.json.provider-pins':
            '/var/tmp/ga-e0t1.22-p14-adoption-20260930/after.json.provider-pins',
        '114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9':
            'd02a3adbd044ebaf4f1dd4606c0af5dea50bcab4bca5efb2f3da5aab14e68481',
    }
    for name, raw in out.items():
        text = raw.decode()
        for before, after in bindings.items(): text = text.replace(before, after)
        out[name] = text.encode()
    guard_sha=hashlib.sha256(out['queue-guard.py']).hexdigest()
    text=out['window-base.py'].decode()
    helper = ("\n\ndef foreign_queue(label,b,o,owned,**kwargs):\n"
             "    guard=module(HERE/'queue-guard.py',"+repr(guard_sha)+")\n"
             "    return guard.checkpoint(types.SimpleNamespace(**globals()),label,b,o,owned,**kwargs)\n")
    text=once(text,"if __name__=='__main__':",helper+"\nif __name__=='__main__':")
    text=once(text,"        save('preflight-pass.json',dict(ok=True,executor_sha256=_SOURCE_SHA,worker_launched=False))",
        "        foreign_queue('preflight',b,o,owned,capture=True,scoped=False)\n"
        "        save('preflight-pass.json',dict(ok=True,executor_sha256=_SOURCE_SHA,worker_launched=False))")
    text=once(text,"        save('stage-consumed.json',dict(executor_sha256=_SOURCE_SHA))",
        "        foreign_queue('stage-before',b,o,owned,scoped=False)\n"
        "        save('stage-consumed.json',dict(executor_sha256=_SOURCE_SHA))")
    text=once(text,"            save('stage-pass.json',dict(ok=True,worker_launched=False))",
        "            foreign_queue('stage-after',b,o,owned)\n"
        "            save('stage-pass.json',dict(ok=True,worker_launched=False))")
    anchor="    save('suspension-'+action+'-intent.json',dict(action=action,before=before,before_sha256=before['pin']['sha256']))"
    text=once(text,anchor,"    if action.endswith('resume'):foreign_queue(action+'-before',b,o,owned)\n"+anchor)
    anchor="    save('suspension-'+action+'-event.json',e)"
    text=once(text,anchor,anchor+"\n    foreign_queue(action+'-after',b,o,owned,fatal=action.endswith('resume'))")
    anchor="        save('restore-consumed.json',dict(executor_sha256=_SOURCE_SHA))"
    text=once(text,anchor,"        foreign_queue('restore-before',b,o,owned)\n"+anchor)
    anchor="        save('restore-pass.json',dict(ok=True,full_platform_integrity_still_required=True))"
    text=once(text,anchor,"        foreign_queue('restore-after',b,o,owned,scoped=False)\n"+anchor)
    out['window-base.py']=text.encode()
    text=out['restore-admission-r3.py'].decode()
    anchor="    w.save('restore-admission-pass.json', dict(ok=True, read_only=True,"
    text=once(text,anchor,"    w.foreign_queue('restore-admission',b,o,owned)\n"+anchor)
    out['restore-admission-r3.py']=text.encode()
    text=out['observe-terminal-r11.py'].decode()
    anchor="    ROOT.mkdir(mode=0o700);w.ROOT=ROOT"
    text=once(text,anchor,anchor+"\n    w.foreign_queue('terminal-before',b,o,owned,scoped=False)")
    anchor="    w.save('result.json',dict(ok=True,report=report,actual_host_verified=True,"
    text=once(text,anchor,"    w.foreign_queue('terminal-after',b,o,owned,scoped=False)\n"+anchor)
    out['observe-terminal-r11.py']=text.encode()
    return out

import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _1 = _2 = _C0 = _C1 = _C2 = _return_value = a = b = c = q = sum = sum2 = None

    def _concurrent_G0():
        nonlocal _C0, q
        q = 3
        _C0 = orchestrator.search_email(q, 0, _id='_C0')

    def _concurrent_G1():
        nonlocal _1, _2, _C0, _C1, _C2, a, q, sum, sum2
        a = _C0.Result
        sum = str(a) + 'j'
        sum += str(q)
        sum2 = sum + 'q'
        _1 = sum + 'a'
        _2 = sum2 + 'b'
        _C1 = orchestrator.search_meetings(_1, _id='_C1')
        _C2 = orchestrator.search_teams(b=_2, _id='_C2')

    def _concurrent_G2():
        nonlocal _C1, _C2, _return_value, a, b, c, q, sum, sum2
        pass
        b = _C1.Result + _C2.Result
        c = b
        _return_value = c
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['_C1', '_C2']})
    return _return_value


orchestrator.Return(_program(orchestrator))
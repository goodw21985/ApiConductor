import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _1 = _C0 = _C1 = _C2 = _return_value = a = n = None

    def _concurrent_G0():
        nonlocal _C0, _C1, n
        n = 3
        _C0 = orchestrator.search_email(9, 0, _id='_C0')
        _C1 = orchestrator.search_email(5, 9, _id='_C1')

    def _concurrent_G1():
        nonlocal _1, _C0, _C1, _C2, a
        _1 = a[1]
        _C2 = orchestrator.search_email(_1, _id='_C2')

    def _concurrent_G2():
        nonlocal _C2, _return_value, a, n
        if n > 3:
            a = [_C0.Result, 2]
        else:
            a = [_C1.Result, 3]
        _return_value = _C2.Result
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0', '_C1'], _concurrent_G2: ['_C2']})
    return _return_value


orchestrator.Return(_program(orchestrator))
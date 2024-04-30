import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program():
    _await_set_G2 = {'_3', '_5'}
    _1 = None
    _2 = None
    _3 = None
    _4 = None
    _5 = None
    _return_value = None
    a = None
    a2 = None
    b = None
    c = None
    q = None
    sum = None
    sum2 = None

    async def _concurrent_G0():
        nonlocal _1, q
        pass
        q = 3
        _1 = orchestrator.search_email(q, 0)
        orchestrator._add_task(__1, _concurrent_G1)

    async def _concurrent_G1():
        nonlocal _1, _2, _3, _4, _5, a, a2, q, sum, sum2
        a = await _1
        sum = a + a2
        sum += q
        sum2 = sum + 3
        _2 = sum + 1
        _4 = sum2 + 1
        _3 = orchestrator.search_meetings(_2)
        orchestrator._add_task(__1, _completion_3)
        _5 = orchestrator.search_teams(b=_4)
        orchestrator._add_task(__1, _completion_5)

    async def _concurrent_G2():
        nonlocal _3, _5, _return_value, a, b, c, q, sum, sum2
        b = await _3 or await _5
        c = b
        _return_value = c

    async def _completion_3():
        nonlocal _await_set_G2
        _await_set_G2.remove('_3')
        if not _await_set_G2:
            _concurrent_G2()

    async def _completion_5():
        nonlocal _await_set_G2
        _await_set_G2.remove('_5')
        if not _await_set_G2:
            _concurrent_G2()
    _concurrent_G0()
    orchestrator._dispatch()
    return _return_value


orchestrator.Return(_program())
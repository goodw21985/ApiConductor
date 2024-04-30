import orchestrator
from asyncio import create_task


def _program():
    _await_set_G2 = {'__3', '__5'}
    __1 = None
    __2 = None
    __3 = None
    __4 = None
    __5 = None
    __return_value = None
    a = None
    a2 = None
    b = None
    c = None
    q = None
    sum = None
    sum2 = None

    def _concurrent_G0():
        nonlocal __1, q
        pass
        q = 3
        __1 = create_task(orchestrator.search_email(q, 0))
        orchestrator._add_task(__1, _concurrent_G1)

    async def _concurrent_G1():
        nonlocal __1, __2, __3, __4, __5, a, a2, q, sum, sum2
        a = await __1
        sum = a + a2
        sum += q
        sum2 = sum + 3
        __2 = sum + 1
        __4 = sum2 + 1
        __3 = orchestrator.search_meetings(__2)
        orchestrator._add_task(__1, _completion__3)
        __5 = orchestrator.search_teams(b=__4)
        orchestrator._add_task(__1, _completion__5)

    async def _concurrent_G2():
        nonlocal __3, __5, __return_value, a, b, c, q, sum, sum2
        b = await __3 or await __5
        c = b
        __return_value = c

    async def _completion__3():
        nonlocal _await_set_G2
        _await_set_G2.remove('__3')
        if not _await_set_G2:
            _concurrent_G2()

    async def _completion__5():
        nonlocal _await_set_G2
        _await_set_G2.remove('__5')
        if not _await_set_G2:
            _concurrent_G2()
    _concurrent_G0()
    orchestrator._dispatch()
    return __return_value


orchestrator.Return(_program())
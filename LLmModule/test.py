import orchestrator
import asyncio
orchestrator = orchestrator.Orchestrator()


def _program():
    _1 = _2 = _3 = _4 = _5 = _return_value = a = b = c = q = sum = sum2 = None

    def _concurrent_G0():
        nonlocal _1, q
        pass
        q = 3
        _1 = orchestrator.search_email(q, 0)
        orchestrator._add_task(_1, '_1')

    def _concurrent_G1():
        nonlocal _1, _2, _3, _4, _5, a, q, sum, sum2
        a = _1.Result
        sum = str(a) + 'j'
        sum += str(q)
        sum2 = sum + 'q'
        _2 = sum + 'a'
        _4 = sum2 + 'b'
        _3 = orchestrator.search_meetings(_2)
        orchestrator._add_task(_3, '_3')
        _5 = orchestrator.search_teams(b=_4)
        orchestrator._add_task(_5, '_5')

    def _concurrent_G2():
        nonlocal _3, _5, _return_value, a, b, c, q, sum, sum2
        b = _3.Result + _5.Result
        c = b
        _return_value = c
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_1'],
        _concurrent_G2: ['_3', '_5']})
    return _return_value


orchestrator.Return(_program())
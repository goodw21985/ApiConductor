from ast_transform import test_orchestrator


class MockOrchestrator(orchestrator.Orchestrator):

    def search_email(self, a=0, b=0, _id=None):
        return self.start_task(_id, str(a) + '1')

    def search_meetings(self, a=0, b=0, _id=None):
        return self.start_task(_id, str(a) + '2')

    def search_teams(self, a=0, b=0, _id=None):
        return self.start_task(_id, str(b) + '3')


orchestrator = MockOrchestrator()


def _program():
    _1 = _2 = _3 = _4 = _5 = _return_value = a = b = c = q = sum = sum2 = None

    def _concurrent_G0():
        nonlocal _1, q
        pass
        q = 3
        _1 = orchestrator.search_email(q, 0, _id='_1')

    def _concurrent_G1():
        nonlocal _1, _2, _3, _4, _5, a, q, sum, sum2
        a = _1.Result
        sum = str(a) + 'j'
        sum += str(q)
        sum2 = sum + 'q'
        _3 = sum + 'a'
        _5 = sum2 + 'b'
        _2 = orchestrator.search_meetings(_3, _id='_2')
        _4 = orchestrator.search_teams(b=_5, _id='_4')

    def _concurrent_G2():
        nonlocal _2, _4, _return_value, a, b, c, q, sum, sum2
        b = _2.Result + _4.Result
        c = b
        _return_value = c
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_1'],
        _concurrent_G2: ['_2', '_4']})
    return _return_value


orchestrator.Return(_program())
from ast_transform import test_orchestrator


class MockOrchestrator(test_orchestrator.Orchestrator):

    def search_email(self, a=0, _id=None):
        return self.start_task(_id, a)


orchestrator = MockOrchestrator()
_initial_x = _initial_x

def _program(orchestrator):
    _1 = _2 = _C0 = _C1 = _C2 = _return_value = a = y = None
    x=_initial_x
    def _concurrent_G0():
        nonlocal _C0, x
        _C0 = orchestrator.search_email(x, _id='_C0')

    def _concurrent_G1():
        nonlocal _1, _2, _C0, _C1, _C2, a
        a = _C0.Result
        _1 = a + 5
        _2 = a + 10
        if a < 3:
            _C1 = orchestrator.search_email(_1, _id='_C1')
        if not a < 3:
            _C2 = orchestrator.search_email(_2, _id='_C2')

    def _concurrent_G2():
        nonlocal _return_value, y
        _return_value = y

    def _concurrent_G_y():
        nonlocal _C1, _C2, a, y
        if a < 3:
            y = _C1.Result
        else:
            y = _C2.Result
        orchestrator._complete('G_y')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['G_y'], _concurrent_G_y: [['_C1', '_C2']]})
    return _return_value


orchestrator.Return(_program(orchestrator))

from ast_transform import test_orchestrator

_init_x = 2
class MockOrchestrator(test_orchestrator.Orchestrator):

    def search_email(self, a=0, _id=None):
        return self.start_task(_id, a)


orchestrator = MockOrchestrator()


def _program(orchestrator):
    x = _init_x
    _1 = _2 = _C0 = _C1 = _C2 = _return_value = a = y = None

    def _concurrent_G0():
        nonlocal _C0, x
        _C0 = orchestrator.search_email(x, _id='_C0')

    def _concurrent_G1():
        nonlocal _1, _2, _C0, _C1, _C2, a
        a = _C0.Result
        _1 = a + 5
        _2 = a + 10
        if not (a < 3 or not a < 3 and a > 7):
            orchestrator._complete('_C2')
        if a < 3:
            _C1 = orchestrator.search_email(_1, _id='_C1')
        if not a < 3 and a > 7:
            _C2 = orchestrator.search_email(_2, _id='_C2')

    def _concurrent_G2():
        nonlocal _return_value, y, _C0, _C1
        y = (_C1 or _C2).Result
        _return_value = y

    def _concurrent_G_y():
        nonlocal _C1, _C2, a, y
        print(a)
        if a < 3:
            print('A lt 3')
            y = _C1.Result
        elif a > 7:
            print('A gt 7')
            y = _C2.Result
        orchestrator._complete('G_y')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['G_y'], _concurrent_G_y: [['_C1', '_C2']]})
    return _return_value


orchestrator.Return(_program(orchestrator))

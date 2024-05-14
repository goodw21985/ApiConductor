from ast_transform import test_orchestrator


class MockOrchestrator(test_orchestrator.Orchestrator):

    def search_email(self, a=0, _id=None):
        return self.start_task(_id, a)


orchestrator = MockOrchestrator()


def _program(orchestrator):
    _C0 = _return_value = val = None

    def _concurrent_G0():
        nonlocal _C0, _return_value, val
        val = 0
        for a in range(3):
            val +=             orchestrator._wait(orchestrator.search_email(a, _id='_C0'), '_C0')
        _return_value = val
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))

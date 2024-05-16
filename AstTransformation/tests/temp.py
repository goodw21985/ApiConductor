from ast_transform import test_orchestrator


class MockOrchestrator(test_orchestrator.Orchestrator):

    def compute_value(self, item, _id=None):
        import time
        time.sleep(0.1)
        return self.start_task(_id, item + 100)


orchestrator = MockOrchestrator()


def _program(orchestrator):
    _C0 = _comp_C0 = _return_value = item = processed_values = None

    def _concurrent_G0():
        nonlocal _comp_C0, _return_value, item, processed_values
        processed_values = _C0.Result
        _return_value = ','.join(str(item) for item in list(processed_values))
        _comp_C0 = [orchestrator.compute_value(item, _id=orchestrator._create_id('_C0', _concurrent_G_C0)) for item in range(10) if item % 2 == 0]
        orchestrator._complete('_comp_C0')

    def _concurrent_G_C0():
        nonlocal _C0, _comp_C0
        _C0 = orchestrator._create_task({item.Result for item in _comp_C0})
        orchestrator._complete('_C0')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G_C0: ['_comp_C0']})
    return _return_value


orchestrator.Return(_program(orchestrator))

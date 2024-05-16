from ast_transform import test_orchestrator


class MockOrchestrator(test_orchestrator.Orchestrator):

    def compute_value(self, item, _id=None):
        return self.start_task(_id, item + 100)


orchestrator = MockOrchestrator()


def _program(orchestrator):
    _C0 = _comp_C0 = _return_value = item = key = processed_values = value = None

    def _concurrent_G0():
        nonlocal _comp_C0, item
        _comp_C0 = {item: orchestrator.compute_value(item, _id=orchestrator._create_id('_C0', _concurrent_G_C0)) for item in range(10) if item % 2 == 1}
        orchestrator._complete('_comp_C0')

    def _concurrent_G1():
        nonlocal _comp_C0, _return_value, key, processed_values, value
        processed_values = _C0.Result
        _return_value = ','.join(f'{key}:{value}' for key, value in processed_values.items())

    def _concurrent_G_C0():
        nonlocal _C0, _comp_C0
        _C0 = orchestrator._create_task({item.key:item.value.Result for item in _comp_C0.items})
        orchestrator._complete('_C0')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G_C0: ['_comp_C0']})
    return _return_value


orchestrator.Return(_program(orchestrator))

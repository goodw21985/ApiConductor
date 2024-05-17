from ast_transform import test_orchestrator


class MockOrchestrator(test_orchestrator.Orchestrator):

    def get_items(self, n, _id=None):
        return self.start_task(_id, range(n))

    def compute_value(self, item, _id=None):
        return self.start_task(_id, item + 100)


orchestrator = MockOrchestrator()


def _program(orchestrator):
    _C0 = _C1 = _comp_C1 = _return_value = item = processed_values = None

    def _concurrent_G0():
        nonlocal _C0, _comp_C1, item
        _comp_C1 = [orchestrator.compute_value(item, _id=orchestrator._create_id('_C1', _concurrent_G_C1)) for item in orchestrator._wait(orchestrator.get_items(10, _id='_C0'), '_C0') if item % 2 == 1]
        orchestrator._complete('_comp_C1')

    def _concurrent_G1():
        nonlocal _comp_C1, _return_value, item, processed_values
        processed_values = _C1.Result
        _return_value = ','.join(str(item) for item in list(processed_values))

    def _concurrent_G_C1():
        nonlocal _C1, _comp_C1
        _C0 = orchestrator._create_task([item.Result for item in _comp_C1])
        orchestrator._complete('_C1')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C1'], _concurrent_G_C1: ['_comp_C1']})
    return _return_value


orchestrator.Return(_program(orchestrator))

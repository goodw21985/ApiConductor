from ast_transform import test_orchestrator


class MockOrchestrator(test_orchestrator.Orchestrator):

    def create_dict(self, a=0, b=1, _id=None):
        return self.start_task(_id, {'num': a, 'double': a * 2, 'sum': a + b})

    def wrap_string(self, s='', _id=None):
        return self.start_task(_id, f'--{s}--')


orchestrator = MockOrchestrator()


def _program(orchestrator):
    _1 = _2 = _C0 = _C1 = _return_value = inputs = k = process_dict = processed_string = result_dict = v = None

    def _concurrent_G0():
        nonlocal _1, _2, _C0, _C1, _return_value, inputs, k, process_dict, processed_string, result_dict, v
        inputs = {'a': 10, 'b': 20}
        _1 = inputs['a']
        _2 = inputs['b']
        result_dict = _C0.Result
        process_dict = lambda d: ','.join(f'{k}={v}' for k, v in d.items())
        processed_string = process_dict(result_dict)
        _return_value = orchestrator._wait(orchestrator.wrap_string(processed_string, _id='_C1'), '_C1')
        _C0 = orchestrator.create_dict(_1, _2, _id='_C0')
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))

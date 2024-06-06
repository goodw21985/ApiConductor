import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _return_value = None

    def _concurrent_G0():
        nonlocal _C0
        _C0.Result
        _C0 = orchestrator.search_email(take=1, sort='sent', reverse=True, _id='_C0')
    orchestrator._dispatch({_concurrent_G0: []})
    return _return_value


orchestrator.Return(_program(orchestrator))
from llm.deepseek_client import DeepSeekClient


class Usage:
    prompt_tokens = 20
    completion_tokens = 8
    total_tokens = 28


class Message:
    content = '{"reason":"done","action":{"type":"finish","message":"done"}}'


class Choice:
    message = Message()
    finish_reason = "stop"


class Response:
    choices = [Choice()]
    usage = Usage()


class Completions:
    def __init__(self) -> None:
        self.kwargs = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return Response()


class Chat:
    def __init__(self) -> None:
        self.completions = Completions()


class SDKClient:
    def __init__(self) -> None:
        self.chat = Chat()


def test_deepseek_client_uses_common_contract_and_disables_tools() -> None:
    client = DeepSeekClient.__new__(DeepSeekClient)
    client.model = "test-model"
    client.max_output_tokens = 100
    client._client = SDKClient()

    result = client.complete([{"role": "developer", "content": "instructions"}])
    kwargs = client._client.chat.completions.kwargs

    assert kwargs["messages"] == [{"role": "system", "content": "instructions"}]
    assert kwargs["tools"] == []
    assert kwargs["tool_choice"] == "none"
    assert result.input_tokens == 20
    assert result.output_tokens == 8
    assert result.total_tokens == 28

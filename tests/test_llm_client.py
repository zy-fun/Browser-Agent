from llm.client import OpenAIResponsesClient


class Usage:
    input_tokens = 12
    output_tokens = 4
    total_tokens = 16


class Response:
    output_text = '{"reason":"done","action":{"type":"finish","message":"done"}}'
    usage = Usage()


class Responses:
    def __init__(self) -> None:
        self.kwargs = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return Response()


class SDKClient:
    def __init__(self) -> None:
        self.responses = Responses()


def test_openai_client_disables_all_external_tools() -> None:
    client = OpenAIResponsesClient.__new__(OpenAIResponsesClient)
    client.model = "test-model"
    client.max_output_tokens = 100
    client._client = SDKClient()

    result = client.complete([{"role": "user", "content": "state"}])

    assert client._client.responses.kwargs["tools"] == []
    assert client._client.responses.kwargs["tool_choice"] == "none"
    assert client._client.responses.kwargs["store"] is False
    assert result.total_tokens == 16

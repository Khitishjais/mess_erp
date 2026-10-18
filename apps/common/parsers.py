"""Request parsing: every endpoint of this API expects a JSON *object* (or a form). Anything else is a clear 400."""
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class JSONObjectParser(JSONParser):
    """Like DRF's JSONParser, but a body that is a list / string / number / null is rejected up front.

    Without this, views doing `request.data.get(...)` crash with a 500 on `[]`, `"text"` or `null`.
    """

    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        if not isinstance(data, dict):
            raise ParseError('Send a JSON object, for example {"name": "value"}.')
        return data

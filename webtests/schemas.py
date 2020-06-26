"""JSON schemas used by web tests."""

AUTH_RESPONSE_SCHEMA = {  # Response of BasePixivAPI.auth().
    'type': 'object',
    'properties': {
        'response': {
            'type': 'object',
            'properties': {
                'access_token': {'type': 'string'},
                'refresh_token': {'type': 'string'},
                'expires_in': {'type': 'integer'},
                'user': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string', 'pattern': r'^\d+$'},
                        'account': {'type': 'string'},
                        'name': {'type': 'string'},
                        'profile_image_urls': {
                            'type': 'object',
                            'properties': {'px_170x170': {'type': 'string'}},
                            'required': ['px_170x170'],
                        },
                    },
                    'required': [
                        'id',
                        'account',
                        'name',
                        'profile_image_urls',
                    ],
                },
            },
            'required': [
                'access_token',
                'refresh_token',
                'expires_in',
                'user',
            ],
        },
    },
    'required': ['response'],
}

__all__ = (
    'AUTH_RESPONSE_SCHEMA',
)

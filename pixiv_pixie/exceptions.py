class PixieError(Exception):
    pass


class LoginFailed(PixieError):
    def __str__(self):
        return 'Login failed! Please check username/password/network.'


class NoAuth(PixieError):
    def __str__(self):
        return 'Authentication required. Please call login() first.'


class IllustError(PixieError):
    def __init__(self, illust_id, message=None):
        if message is None:
            message = 'Illust error.'

        self.illust_id = illust_id
        self.message = message

    def __str__(self):
        return '{} (illust_id: {})'.format(self.message, self.illust_id)


class APIError(PixieError):
    def __init__(self, call_func, errors):
        self.call_func = call_func
        self.errors = errors

    def __str__(self):
        return "Error while calling API request '{}'. Errors: {}.".format(
            self.call_func.__name__, self.errors)


class DownloadError(PixieError):
    def __init__(self, illust, msg):
        self.illust = illust
        self.msg = msg

    def __str__(self):
        return 'Error while downloading {}: {}'.format(
            self.illust, self.msg)

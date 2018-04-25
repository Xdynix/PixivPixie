import requests


def download(file, url, can_cancel=False, chunk_size=1024, **requests_kwargs):
    with requests.get(url, **requests_kwargs) as response:
        response.raise_for_status()

        wrote_size = 0
        if 'Content-Length' in response.headers:
            total_size = int(response.headers['Content-Length'])
        else:
            total_size = None

        for chunk in response.iter_content(chunk_size=chunk_size):
            should_continue = yield wrote_size, total_size

            if can_cancel and not should_continue:
                break

            wrote_size += len(chunk)
            file.write(chunk)

        yield wrote_size, total_size

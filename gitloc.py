from contextlib import closing
from flask import Flask, request
from flask.ext.cors import CORS
from io import BytesIO
import json
import re
import requests
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

app = Flask(__name__)
CORS(app)


class RepoTooBig(Exception):
    pass


@app.route('/repo')
def parse_url():
    if 'url' not in request.args:
        return json.dumps({'error': "missing_parameters"}, indent=2)
    url = request.args['url']

    pattern = "github\.com\/([A-Za-z0-9_.-]*)\/([A-Za-z0-9_.-]*)"
    match = re.search(pattern, url)
    if not match:
        return json.dumps({'error': "invalid_url"}, indent=2)
    owner, repo = match.group(1), match.group(2)

    return json.dumps({'owner': owner, 'repo': repo}, indent=2)


def _get_zip(owner, repo):
    url = 'https://codeload.github.com/{}/{}/zip/master'.format(
        owner, repo)
    with closing(requests.get(url, stream=True)) as r:
        chunks = r.iter_content(chunk_size=15000000)
        content = next(chunks)
        try:
            next(chunks)
        except StopIteration:
            r.raise_for_status()
            return content
        raise RepoTooBig


def _get_loc(zip_contents):
    with ZipFile(BytesIO(zip_contents)) as zip_file:
        with TemporaryDirectory() as temp_dir:
            for member in zip_file.namelist():
                zip_file.extract(member, temp_dir)

            sloc_resp = subprocess.run(
                ['sloc', temp_dir, '--format', 'json'],
                timeout=10,
                stdout=subprocess.PIPE,
            )

            resp = json.loads(sloc_resp.stdout.decode('utf-8'))
            lang_data = {lang: resp["byExt"][lang]["summary"]
                         for lang in resp["byExt"]}
            data = {
                "languages": lang_data,
                "summary": resp["summary"] or {"source": 0, "total": 0}
            }
            return data


@app.route('/loc/github')
def github_loc():
    if 'owner' not in request.args or 'repo' not in request.args:
        return json.dumps({"error": "missing_parameters"}, indent=2)
    owner = request.args['owner']
    repo = request.args['repo']

    try:
        repo_contents = _get_zip(owner, repo)
    except requests.exceptions.HTTPError:
        return json.dumps({"error": "invalid_repo"}, indent=2)
    except RepoTooBig:
        return json.dumps({"error": "repo_too_big"}, indent=2)

    try:
        return json.dumps(_get_loc(repo_contents), indent=2)
    except RuntimeError:
        return json.dumps({"error": "parse_error"}, indent=2)
    except (subprocess.TimeoutExpired, RepoTooBig):
        return json.dumps({"error": "repo_too_big"}, indent=2)

    return json.dumps({"error": "parse_error"}, indent=2)

if __name__ == '__main__':
    app.run(debug=True)

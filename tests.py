import gitloc
import json
import requests
import unittest


class ParseUrlTests(unittest.TestCase):

    def setUp(self):
        gitloc.app.config['TESTING'] = True
        self.app = gitloc.app.test_client()

    def test_missing_url(self):
        response = self.app.get('/repo')
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertEqual(json_response, {'error': 'missing_parameters'})

    def test_invalid_url(self):
        response = self.app.get('/repo?url=github.com%2F404')
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertEqual(json_response, {'error': 'invalid_url'})


class GetZipTests(unittest.TestCase):

    def setUp(self):
        gitloc.app.config['TESTING'] = True
        self.app = gitloc.app.test_client()

    def test_successful_download(self):
        self.assertEqual(len(gitloc._get_zip('octocat', 'Hello-World')), 351)

    def test_invalid_repo(self):
        try:
            gitloc._get_zip('fakeuser', 'fakerepo')
            self.assertFail()
        except requests.exceptions.HTTPError as e:
            self.assertEqual(e.response.status_code, 404)


class GithubLocTests(unittest.TestCase):

    def setUp(self):
        gitloc.app.config['TESTING'] = True
        self.app = gitloc.app.test_client()

    def test_invalid_repo(self):
        response = self.app.get('loc/github?owner=fakeowner&repo=fakerepo')
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertEqual(json_response, {'error': 'invalid_repo'})

    def test_missing_parameters(self):
        response = self.app.get('loc/github?repo=fakerepo')
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertEqual(json_response, {'error': 'missing_parameters'})

    def test_loc(self):
        response = self.app.get('loc/github?owner=octocat&repo=Spoon-Knife')
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertCountEqual(
            json_response["languages"].keys(),
            ['html', 'css']
        )

if __name__ == '__main__':
    unittest.main(warnings='ignore')

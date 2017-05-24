# -*- coding: utf-8 -*-
"""
This is the version 2 HTTP API.

It uses OpenID Connect for endpoints that require authentication.
"""

from gettext import gettext as _

from flask import jsonify
from flask_restful import Resource, reqparse

from anitya.app import APP, SESSION
from anitya.lib.exceptions import ProjectExists
import anitya
import anitya.lib.model
import anitya.authentication

_BASE_ARG_PARSER = reqparse.RequestParser(trim=True, bundle_errors=True)
_BASE_ARG_PARSER.add_argument('access_token', type=str)


def _page_validator(arg):
    """
    Validator for a pagination page number.

    Args:
        arg (object): The object to validate as an integer greater than or
            equal to 1.

    Returns:
        int: The validated argument.

    Raises:
        ValueError: If the integer is smaller than 1 or it can't be cast to an
            int.
    """
    arg = int(arg)
    if arg < 1:
        raise ValueError(_('Value must be greater than or equal to 1.'))
    return arg


def _items_per_page_validator(arg):
    """
    Validator for a pagination items_per_page number.

    Args:
        arg (object): The object to validate as an integer greater than or
            equal to 1 and less or equal to 250.

    Returns:
        int: The validated argument.

    Raises:
        ValueError: If the integer is smaller than 1 or it can't be cast to an
            int.
    """
    arg = int(arg)
    if arg < 1:
        raise ValueError(_('Value must be greater than or equal to 1.'))
    if arg > 250:
        raise ValueError(_('Value must be less than or equal to 250.'))
    return arg


class ProjectsResource(Resource):
    """
    The ``api/v2/projects/`` API endpoint.
    """

    @anitya.authentication.parse_api_token
    def get(self):
        """
        Lists all projects.

        **Example request**:

        .. sourcecode:: http

            GET /api/v2/projects/?items_per_page=1&page=2 HTTP/1.1
            Accept: application/json
            Accept-Encoding: gzip, deflate
            Connection: keep-alive
            Host: localhost:5000
            User-Agent: HTTPie/0.9.4

        **Example response**:

        .. sourcecode:: http

            HTTP/1.0 200 OK
            Content-Length: 676
            Content-Type: application/json
            Date: Fri, 24 Mar 2017 18:44:32 GMT
            Server: Werkzeug/0.12.1 Python/2.7.13

            {
                "items": [
                    {
                        "backend": "Sourceforge",
                        "created_on": 1412174943.0,
                        "homepage": "http://sourceforge.net/projects/zero-install",
                        "id": 1,
                        "name": "0install",
                        "regex": "",
                        "updated_on": 1482495004.0,
                        "version": "2.12",
                        "version_url": "zero-install",
                        "versions": [
                            "2.12",
                            "2.11",
                            "2.10",
                            "2.9.1",
                            "2.9",
                            "2.8",
                            "2.7"
                        ]
                    }
                ],
                "items_per_page": 1,
                "page": 2,
                "total_items": 13468
            }


        :query int page: The project page number to retrieve (defaults to 1).
        :query int items_per_page: The number of items per page (defaults to
                                   25, maximum of 250).
        :statuscode 200: If all arguments are valid. Note that even if there
                         are no projects, this will return 200.
        :statuscode 400: If one or more of the query arguments is invalid.
        """

        parser = _BASE_ARG_PARSER.copy()
        parser.add_argument('page', type=_page_validator, location='args')
        parser.add_argument('items_per_page', type=_items_per_page_validator, location='args')
        args = parser.parse_args(strict=True)
        args.pop('access_token')
        projects_page = anitya.lib.model.Project.query.paginate(
            order_by=anitya.lib.model.Project.name, **args)
        return projects_page.as_dict()

    @anitya.authentication.require_api_token("upstream")
    def post(self):
        """
        Create a new project.

        **Example Request**:

        .. sourcecode:: http

            POST /api/v2/projects/?access_token=MYAPIACCESSTOKEN HTTP/1.1
            Accept: application/json
            Accept-Encoding: gzip, deflate
            Connection: keep-alive
            Content-Length: 114
            Content-Type: application/json
            Host: localhost:5000
            User-Agent: HTTPie/0.9.4

            {
                "backend": "custom",
                "homepage": "http://example.com/test",
                "name": "test_project",
                "version_prefix": "release-"
            }


        **Example Response**:

        .. sourcecode:: http

            HTTP/1.0 201 CREATED
            Content-Length: 276
            Content-Type: application/json
            Date: Sun, 26 Mar 2017 15:56:30 GMT
            Server: Werkzeug/0.12.1 Python/2.7.13

            {
                "backend": "PyPI",
                "created_on": 1490543790.0,
                "homepage": "http://python-requests.org",
                "id": 13857,
                "name": "requests",
                "regex": null,
                "updated_on": 1490543790.0,
                "version": null,
                "version_url": null,
                "versions": []
            }

        :query string access_token: Your API access token.
        :reqjson string name: The project name
        :reqjson string homepage: The project homepage URL
        :reqjson string backend: The project backend (github, folder, etc.).
        :reqjson string version_url: The URL to fetch when determining the
                                     project version (defaults to null).
        :reqjson string version_prefix: The project version prefix, if any. For
                                        example, some projects prefix with "v".
        :reqjson string regex: The regex to use when searching the
                               ``version_url`` page.
        :reqjson bool insecure: When retrieving the versions via HTTPS, do not
                                validate the certificate (defaults to false).
        :reqjson bool check_release: Check the release immediately after
                                     creating the project.

        :statuscode 201: When the project was successfully created.
        :statuscode 400: When required arguments are missing or malformed.
        :statuscode 401: When your access token is missing or invalid, or when
                         the server is not configured for OpenID Connect. The
                         response will include a JSON body describing the exact
                         problem.
        :statuscode 409: When the project already exists.
        """
        name_help = _('The project name')
        homepage_help = _('The project homepage URL')
        backend_help = _('The project backend (github, folder, etc.)')
        version_url_help = _('The URL to fetch when determining the project '
                             'version (defaults to null)')
        version_prefix_help = _('The project version prefix, if any. For '
                                'example, some projects prefix with "v"')
        regex_help = _('The regex to use when searching the version_url page')
        insecure_help = _('When retrieving the versions via HTTPS, do not '
                          'validate the certificate (defaults to false)')
        check_release_help = _('Check the release immediately after creating '
                               'the project.')

        parser = _BASE_ARG_PARSER.copy()
        parser.add_argument('name', type=str, help=name_help, required=True)
        parser.add_argument(
            'homepage', type=str, help=homepage_help, required=True)
        parser.add_argument(
            'backend', type=str, help=backend_help, required=True)
        parser.add_argument(
            'version_url', type=str, help=version_url_help, default=None)
        parser.add_argument(
            'version_prefix', type=str, help=version_prefix_help, default=None)
        parser.add_argument('regex', type=str, help=regex_help, default=None)
        parser.add_argument(
            'insecure', type=bool, help=insecure_help, default=False)
        parser.add_argument(
            'check_release', type=bool, help=check_release_help)
        args = parser.parse_args(strict=True)
        access_token = args.pop('access_token')

        try:
            project = anitya.lib.create_project(
                SESSION,
                user_id=APP.oidc.user_getfield('email', access_token),
                **args
            )
            SESSION.commit()
            return project.__json__(), 201
        except ProjectExists as e:
            response = jsonify(e.to_dict())
            response.status_code = 409
            return response


APP.api.add_resource(ProjectsResource, '/api/v2/projects/')

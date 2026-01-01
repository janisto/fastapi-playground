"""
Unit tests for base exception classes.

These tests verify that fastapi-problem exception classes are properly re-exported.
"""

from fastapi_problem.error import Problem

from app.exceptions.base import (
    BadRequestProblem,
    ConflictProblem,
    ForbiddenProblem,
    NotFoundProblem,
    ServerProblem,
    UnauthorisedProblem,
    UnprocessableProblem,
)


class TestProblemExports:
    """
    Tests for base exception re-exports from fastapi-problem.
    """

    def test_not_found_problem_status(self) -> None:
        """
        Verify NotFoundProblem has correct status code.
        """
        err = NotFoundProblem()
        assert err.status == 404

    def test_not_found_problem_inherits_from_problem(self) -> None:
        """
        Verify NotFoundProblem inherits from Problem.
        """
        err = NotFoundProblem()
        assert isinstance(err, Problem)

    def test_conflict_problem_status(self) -> None:
        """
        Verify ConflictProblem has correct status code.
        """
        err = ConflictProblem()
        assert err.status == 409

    def test_conflict_problem_inherits_from_problem(self) -> None:
        """
        Verify ConflictProblem inherits from Problem.
        """
        err = ConflictProblem()
        assert isinstance(err, Problem)

    def test_bad_request_problem_status(self) -> None:
        """
        Verify BadRequestProblem has correct status code.
        """
        err = BadRequestProblem()
        assert err.status == 400

    def test_forbidden_problem_status(self) -> None:
        """
        Verify ForbiddenProblem has correct status code.
        """
        err = ForbiddenProblem()
        assert err.status == 403

    def test_unauthorised_problem_status(self) -> None:
        """
        Verify UnauthorisedProblem has correct status code.
        """
        err = UnauthorisedProblem()
        assert err.status == 401

    def test_unprocessable_problem_status(self) -> None:
        """
        Verify UnprocessableProblem has correct status code.
        """
        err = UnprocessableProblem()
        assert err.status == 422

    def test_server_problem_status(self) -> None:
        """
        Verify ServerProblem has correct status code.
        """
        err = ServerProblem()
        assert err.status == 500

    def test_custom_detail(self) -> None:
        """
        Verify custom detail can be set.
        """
        err = NotFoundProblem(detail="No profile exists for user")
        assert err.detail == "No profile exists for user"

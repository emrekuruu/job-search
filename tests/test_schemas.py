import pytest
from pydantic import ValidationError

from job_search.config import DIMENSIONS
from job_search.schemas import DimensionScore, FitEvaluation, JobQuery, QuerySet


def _scores(values):
    return [
        DimensionScore(name=d.name, score=v, reasoning="r")
        for d, v in zip(DIMENSIONS, values, strict=True)
    ]


def test_queryset_roundtrip():
    qs = QuerySet(queries=[JobQuery(search_term="data scientist", location="NYC")])
    assert QuerySet.model_validate_json(qs.model_dump_json()).queries[0].search_term == "data scientist"


def test_fit_evaluation_valid():
    ev = FitEvaluation(dimensions=_scores([20, 15, 10, 5, 0]), total=50, overall_reasoning="ok")
    assert ev.total == 50


def test_fit_evaluation_total_must_equal_sum():
    with pytest.raises(ValidationError):
        FitEvaluation(dimensions=_scores([20, 20, 20, 20, 20]), total=99, overall_reasoning="x")


def test_fit_evaluation_dimension_count():
    with pytest.raises(ValidationError):
        FitEvaluation(
            dimensions=_scores([20, 20, 20, 20, 20])[:4], total=80, overall_reasoning="x"
        )


def test_dimension_score_bounds():
    with pytest.raises(ValidationError):
        DimensionScore(name="x", score=21, reasoning="r")
